import time
from collections.abc import Callable

import numpy as np

from backend.config import (
    ConfiguracionDesconocidos,
    ConfiguracionGalerias,
    ConfiguracionRostro,
    ConfiguracionTracking,
)
from backend.dominio.modelos import (
    AnalisisRostro,
    CandidatoDesconocido,
    EstadoSeguimiento,
    ReferenciaFacial,
    ResultadoVisual,
)
from backend.galerias.muestras import GestorMuestras
from backend.galerias.referencias import comparar_con_referencias
from backend.ia.identidades import GestorIdentidades
from backend.utilidades.geometria import calcular_iou
from backend.utilidades.imagenes import (
    calcular_calidad_muestra,
    recortar_muestra,
)


class GestorDesconocidos:
    """Administra candidatos sin identidad y su conversion en galerias."""

    def __init__(
        self,
        config: ConfiguracionDesconocidos,
        config_galerias: ConfiguracionGalerias,
        config_rostro: ConfiguracionRostro,
        config_tracking: ConfiguracionTracking,
        muestras: GestorMuestras,
        identidades: GestorIdentidades,
        registrar_evento: Callable[[str], None],
    ):
        self.config = config
        self.config_galerias = config_galerias
        self.config_rostro = config_rostro
        self.config_tracking = config_tracking
        self.muestras = muestras
        self.identidades = identidades
        self.registrar_evento = registrar_evento

    @staticmethod
    def clave(tracker_id: int, persona_id: int | None = None) -> tuple[str, int]:
        return (
            ("persona", int(persona_id))
            if persona_id is not None
            else ("rostro", int(tracker_id))
        )

    @staticmethod
    def eliminar(
        candidatos: dict[tuple[str, int], CandidatoDesconocido],
        tracker_id: int | None = None,
        persona_id: int | None = None,
    ) -> None:
        if tracker_id is not None:
            candidatos.pop(("rostro", int(tracker_id)), None)
        if persona_id is not None:
            candidatos.pop(("persona", int(persona_id)), None)

    def limpiar(
        self,
        candidatos: dict[tuple[str, int], CandidatoDesconocido],
    ) -> None:
        ahora = time.time()
        for clave, candidato in list(candidatos.items()):
            tolerancia = (
                self.config.tolerancia_candidato_facial
                if clave[0] == "rostro"
                else 2.0
            )
            if ahora - candidato.ultimo_visto > tolerancia:
                candidatos.pop(clave, None)

    def buscar_candidato_facial_reciente(
        self,
        tracker_id: int,
        bbox: tuple[int, int, int, int],
        embedding: np.ndarray,
        candidatos: dict[tuple[str, int], CandidatoDesconocido],
        rostros_visibles: set[int],
    ) -> CandidatoDesconocido | None:
        ahora = time.time()
        mejor = None
        for clave, candidato in candidatos.items():
            if (
                clave[0] != "rostro"
                or clave[1] == tracker_id
                or candidato.rostro_tracker_id in rostros_visibles
                or ahora - candidato.ultimo_visto
                > self.config.tolerancia_candidato_facial
            ):
                continue
            iou = calcular_iou(bbox, candidato.bbox)
            similitud = float(np.dot(embedding, candidato.embedding_semilla))
            posicion_fuerte = (
                iou >= self.config.iou_reasociacion_facial_fuerte
                and similitud >= 0.05
            )
            coincidencia = (
                iou >= self.config.iou_reasociacion_facial
                and similitud >= self.config.similitud_reasociacion_facial
            )
            if not posicion_fuerte and not coincidencia:
                continue
            puntuacion = iou + max(0.0, similitud) * 0.5
            if mejor is None or puntuacion > mejor[0]:
                mejor = (puntuacion, clave, candidato)
        if mejor is None:
            return None
        _, clave_anterior, candidato = mejor
        candidatos.pop(clave_anterior, None)
        return candidato

    @staticmethod
    def _crear_candidato(
        ahora: float,
        tracker_id: int,
        persona_id: int | None,
        bbox: tuple[int, int, int, int],
        frame: np.ndarray,
        area: int,
        calidad: float,
        embedding: np.ndarray,
    ) -> CandidatoDesconocido:
        return CandidatoDesconocido(
            inicio=ahora,
            ultimo_visto=ahora,
            muestras=1,
            rostro_tracker_id=tracker_id,
            persona_id=persona_id,
            bbox=bbox,
            mejor_frame=frame.copy(),
            mejor_bbox=bbox,
            mejor_area=area,
            mejor_calidad=calidad,
            mejor_embedding=embedding.copy(),
            embedding_semilla=embedding.copy(),
        )

    def _reiniciar(
        self,
        candidato: CandidatoDesconocido,
        ahora: float,
        tracker_id: int,
        persona_id: int | None,
        bbox: tuple[int, int, int, int],
        frame: np.ndarray,
        area: int,
        calidad: float,
        embedding: np.ndarray,
        muestras: int = 1,
    ) -> None:
        nuevo = self._crear_candidato(
            ahora,
            tracker_id,
            persona_id,
            bbox,
            frame,
            area,
            calidad,
            embedding,
        )
        candidato.__dict__.update(nuevo.__dict__)
        candidato.muestras = muestras

    def manejar(
        self,
        frame: np.ndarray,
        tracker_id: int,
        box: tuple[int, int, int, int],
        rostro: AnalisisRostro,
        referencias: list[ReferenciaFacial],
        estado: EstadoSeguimiento,
        persona_id: int | None,
        rostros_visibles: set[int],
    ) -> ResultadoVisual:
        bbox = rostro.bbox
        x1, y1, x2, y2 = box
        clave_rostro = self.clave(tracker_id)
        clave = self.clave(tracker_id, persona_id)
        candidatos = estado.candidatos_desconocidos
        if (
            persona_id is not None
            and clave not in candidatos
            and clave_rostro in candidatos
        ):
            candidatos[clave] = candidatos.pop(clave_rostro)
        elif persona_id is None and clave not in candidatos:
            reciente = self.buscar_candidato_facial_reciente(
                tracker_id,
                bbox,
                rostro.embedding,
                candidatos,
                rostros_visibles,
            )
            if reciente is not None:
                candidatos[clave] = reciente

        historial = estado.historial_rostros.get(tracker_id)
        if historial is not None:
            tiempo = time.time() - historial["ultimo_visto"]
            parece_misma = (
                rostro.nombre == historial["nombre"]
                and rostro.similitud
                >= self.config_tracking.similitud_posible_misma_persona
            )
            if (
                tiempo <= self.config_tracking.tolerancia_oclusion
                or parece_misma
            ):
                if historial["tipo"] == "pendiente":
                    self.muestras.agregar(
                        frame,
                        bbox,
                        historial["nombre"],
                        rostro.embedding,
                        referencias,
                    )
                historial["ultimo_visto"] = time.time()
                historial["bbox"] = bbox
                self.eliminar(candidatos, tracker_id, persona_id)
                texto = (
                    f"{historial['nombre']} | "
                    f"oclusion {rostro.similitud:.2f}"
                )
                return ResultadoVisual(box, texto, (0, 180, 255))

        reidentificado, similitud = self.identidades.buscar_identidad_reciente(
            tracker_id,
            rostro.embedding,
            bbox,
            estado.historial_rostros,
            self.config_rostro.umbral_similitud,
        )
        if reidentificado is not None:
            estado.historial_rostros[tracker_id] = {
                **reidentificado,
                "ultimo_visto": time.time(),
                "bbox": bbox,
            }
            self.eliminar(candidatos, tracker_id, persona_id)
            texto = (
                f"{reidentificado['nombre']} | "
                f"reidentificado {similitud:.2f}"
            )
            return ResultadoVisual(box, texto, (0, 180, 255))

        ahora = time.time()
        ancho = x2 - x1
        alto = y2 - y1
        area = ancho * alto
        calidad = calcular_calidad_muestra(recortar_muestra(frame, bbox))
        if (
            rostro.nombre != "Desconocido"
            and rostro.similitud
            >= self.config_galerias.similitud_evitar_duplicado
        ):
            self.eliminar(candidatos, tracker_id, persona_id)
            texto = (
                f"Posible {rostro.nombre} | "
                "esperando mejor angulo"
            )
            return ResultadoVisual(box, texto, (160, 160, 160))
        if (
            ancho < self.config_rostro.ancho_minimo
            or alto < self.config_rostro.alto_minimo
        ):
            return ResultadoVisual(
                box,
                "Rostro desconocido | Muy pequeno",
                (0, 0, 255),
            )

        if clave not in candidatos:
            candidatos[clave] = self._crear_candidato(
                ahora,
                tracker_id,
                persona_id,
                bbox,
                frame,
                area,
                calidad,
                rostro.embedding,
            )
        else:
            candidato = candidatos[clave]
            similitud_semilla = float(
                np.dot(rostro.embedding, candidato.embedding_semilla)
            )
            if (
                similitud_semilla
                < self.config_galerias.similitud_muestra_semilla
            ):
                candidato.confirmaciones_incompatibles += 1
                if candidato.confirmaciones_incompatibles < 2:
                    candidato.ultimo_visto = ahora
                    return ResultadoVisual(
                        box,
                        "Rostro desconocido | Identidad en verificacion",
                        (160, 160, 160),
                    )
                self._reiniciar(
                    candidato,
                    ahora,
                    tracker_id,
                    persona_id,
                    bbox,
                    frame,
                    area,
                    calidad,
                    rostro.embedding,
                )
            else:
                candidato.confirmaciones_incompatibles = 0
                candidato.ultimo_visto = ahora
                candidato.muestras += 1
                candidato.rostro_tracker_id = tracker_id
                candidato.persona_id = persona_id
                candidato.bbox = bbox
                if (
                    calidad > candidato.mejor_calidad
                    or (
                        calidad == candidato.mejor_calidad
                        and area > candidato.mejor_area
                    )
                ):
                    candidato.mejor_frame = frame.copy()
                    candidato.mejor_bbox = bbox
                    candidato.mejor_area = area
                    candidato.mejor_calidad = calidad
                    candidato.mejor_embedding = rostro.embedding.copy()

        candidato = candidatos[clave]
        tiempo_visible = ahora - candidato.inicio
        texto = (
            "Rostro desconocido | Analizando... "
            f"{tiempo_visible:.1f}s"
        )
        tiempo_requerido = (
            self.config.tiempo_confirmacion
            if persona_id is not None
            else self.config.tiempo_confirmacion_sin_cuerpo
        )
        muestras_requeridas = (
            self.config.muestras_minimas
            if persona_id is not None
            else self.config.muestras_minimas_sin_cuerpo
        )
        if (
            tiempo_visible >= tiempo_requerido
            and candidato.muestras >= muestras_requeridas
            and not candidato.guardado
            and ahora - candidato.ultima_captura >= self.config.cooldown_captura
        ):
            captura = self.muestras.guardar_desconocido(
                candidato,
                tracker_id,
            )
            if captura is None:
                self._reiniciar(
                    candidato,
                    ahora,
                    tracker_id,
                    persona_id,
                    bbox,
                    frame,
                    area,
                    calidad,
                    rostro.embedding,
                    muestras=0,
                )
                return ResultadoVisual(
                    box,
                    "Rostro desconocido | Esperando mejor captura",
                    (160, 160, 160),
                )
            nombre_temporal, ruta, embedding_muestra, calidad_muestra = captura
            nombre_existente, similitud_existente, tipo_existente, reconocido = (
                comparar_con_referencias(
                    embedding_muestra,
                    referencias,
                    self.config_rostro,
                )
            )
            if reconocido:
                identidad = {
                    "nombre": nombre_existente,
                    "similitud": similitud_existente,
                    "tipo": tipo_existente,
                    "embedding": embedding_muestra.copy(),
                }
                revocados: set[int] | None = set()
                if persona_id is not None:
                    revocados = self.identidades.resolver_propietarios(
                        persona_id,
                        identidad,
                        estado.historial_personas,
                    )
                if revocados is not None:
                    with self.muestras.repositorio.transaccion():
                        ruta.unlink(missing_ok=True)
                        ruta.parent.rmdir()
                    for rostro_id in revocados:
                        estado.historial_rostros.pop(rostro_id, None)
                        self.eliminar(candidatos, tracker_id=rostro_id)
                    estado.historial_rostros[tracker_id] = {
                        **identidad,
                        "ultimo_visto": ahora,
                        "bbox": bbox,
                    }
                    if persona_id is not None:
                        persona = estado.historial_personas.setdefault(
                            persona_id,
                            {},
                        )
                        self.identidades.asignar_identidad(
                            persona,
                            identidad,
                            tracker_id,
                        )
                    candidato.ultima_captura = ahora
                    candidato.guardado = True
                    texto = (
                        f"{nombre_existente} | "
                        "reidentificado desde mejor captura "
                        f"{similitud_existente:.2f}"
                    )
                    self.registrar_evento(texto)
                    color = (
                        (0, 255, 0)
                        if tipo_existente == "oficial"
                        else (0, 255, 255)
                    )
                    return ResultadoVisual(box, texto, color)

            posible_duplicado = (
                nombre_existente != "Desconocido"
                and similitud_existente
                >= self.config_galerias.similitud_evitar_duplicado
            )
            if reconocido or posible_duplicado:
                with self.muestras.repositorio.transaccion():
                    ruta.unlink(missing_ok=True)
                    ruta.parent.rmdir()
                self._reiniciar(
                    candidato,
                    ahora,
                    tracker_id,
                    persona_id,
                    bbox,
                    frame,
                    area,
                    calidad,
                    rostro.embedding,
                    muestras=0,
                )
                estado_texto = (
                    "coincidencia ambigua"
                    if reconocido
                    else "esperando mejor angulo"
                )
                texto = (
                    f"Posible {nombre_existente} | "
                    f"{estado_texto}"
                )
                return ResultadoVisual(box, texto, (160, 160, 160))

            datos = ruta.stat()
            referencias.append(
                ReferenciaFacial(
                    nombre=nombre_temporal,
                    embedding=embedding_muestra,
                    tipo="pendiente",
                    firma_archivo=(datos.st_mtime_ns, datos.st_size),
                    ruta=ruta,
                    calidad=calidad_muestra,
                )
            )
            identidad = {
                "nombre": nombre_temporal,
                "similitud": 1.0,
                "tipo": "pendiente",
                "embedding": embedding_muestra.copy(),
            }
            estado.historial_rostros[tracker_id] = {
                **identidad,
                "ultimo_visto": ahora,
                "bbox": bbox,
            }
            if persona_id is not None:
                persona = estado.historial_personas.setdefault(persona_id, {})
                self.identidades.asignar_identidad(
                    persona,
                    identidad,
                    tracker_id,
                )
            candidato.ultima_captura = ahora
            candidato.guardado = True
            texto = f"{nombre_temporal} | Pendiente guardada"
            self.registrar_evento(texto)
        return ResultadoVisual(box, texto, (0, 0, 255))
