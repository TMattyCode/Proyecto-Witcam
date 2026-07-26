import time

import cv2
import numpy as np

from backend.config import ConfiguracionApp
from backend.dominio.modelos import (
    AnalisisRostro,
    AsociacionRostroPersona,
    DeteccionPersona,
    EstadoSeguimiento,
    ReferenciaFacial,
    ResultadoVisual,
)
from backend.galerias.muestras import GestorMuestras
from backend.galerias.referencias import comparar_con_referencias
from backend.ia.desconocidos import GestorDesconocidos
from backend.ia.identidades import GestorIdentidades
from backend.ia.interfaces import (
    AnalizadorFrame,
    DetectorPersonas,
    DetectorRostros,
    RastreadorObjetos,
    ReconocedorFacial,
)
from backend.utilidades.geometria import calcular_iou
from backend.utilidades.imagenes import normalizar_vector
from backend.utilidades.rostros import evaluar_calidad_rostro


class PipelineReconocimiento:
    """Orquesta modelos y reglas sin depender de proveedores concretos."""

    def __init__(
        self,
        config: ConfiguracionApp,
        detector_rostros: DetectorRostros,
        reconocedor: ReconocedorFacial,
        rastreador_rostros: RastreadorObjetos,
        identidades: GestorIdentidades,
        desconocidos: GestorDesconocidos,
        muestras: GestorMuestras,
        detector_personas: DetectorPersonas | None = None,
        rastreador_personas: RastreadorObjetos | None = None,
        analizadores_adicionales: list[AnalizadorFrame] | None = None,
    ):
        self.config = config
        self.detector_rostros = detector_rostros
        self.reconocedor = reconocedor
        self.rastreador_rostros = rastreador_rostros
        self.identidades = identidades
        self.desconocidos = desconocidos
        self.muestras = muestras
        self.detector_personas = detector_personas
        self.rastreador_personas = rastreador_personas
        self.analizadores_adicionales = analizadores_adicionales or []

    def detectar_personas(self, frame: np.ndarray) -> list[DeteccionPersona]:
        if self.detector_personas is None or self.rastreador_personas is None:
            return []
        detecciones = self.detector_personas.detectar(frame)
        cajas = [caja for caja, _ in detecciones]
        confianzas = [confianza for _, confianza in detecciones]
        return self.rastreador_personas.actualizar(cajas, confianzas)

    def analizar_frame(
        self,
        frame: np.ndarray,
        referencias: list[ReferenciaFacial],
        realizar_reconocimiento: bool,
        personas: list[DeteccionPersona],
        estado: EstadoSeguimiento,
    ) -> list[ResultadoVisual]:
        analisis, cajas, confianzas = self._preparar_rostros(
            frame,
            referencias,
            realizar_reconocimiento,
        )
        rastreados = self.rastreador_rostros.actualizar(cajas, confianzas)
        if not rastreados:
            return []

        rostros_visibles = {rostro.tracker_id for rostro in rastreados}
        rastreados.sort(
            key=lambda rostro: (
                rostro.tracker_id not in estado.asociaciones_rostro_persona,
                rostro.tracker_id,
            )
        )
        personas_asignadas: set[int] = set()
        resultados = []
        for rostro_rastreado in rastreados:
            dato, mejor_iou = self._buscar_analisis(
                rostro_rastreado.bbox,
                analisis,
            )
            resultado = self._resolver_rostro(
                frame,
                rostro_rastreado,
                dato,
                mejor_iou,
                referencias,
                personas,
                personas_asignadas,
                rostros_visibles,
                estado,
            )
            resultados.append(resultado)
        for analizador in self.analizadores_adicionales:
            analizador.analizar(frame)
        return resultados

    def _preparar_rostros(
        self,
        frame: np.ndarray,
        referencias: list[ReferenciaFacial],
        realizar_reconocimiento: bool,
    ) -> tuple[list[AnalisisRostro], list[np.ndarray], list[float]]:
        alto_original, ancho_original = frame.shape[:2]
        video = self.config.video
        factor = min(
            video.ancho_analisis / ancho_original,
            video.alto_analisis / alto_original,
        )
        ancho_ia = max(1, round(ancho_original * factor))
        alto_ia = max(1, round(alto_original * factor))
        frame_ia = cv2.resize(frame, (ancho_ia, alto_ia))
        escala_x = ancho_original / ancho_ia
        escala_y = alto_original / alto_ia

        detecciones = self.detector_rostros.detectar(frame_ia)
        analisis: list[AnalisisRostro] = []
        cajas: list[np.ndarray] = []
        confianzas: list[float] = []
        puntos_analizables: list[np.ndarray] = []
        indices_analizables: list[int] = []
        for deteccion in detecciones:
            x1, y1, x2, y2 = deteccion.bbox
            bbox = (
                int(x1 * escala_x),
                int(y1 * escala_y),
                int(x2 * escala_x),
                int(y2 * escala_y),
            )
            puntos = None
            if deteccion.puntos_clave is not None:
                puntos = np.asarray(
                    deteccion.puntos_clave,
                    dtype=np.float32,
                ).copy()
                puntos[:, 0] *= escala_x
                puntos[:, 1] *= escala_y
            evaluable, motivo = evaluar_calidad_rostro(
                bbox,
                puntos,
                deteccion.confianza,
                self.config.rostro,
            )
            cajas.append(np.asarray(bbox, dtype=np.float32))
            confianzas.append(deteccion.confianza)
            analisis.append(
                AnalisisRostro(
                    bbox=bbox,
                    evaluable=evaluable,
                    motivo_no_evaluable=motivo or "",
                    reconocimiento_ejecutado=realizar_reconocimiento,
                )
            )
            if realizar_reconocimiento and evaluable and puntos is not None:
                puntos_analizables.append(puntos)
                indices_analizables.append(len(analisis) - 1)

        embeddings = (
            self.reconocedor.generar_embeddings(frame, puntos_analizables)
            if puntos_analizables
            else []
        )
        for indice, embedding in zip(indices_analizables, embeddings):
            normalizado = normalizar_vector(embedding)
            nombre, similitud, tipo, reconocido = comparar_con_referencias(
                normalizado,
                referencias,
                self.config.rostro,
            )
            dato = analisis[indice]
            dato.embedding = normalizado
            dato.nombre = nombre
            dato.similitud = similitud
            dato.tipo = tipo
            dato.reconocido = reconocido
        return analisis, cajas, confianzas

    @staticmethod
    def _buscar_analisis(
        bbox: tuple[int, int, int, int],
        analisis: list[AnalisisRostro],
    ) -> tuple[AnalisisRostro | None, float]:
        mejor = None
        mejor_iou = 0.0
        for dato in analisis:
            iou = calcular_iou(bbox, dato.bbox)
            if iou > mejor_iou:
                mejor = dato
                mejor_iou = iou
        return mejor, mejor_iou

    def _resolver_rostro(
        self,
        frame: np.ndarray,
        rostro_rastreado: DeteccionPersona,
        dato: AnalisisRostro | None,
        mejor_iou: float,
        referencias: list[ReferenciaFacial],
        personas: list[DeteccionPersona],
        personas_asignadas: set[int],
        rostros_visibles: set[int],
        estado: EstadoSeguimiento,
    ) -> ResultadoVisual:
        tracker_id = rostro_rastreado.tracker_id
        box = rostro_rastreado.bbox
        persona = self.identidades.buscar_persona_para_rostro(
            box,
            personas,
            self._persona_preferida(tracker_id, estado),
            personas_asignadas,
        )
        persona_id = persona.tracker_id if persona is not None else None
        if persona_id is not None:
            personas_asignadas.add(persona_id)
            estado.asociaciones_rostro_persona[tracker_id] = (
                AsociacionRostroPersona(persona_id, time.time())
            )
            resultado = self._resolver_identidad_corporal(
                frame,
                tracker_id,
                box,
                dato,
                persona_id,
                referencias,
                estado,
            )
            if resultado is not None:
                return resultado

        if dato is None or mejor_iou <= 0.3:
            return self._resultado_sin_match(tracker_id, box, estado)
        if not dato.evaluable:
            return self._resultado_no_evaluable(
                tracker_id,
                box,
                dato,
                persona_id,
                estado,
            )
        if not dato.reconocimiento_ejecutado:
            return self._resultado_seguimiento(
                tracker_id,
                box,
                dato,
                persona_id,
                estado,
            )
        if dato.embedding is None:
            return ResultadoVisual(
                box,
                f"ID {tracker_id} | Sin embedding",
                (0, 0, 255),
            )
        return self._resolver_reconocimiento(
            frame,
            tracker_id,
            box,
            dato,
            persona_id,
            referencias,
            rostros_visibles,
            estado,
        )

    @staticmethod
    def _persona_preferida(
        tracker_id: int,
        estado: EstadoSeguimiento,
    ) -> int | None:
        asociacion = estado.asociaciones_rostro_persona.get(tracker_id)
        return asociacion.persona_id if asociacion is not None else None

    def _resolver_identidad_corporal(
        self,
        frame: np.ndarray,
        tracker_id: int,
        box: tuple[int, int, int, int],
        dato: AnalisisRostro | None,
        persona_id: int,
        referencias: list[ReferenciaFacial],
        estado: EstadoSeguimiento,
    ) -> ResultadoVisual | None:
        if dato is not None and dato.reconocido:
            revocados = self.identidades.registrar_identidad(
                persona_id,
                dato,
                estado.historial_personas,
                tracker_id,
            )
            for rostro_id in revocados:
                estado.historial_rostros.pop(rostro_id, None)
                self.desconocidos.eliminar(
                    estado.candidatos_desconocidos,
                    tracker_id=rostro_id,
                )
        identidad = estado.historial_personas.get(persona_id)
        if identidad is not None and "nombre" in identidad:
            suspendida = self.identidades.actualizar_contradiccion(
                identidad,
                dato,
                referencias,
            )
            if suspendida:
                liberados = self.identidades.revocar_identidad(identidad)
                liberados.add(tracker_id)
                for rostro_id in liberados:
                    estado.historial_rostros.pop(rostro_id, None)
                    self.desconocidos.eliminar(
                        estado.candidatos_desconocidos,
                        tracker_id=rostro_id,
                    )
                self.desconocidos.eliminar(
                    estado.candidatos_desconocidos,
                    persona_id=persona_id,
                )
            else:
                if (
                    identidad["tipo"] == "pendiente"
                    and dato is not None
                    and dato.embedding is not None
                ):
                    self.muestras.agregar(
                        frame,
                        box,
                        identidad["nombre"],
                        dato.embedding,
                        referencias,
                    )
                identidad.setdefault("rostros_asociados", set()).add(
                    tracker_id
                )
                estado.historial_rostros[tracker_id] = {
                    "nombre": identidad["nombre"],
                    "similitud": identidad["similitud"],
                    "tipo": identidad["tipo"],
                    "ultimo_visto": time.time(),
                    "embedding": identidad["embedding"].copy(),
                    "bbox": box,
                }
                self.desconocidos.eliminar(
                    estado.candidatos_desconocidos,
                    tracker_id,
                    persona_id,
                )
                color = (
                    (0, 255, 0)
                    if identidad["tipo"] == "oficial"
                    else (0, 255, 255)
                )
                return ResultadoVisual(
                    box,
                    f"ID {tracker_id} | {identidad['nombre']} "
                    "| identidad corporal",
                    color,
                )
        if dato is not None and dato.reconocido:
            pertenece_a_otra = any(
                otro_id != persona_id
                and otra.get("nombre") == dato.nombre
                for otro_id, otra in estado.historial_personas.items()
            )
            etiqueta = (
                "coincidencia ambigua"
                if pertenece_a_otra
                else "identidad por confirmar"
            )
            return ResultadoVisual(
                box,
                f"ID {tracker_id} | {dato.nombre} | {etiqueta}",
                (160, 160, 160),
            )
        return None

    @staticmethod
    def _resultado_sin_match(
        tracker_id: int,
        box: tuple[int, int, int, int],
        estado: EstadoSeguimiento,
    ) -> ResultadoVisual:
        historial = estado.historial_rostros.get(tracker_id)
        if historial is None:
            return ResultadoVisual(
                box,
                f"ID {tracker_id} | Sin match",
                (0, 0, 255),
            )
        color = (
            (0, 255, 0)
            if historial["tipo"] == "oficial"
            else (0, 255, 255)
        )
        texto = (
            f"ID {tracker_id} | {historial['nombre']} | "
            f"{historial['similitud']:.2f}"
        )
        return ResultadoVisual(box, texto, color)

    def _resultado_no_evaluable(
        self,
        tracker_id: int,
        box: tuple[int, int, int, int],
        dato: AnalisisRostro,
        persona_id: int | None,
        estado: EstadoSeguimiento,
    ) -> ResultadoVisual:
        historial = estado.historial_rostros.get(tracker_id)
        if historial is None:
            historial = self.identidades.buscar_identidad_por_posicion(
                tracker_id,
                dato.bbox,
                estado.historial_rostros,
            )
            if historial is not None:
                estado.historial_rostros[tracker_id] = {
                    **historial,
                    "ultimo_visto": time.time(),
                    "bbox": dato.bbox,
                }
        if historial is None:
            candidato = estado.candidatos_desconocidos.get(
                self.desconocidos.clave(tracker_id, persona_id)
            )
            if candidato is not None:
                candidato.ultimo_visto = time.time()
                candidato.bbox = dato.bbox
            return ResultadoVisual(
                box,
                f"ID {tracker_id} | No evaluable | "
                f"{dato.motivo_no_evaluable}",
                (160, 160, 160),
            )
        self.desconocidos.eliminar(
            estado.candidatos_desconocidos,
            tracker_id,
            persona_id,
        )
        historial["ultimo_visto"] = time.time()
        historial["bbox"] = dato.bbox
        texto = (
            f"ID {tracker_id} | {historial['nombre']} | "
            f"{dato.motivo_no_evaluable}"
        )
        return ResultadoVisual(box, texto, (0, 180, 255))

    def _resultado_seguimiento(
        self,
        tracker_id: int,
        box: tuple[int, int, int, int],
        dato: AnalisisRostro,
        persona_id: int | None,
        estado: EstadoSeguimiento,
    ) -> ResultadoVisual:
        historial = estado.historial_rostros.get(tracker_id)
        if historial is None:
            historial = self.identidades.buscar_identidad_por_posicion(
                tracker_id,
                dato.bbox,
                estado.historial_rostros,
            )
        if historial is not None:
            historial["ultimo_visto"] = time.time()
            historial["bbox"] = dato.bbox
            estado.historial_rostros[tracker_id] = historial
            self.desconocidos.eliminar(
                estado.candidatos_desconocidos,
                tracker_id,
                persona_id,
            )
            color = (
                (0, 255, 0)
                if historial["tipo"] == "oficial"
                else (0, 255, 255)
            )
            return ResultadoVisual(
                box,
                f"ID {tracker_id} | {historial['nombre']} | seguimiento",
                color,
            )
        candidato = estado.candidatos_desconocidos.get(
            self.desconocidos.clave(tracker_id, persona_id)
        )
        if candidato is not None:
            ahora = time.time()
            candidato.ultimo_visto = ahora
            candidato.bbox = dato.bbox
            tiempo_visible = ahora - candidato.inicio
            return ResultadoVisual(
                box,
                f"ID {tracker_id} | Desconocido en seguimiento... "
                f"{tiempo_visible:.1f}s",
                (160, 160, 160),
            )
        return ResultadoVisual(
            box,
            f"ID {tracker_id} | Rostro detectado",
            (160, 160, 160),
        )

    def _resolver_reconocimiento(
        self,
        frame: np.ndarray,
        tracker_id: int,
        box: tuple[int, int, int, int],
        dato: AnalisisRostro,
        persona_id: int | None,
        referencias: list[ReferenciaFacial],
        rostros_visibles: set[int],
        estado: EstadoSeguimiento,
    ) -> ResultadoVisual:
        historial = estado.historial_rostros.get(tracker_id)
        if (
            dato.reconocido
            and
            historial is not None
            and dato.nombre != historial["nombre"]
            and time.time() - historial["ultimo_visto"]
            <= self.config.tracking.tolerancia_oclusion
        ):
            historial["ultimo_visto"] = time.time()
            historial["bbox"] = dato.bbox
            self.desconocidos.eliminar(
                estado.candidatos_desconocidos,
                tracker_id,
                persona_id,
            )
            color = (
                (0, 255, 0)
                if historial["tipo"] == "oficial"
                else (0, 255, 255)
            )
            return ResultadoVisual(
                box,
                f"ID {tracker_id} | {historial['nombre']} | "
                "identidad estable",
                color,
            )
        if not dato.reconocido:
            return self.desconocidos.manejar(
                frame,
                tracker_id,
                box,
                dato,
                referencias,
                estado,
                persona_id,
                rostros_visibles,
            )
        if persona_id is None:
            asignada = any(
                time.time() - persona.get("ultimo_visto", 0)
                <= self.config.tracking.tolerancia_identidad_corporal
                and persona.get("nombre") == dato.nombre
                for persona in estado.historial_personas.values()
            )
            if asignada:
                self.desconocidos.eliminar(
                    estado.candidatos_desconocidos,
                    tracker_id,
                    persona_id,
                )
                return ResultadoVisual(
                    box,
                    f"ID {tracker_id} | {dato.nombre} | "
                    "coincidencia ambigua",
                    (160, 160, 160),
                )
        if dato.tipo == "pendiente" and dato.embedding is not None:
            self.muestras.agregar(
                frame,
                dato.bbox,
                dato.nombre,
                dato.embedding,
                referencias,
            )
        estado.historial_rostros[tracker_id] = {
            "nombre": dato.nombre,
            "similitud": dato.similitud,
            "tipo": dato.tipo,
            "ultimo_visto": time.time(),
            "embedding": dato.embedding.copy(),
            "bbox": dato.bbox,
        }
        self.desconocidos.eliminar(
            estado.candidatos_desconocidos,
            tracker_id,
            persona_id,
        )
        color = (
            (0, 255, 0)
            if dato.tipo == "oficial"
            else (0, 255, 255)
        )
        texto = (
            f"ID {tracker_id} | {dato.nombre} | {dato.similitud:.2f}"
            if dato.tipo == "oficial"
            else f"ID {tracker_id} | Pendiente: {dato.nombre} | "
            f"{dato.similitud:.2f}"
        )
        return ResultadoVisual(box, texto, color)
