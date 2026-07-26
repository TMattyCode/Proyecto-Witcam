import shutil
import time
from pathlib import Path

import numpy as np

from backend.config import ConfiguracionGalerias
from backend.dominio.modelos import ReferenciaFacial
from backend.galerias.repositorio import RepositorioGalerias


def evaluar_coincidencia(
    muestras_a: list[ReferenciaFacial],
    muestras_b: list[ReferenciaFacial],
    config: ConfiguracionGalerias,
) -> dict[str, float] | None:
    if (
        len(muestras_a) < config.muestras_minimas_reconciliacion
        or len(muestras_b) < config.muestras_minimas_reconciliacion
    ):
        return None
    coincidencias = sorted(
        (
            (
                float(np.dot(a.embedding, b.embedding)),
                indice_a,
                indice_b,
            )
            for indice_a, a in enumerate(muestras_a)
            for indice_b, b in enumerate(muestras_b)
        ),
        reverse=True,
    )
    if not coincidencias:
        return None
    principal = coincidencias[0]
    secundaria = next(
        (
            coincidencia
            for coincidencia in coincidencias[1:]
            if coincidencia[1] != principal[1]
            and coincidencia[2] != principal[2]
        ),
        None,
    )
    if secundaria is None:
        return None
    promedio = (principal[0] + secundaria[0]) / 2.0
    if (
        principal[0] < config.similitud_principal_reconciliacion
        or secundaria[0] < config.similitud_secundaria_reconciliacion
        or promedio < config.promedio_reconciliacion
    ):
        return None
    return {
        "principal": principal[0],
        "secundaria": secundaria[0],
        "promedio": promedio,
    }


def antiguedad(muestras: list[ReferenciaFacial]) -> int:
    fechas = [
        muestra.ruta.stat().st_mtime_ns
        for muestra in muestras
        if muestra.ruta is not None and muestra.ruta.is_file()
    ]
    return min(fechas, default=time.time_ns())


def seleccionar_para_fusion(
    destino: list[ReferenciaFacial],
    origen: list[ReferenciaFacial],
    config: ConfiguracionGalerias,
) -> list[ReferenciaFacial]:
    seleccionadas = sorted(
        destino,
        key=lambda muestra: antiguedad([muestra]),
    )[: config.max_muestras_por_persona]
    for candidata in sorted(
        origen,
        key=lambda muestra: muestra.calidad,
        reverse=True,
    ):
        if len(seleccionadas) < config.max_muestras_por_persona:
            seleccionadas.append(candidata)
            continue
        peor = min(seleccionadas, key=lambda muestra: muestra.calidad)
        if (
            candidata.calidad
            >= peor.calidad + config.mejora_calidad_reemplazo
        ):
            seleccionadas.remove(peor)
            seleccionadas.append(candidata)
    return seleccionadas


def fusionar(
    repositorio: RepositorioGalerias,
    nombre_destino: str,
    nombre_origen: str,
    referencias: list[ReferenciaFacial],
) -> bool:
    config = repositorio.config
    with repositorio.transaccion():
        ruta_destino = repositorio.ruta_galeria(
            config.carpeta_pendientes,
            nombre_destino,
        )
        ruta_origen = repositorio.ruta_galeria(
            config.carpeta_pendientes,
            nombre_origen,
        )
        if not ruta_destino.is_dir() or not ruta_origen.is_dir():
            return False
        destino = [
            referencia
            for referencia in referencias
            if referencia.tipo == "pendiente"
            and referencia.nombre == nombre_destino
        ]
        origen = [
            referencia
            for referencia in referencias
            if referencia.tipo == "pendiente"
            and referencia.nombre == nombre_origen
        ]
        seleccionadas = seleccionar_para_fusion(destino, origen, config)
        ids_seleccionadas = {id(muestra) for muestra in seleccionadas}
        for muestra in destino + origen:
            ruta_actual = muestra.ruta
            if ruta_actual is None:
                continue
            if id(muestra) not in ids_seleccionadas:
                if ruta_actual.is_file():
                    ruta_actual.unlink()
                continue
            if ruta_actual.parent == ruta_origen:
                ruta_nueva = ruta_destino / ruta_actual.name
                if ruta_nueva.exists():
                    ruta_nueva = (
                        ruta_destino
                        / f"muestra_fusion_{time.time_ns()}"
                        f"{ruta_actual.suffix.lower()}"
                    )
                shutil.move(str(ruta_actual), str(ruta_nueva))
                ruta_actual = ruta_nueva
            datos = ruta_actual.stat()
            muestra.nombre = nombre_destino
            muestra.ruta = ruta_actual
            muestra.firma_archivo = (datos.st_mtime_ns, datos.st_size)
        if ruta_origen.is_dir():
            shutil.rmtree(ruta_origen)
        referencias[:] = [
            referencia
            for referencia in referencias
            if not (
                referencia.tipo == "pendiente"
                and referencia.nombre in {nombre_destino, nombre_origen}
            )
        ] + seleccionadas
        return True


def reconciliar(
    repositorio: RepositorioGalerias,
    referencias: list[ReferenciaFacial],
) -> dict[tuple[str, str], tuple[str, str]]:
    mapa = {}
    with repositorio.transaccion():
        while True:
            galerias: dict[str, list[ReferenciaFacial]] = {}
            for referencia in referencias:
                if referencia.tipo == "pendiente":
                    galerias.setdefault(referencia.nombre, []).append(referencia)
            mejor_fusion = None
            nombres = sorted(galerias)
            for indice, nombre_a in enumerate(nombres):
                for nombre_b in nombres[indice + 1 :]:
                    resultado = evaluar_coincidencia(
                        galerias[nombre_a],
                        galerias[nombre_b],
                        repositorio.config,
                    )
                    if resultado is not None and (
                        mejor_fusion is None
                        or resultado["promedio"] > mejor_fusion[0]
                    ):
                        mejor_fusion = (
                            resultado["promedio"],
                            nombre_a,
                            nombre_b,
                            resultado,
                        )
            if mejor_fusion is None:
                break
            _, nombre_a, nombre_b, resultado = mejor_fusion
            if antiguedad(galerias[nombre_a]) <= antiguedad(
                galerias[nombre_b]
            ):
                nombre_destino, nombre_origen = nombre_a, nombre_b
            else:
                nombre_destino, nombre_origen = nombre_b, nombre_a
            if not fusionar(
                repositorio,
                nombre_destino,
                nombre_origen,
                referencias,
            ):
                break
            mapa[(nombre_origen, "pendiente")] = (
                nombre_destino,
                "pendiente",
            )
            print(
                f"Galerias duplicadas fusionadas: {nombre_origen} -> "
                f"{nombre_destino} | similitudes "
                f"{resultado['principal']:.2f}/{resultado['secundaria']:.2f}"
            )
    return mapa
