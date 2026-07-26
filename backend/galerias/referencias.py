from collections import defaultdict
from pathlib import Path

import numpy as np

from backend.config import ConfiguracionGalerias, ConfiguracionRostro
from backend.dominio.modelos import ReferenciaFacial, RostroModelo
from backend.galerias.repositorio import RepositorioGalerias
from backend.ia.interfaces import ReconocedorFacial
from backend.utilidades.imagenes import (
    calcular_calidad_muestra,
    leer_imagen,
    normalizar_vector,
)


def seleccionar_rostro_principal(rostros: list[RostroModelo]) -> RostroModelo:
    return max(
        rostros,
        key=lambda rostro: (
            (rostro.bbox[2] - rostro.bbox[0])
            * (rostro.bbox[3] - rostro.bbox[1])
        ),
    )


class CargadorReferencias:
    def __init__(
        self,
        repositorio: RepositorioGalerias,
        reconocedor: ReconocedorFacial,
    ):
        self.repositorio = repositorio
        self.reconocedor = reconocedor

    def cargar(
        self,
        anteriores: list[ReferenciaFacial] | None = None,
    ) -> list[ReferenciaFacial]:
        with self.repositorio.transaccion():
            return self._cargar_bajo_bloqueo(anteriores)

    def _cargar_bajo_bloqueo(
        self,
        anteriores: list[ReferenciaFacial] | None,
    ) -> list[ReferenciaFacial]:
        referencias: list[ReferenciaFacial] = []
        cache = {
            referencia.firma_archivo: referencia
            for referencia in anteriores or []
            if referencia.firma_archivo is not None
        }
        carpetas = (
            (self.repositorio.config.carpeta_referencias, "oficial"),
            (self.repositorio.config.carpeta_pendientes, "pendiente"),
        )
        print("Cargando rostros de referencia...")
        for carpeta, tipo in carpetas:
            for nombre, ruta in self.repositorio.iterar_muestras(carpeta):
                try:
                    datos = ruta.stat()
                except FileNotFoundError:
                    continue
                firma = (datos.st_mtime_ns, datos.st_size)
                cacheada = cache.get(firma)
                if cacheada is not None:
                    referencias.append(
                        ReferenciaFacial(
                            nombre=nombre,
                            embedding=cacheada.embedding.copy(),
                            tipo=tipo,
                            firma_archivo=firma,
                            ruta=ruta,
                            calidad=cacheada.calidad,
                        )
                    )
                    print(f"Referencia reutilizada: {nombre} | tipo: {tipo}")
                    continue
                imagen = leer_imagen(ruta)
                if imagen is None:
                    print(f"No se pudo leer: {ruta.name}")
                    continue
                rostros = self.reconocedor.analizar(imagen)
                if not rostros:
                    print(f"No se detecto rostro en: {ruta.name}")
                    continue
                rostro = seleccionar_rostro_principal(rostros)
                referencias.append(
                    ReferenciaFacial(
                        nombre=nombre,
                        embedding=normalizar_vector(rostro.embedding),
                        tipo=tipo,
                        firma_archivo=firma,
                        ruta=ruta,
                        calidad=calcular_calidad_muestra(imagen),
                    )
                )
                print(f"Referencia cargada: {nombre} | tipo: {tipo}")
        if not referencias:
            print("No hay rostros de referencia validos todavia.")
            print(
                "Puedes agregar imagenes manualmente en: "
                f"{self.repositorio.config.carpeta_referencias}"
            )
            print(
                "Las capturas de desconocidos se guardaran en: "
                f"{self.repositorio.config.carpeta_pendientes}"
            )
        return referencias


def comparar_con_referencias(
    embedding: np.ndarray,
    referencias: list[ReferenciaFacial],
    config: ConfiguracionRostro,
) -> tuple[str, float, str | None, bool]:
    mejor_nombre = "Desconocido"
    mejor_similitud = -1.0
    mejor_tipo = None
    mejor_criterio = (-1, -1.0)
    mejor_reconocido = False
    por_identidad: dict[tuple[str, str], list[float]] = defaultdict(list)
    for referencia in referencias:
        por_identidad[(referencia.nombre, referencia.tipo)].append(
            float(np.dot(embedding, referencia.embedding))
        )
    for (nombre, tipo), similitudes in por_identidad.items():
        ordenadas = sorted(similitudes, reverse=True)
        mejor = ordenadas[0]
        if len(ordenadas) >= 2:
            segunda = ordenadas[1]
            puntuacion = (mejor + segunda) / 2.0
            reconocido = (
                mejor >= config.umbral_similitud
                and segunda >= config.segunda_similitud_minima
            )
        else:
            puntuacion = mejor
            reconocido = mejor >= config.umbral_galeria_una_muestra
        criterio = (1 if reconocido else 0, puntuacion)
        if criterio > mejor_criterio:
            mejor_criterio = criterio
            mejor_similitud = mejor
            mejor_nombre = nombre
            mejor_tipo = tipo
            mejor_reconocido = reconocido
    return mejor_nombre, mejor_similitud, mejor_tipo, mejor_reconocido


def crear_mapa_referencias(
    anteriores: list[ReferenciaFacial],
    nuevas: list[ReferenciaFacial],
    config_rostro: ConfiguracionRostro,
    config_galerias: ConfiguracionGalerias,
) -> dict[tuple[str, str], tuple[str, str]]:
    mapa: dict[tuple[str, str], tuple[str, str]] = {}
    for anterior in anteriores:
        misma = [nueva for nueva in nuevas if nueva.nombre == anterior.nombre]
        if misma:
            mejor = max(
                misma,
                key=lambda nueva: float(
                    np.dot(anterior.embedding, nueva.embedding)
                ),
            )
            similitud = float(np.dot(anterior.embedding, mejor.embedding))
            if similitud >= config_rostro.umbral_similitud:
                mapa[(anterior.nombre, anterior.tipo)] = (
                    mejor.nombre,
                    mejor.tipo,
                )
                continue
        if not nuevas:
            continue
        mejor = max(
            nuevas,
            key=lambda nueva: float(
                np.dot(anterior.embedding, nueva.embedding)
            ),
        )
        similitud = float(np.dot(anterior.embedding, mejor.embedding))
        if similitud >= config_galerias.similitud_mapeo_renombrada:
            mapa[(anterior.nombre, anterior.tipo)] = (
                mejor.nombre,
                mejor.tipo,
            )
    return mapa
