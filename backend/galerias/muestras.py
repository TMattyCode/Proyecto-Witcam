import time
from datetime import datetime
from pathlib import Path

import numpy as np

from backend.config import ConfiguracionRostro
from backend.dominio.modelos import CandidatoDesconocido, ReferenciaFacial
from backend.galerias.referencias import seleccionar_rostro_principal
from backend.galerias.repositorio import RepositorioGalerias
from backend.ia.interfaces import ReconocedorFacial
from backend.utilidades.imagenes import (
    calcular_calidad_muestra,
    escribir_jpg,
    normalizar_vector,
    recortar_muestra,
)
from backend.utilidades.rostros import evaluar_calidad_rostro


class GestorMuestras:
    def __init__(
        self,
        repositorio: RepositorioGalerias,
        reconocedor: ReconocedorFacial,
        config_rostro: ConfiguracionRostro,
    ):
        self.repositorio = repositorio
        self.reconocedor = reconocedor
        self.config_rostro = config_rostro

    def agregar(
        self,
        frame: np.ndarray,
        bbox: tuple[int, int, int, int],
        nombre: str,
        embedding: np.ndarray,
        referencias: list[ReferenciaFacial],
    ) -> bool:
        config = self.repositorio.config
        with self.repositorio.transaccion():
            galeria = self.repositorio.ruta_galeria(
                config.carpeta_pendientes,
                nombre,
            )
            if not galeria.is_dir():
                return False
            muestras = [
                referencia
                for referencia in referencias
                if referencia.nombre == nombre
                and referencia.tipo == "pendiente"
            ]
            if muestras:
                semilla = min(
                    muestras,
                    key=lambda referencia: (
                        referencia.ruta.stat().st_mtime_ns
                        if referencia.ruta is not None
                        and referencia.ruta.exists()
                        else 0
                    ),
                )
                if (
                    float(np.dot(embedding, semilla.embedding))
                    < config.similitud_muestra_semilla
                ):
                    return False
                fechas = [
                    referencia.ruta.stat().st_mtime
                    for referencia in muestras
                    if referencia.ruta is not None
                    and referencia.ruta.exists()
                ]
                if fechas and time.time() - max(fechas) < config.intervalo_nueva_muestra:
                    return False
                if (
                    max(
                        float(np.dot(embedding, referencia.embedding))
                        for referencia in muestras
                    )
                    >= config.similitud_muestra_redundante
                ):
                    return False
            recorte = recortar_muestra(frame, bbox)
            calidad = calcular_calidad_muestra(recorte)
            reemplazada = None
            if len(muestras) >= config.max_muestras_por_persona:
                peor = min(muestras, key=lambda referencia: referencia.calidad)
                if (
                    calidad
                    < peor.calidad + config.mejora_calidad_reemplazo
                ):
                    return False
                reemplazada = peor
            ruta = galeria / f"muestra_{time.time_ns()}.jpg"
            escribir_jpg(ruta, recorte)
            datos = ruta.stat()
            if reemplazada is not None:
                if reemplazada.ruta is not None and reemplazada.ruta.exists():
                    reemplazada.ruta.unlink()
                referencias[:] = [
                    referencia
                    for referencia in referencias
                    if referencia is not reemplazada
                ]
            referencias.append(
                ReferenciaFacial(
                    nombre=nombre,
                    embedding=embedding.copy(),
                    tipo="pendiente",
                    firma_archivo=(datos.st_mtime_ns, datos.st_size),
                    ruta=ruta,
                    calidad=calidad,
                )
            )
            return True

    def guardar_desconocido(
        self,
        candidato: CandidatoDesconocido,
        tracker_id: int,
    ) -> tuple[str, Path, np.ndarray, float] | None:
        recorte = recortar_muestra(
            candidato.mejor_frame,
            candidato.mejor_bbox,
        )
        rostros = self.reconocedor.analizar(recorte)
        if not rostros:
            print(
                "Captura descartada: SCRFD no pudo reutilizar "
                "el rostro recortado."
            )
            return None
        rostro = seleccionar_rostro_principal(rostros)
        evaluable, motivo = evaluar_calidad_rostro(
            rostro.bbox,
            rostro.puntos_clave,
            rostro.confianza,
            self.config_rostro,
            validar_tamano_confianza=False,
        )
        if not evaluable:
            print(f"Captura descartada: {motivo}.")
            return None
        embedding = normalizar_vector(rostro.embedding)
        calidad = calcular_calidad_muestra(recorte)
        nombre = datetime.now().strftime(
            f"desconocido_track_{tracker_id}_%Y%m%d_%H%M%S"
        )
        with self.repositorio.transaccion():
            galeria = self.repositorio.ruta_directorio_unica(
                self.repositorio.ruta_galeria(
                    self.repositorio.config.carpeta_pendientes,
                    nombre,
                )
            )
            galeria.mkdir(parents=True)
            ruta = galeria / "muestra_01.jpg"
            escribir_jpg(ruta, recorte)
        print(f"Rostro desconocido guardado para revision: {ruta}")
        return galeria.name, ruta, embedding, calidad
