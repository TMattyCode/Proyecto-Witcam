import time

import numpy as np

from backend.config import ConfiguracionTracking
from backend.dominio.modelos import (
    AnalisisRostro,
    AsociacionRostroPersona,
    CandidatoDesconocido,
    DeteccionPersona,
    ReferenciaFacial,
    ResultadoVisual,
)
from backend.utilidades.geometria import calcular_iou


class GestorIdentidades:
    """Conserva las reglas corporales, contradicciones y transferencias."""

    def __init__(self, config: ConfiguracionTracking):
        self.config = config

    def actualizar_personas_visibles(
        self,
        personas: list[DeteccionPersona],
        historial_personas: dict[int, dict],
        asociaciones: dict[int, AsociacionRostroPersona],
        candidatos: dict[tuple[str, int], CandidatoDesconocido],
    ) -> None:
        ahora = time.time()
        ids_visibles = {persona.tracker_id for persona in personas}
        for persona in personas:
            persona_id = persona.tracker_id
            datos = historial_personas.get(persona_id)
            if datos is None or "nombre" not in datos:
                candidatas = []
                for id_anterior, anteriores in historial_personas.items():
                    tiene_continuidad = (
                        "nombre" in anteriores
                        or ("persona", int(id_anterior)) in candidatos
                    )
                    if (
                        id_anterior == persona_id
                        or id_anterior in ids_visibles
                        or not tiene_continuidad
                        or ahora - anteriores.get("ultimo_visto", 0)
                        > self.config.tolerancia_identidad_corporal
                    ):
                        continue
                    iou = calcular_iou(
                        persona.bbox,
                        anteriores.get("bbox", (0, 0, 0, 0)),
                    )
                    if iou >= self.config.iou_reasociacion_cuerpo:
                        candidatas.append((iou, id_anterior, anteriores))
                if candidatas:
                    _, id_anterior, anteriores = max(
                        candidatas,
                        key=lambda candidata: candidata[0],
                    )
                    historial_personas[persona_id] = anteriores
                    historial_personas.pop(id_anterior, None)
                    for asociacion in asociaciones.values():
                        if asociacion.persona_id == id_anterior:
                            asociacion.persona_id = persona_id
                    clave_anterior = ("persona", int(id_anterior))
                    clave_nueva = ("persona", int(persona_id))
                    if (
                        clave_anterior in candidatos
                        and clave_nueva not in candidatos
                    ):
                        candidatos[clave_nueva] = candidatos.pop(clave_anterior)
                    datos = anteriores
            if datos is None:
                datos = historial_personas.setdefault(persona_id, {})
            datos["ultimo_visto"] = ahora
            datos["bbox"] = persona.bbox
            candidato = candidatos.get(("persona", int(persona_id)))
            if candidato is not None:
                candidato.ultimo_visto = ahora

    def reconciliar_referencias_activas(
        self,
        mapa: dict[tuple[str, str], tuple[str, str]],
        historial_rostros: dict[int, dict],
        historial_personas: dict[int, dict],
        candidatos: dict[tuple[str, int], CandidatoDesconocido],
    ) -> None:
        rostros_revocados = set()
        for persona in historial_personas.values():
            nombre = persona.get("nombre")
            tipo = persona.get("tipo")
            if nombre is not None and tipo is not None:
                nueva = mapa.get((nombre, tipo))
                if nueva is None:
                    rostros_revocados.update(self.revocar_identidad(persona))
                else:
                    persona["nombre"], persona["tipo"] = nueva
            for campo in ("identidad_candidata", "datos_cambio"):
                candidata = persona.get(campo)
                if candidata is None:
                    continue
                nueva = mapa.get(
                    (candidata.get("nombre"), candidata.get("tipo"))
                )
                if nueva is None:
                    persona.pop(campo, None)
                    if campo == "datos_cambio":
                        persona["cambio_candidato"] = None
                        persona["confirmaciones_cambio"] = 0
                else:
                    candidata["nombre"], candidata["tipo"] = nueva
                    if campo == "datos_cambio":
                        persona["cambio_candidato"] = candidata["nombre"]
        for rostro_id, historial in list(historial_rostros.items()):
            nueva = mapa.get(
                (historial.get("nombre"), historial.get("tipo"))
            )
            if nueva is None or rostro_id in rostros_revocados:
                historial_rostros.pop(rostro_id, None)
                candidatos.pop(("rostro", int(rostro_id)), None)
                continue
            historial["nombre"], historial["tipo"] = nueva

    def buscar_persona_para_rostro(
        self,
        caja_rostro: tuple[int, int, int, int],
        personas: list[DeteccionPersona],
        persona_preferida_id: int | None = None,
        personas_excluidas: set[int] | None = None,
    ) -> DeteccionPersona | None:
        rx1, ry1, rx2, ry2 = caja_rostro
        centro_x = (rx1 + rx2) / 2.0
        centro_y = (ry1 + ry2) / 2.0
        area_rostro = max(1.0, (rx2 - rx1) * (ry2 - ry1))
        candidatas = []
        excluidas = personas_excluidas or set()
        for persona in personas:
            if persona.tracker_id in excluidas:
                continue
            px1, py1, px2, py2 = persona.bbox
            ancho = max(1, px2 - px1)
            alto = max(1, py2 - py1)
            limite_cabeza_y = (
                py1 + alto * self.config.limite_vertical_cabeza_cuerpo
            )
            if not (
                px1 <= centro_x <= px2
                and py1 <= centro_y <= limite_cabeza_y
            ):
                continue
            inter_x1 = max(rx1, px1)
            inter_y1 = max(ry1, py1)
            inter_x2 = min(rx2, px2)
            inter_y2 = min(ry2, py2)
            area_interseccion = max(0.0, inter_x2 - inter_x1) * max(
                0.0,
                inter_y2 - inter_y1,
            )
            proporcion_dentro = area_interseccion / area_rostro
            if (
                proporcion_dentro
                < self.config.proporcion_minima_rostro_en_cuerpo
            ):
                continue
            centro_cabeza_x = px1 + ancho / 2.0
            centro_cabeza_y = py1 + alto * 0.20
            distancia = (
                abs(centro_x - centro_cabeza_x) / ancho
                + abs(centro_y - centro_cabeza_y) / alto
                + (1.0 - proporcion_dentro) * 0.5
            )
            candidatas.append((distancia, persona))
        if not candidatas:
            return None
        mejor_distancia, mejor_persona = min(
            candidatas,
            key=lambda candidata: candidata[0],
        )
        preferida = next(
            (
                candidata
                for candidata in candidatas
                if candidata[1].tracker_id == persona_preferida_id
            ),
            None,
        )
        if (
            preferida is not None
            and mejor_persona.tracker_id != persona_preferida_id
            and mejor_distancia + self.config.margen_cambio_asociacion
            >= preferida[0]
        ):
            return preferida[1]
        return mejor_persona

    def registrar_identidad(
        self,
        persona_id: int,
        identidad: AnalisisRostro,
        historial_personas: dict[int, dict],
        rostro_tracker_id: int,
    ) -> set[int]:
        if not identidad.reconocido:
            return set()
        if (
            not identidad.nombre
            or identidad.embedding is None
            or identidad.tipo is None
        ):
            return set()
        similitud = float(identidad.similitud)
        datos_identidad = {
            "nombre": identidad.nombre,
            "similitud": similitud,
            "tipo": identidad.tipo,
            "embedding": identidad.embedding.copy(),
        }
        persona = historial_personas.setdefault(persona_id, {})
        if "nombre" not in persona:
            if similitud < self.config.similitud_identidad_inicial:
                persona.pop("identidad_candidata", None)
                return set()
            candidata = persona.get("identidad_candidata")
            if candidata is not None and candidata["nombre"] == identidad.nombre:
                candidata["confirmaciones"] += 1
                if similitud >= candidata["similitud"]:
                    candidata.update(datos_identidad)
            else:
                candidata = {**datos_identidad, "confirmaciones": 1}
                persona["identidad_candidata"] = candidata
            if (
                candidata["confirmaciones"]
                < self.config.confirmaciones_identidad_inicial
            ):
                return set()
            revocados = self.resolver_propietarios(
                persona_id,
                candidata,
                historial_personas,
            )
            if revocados is None:
                return set()
            self.asignar_identidad(persona, candidata, rostro_tracker_id)
            return revocados
        if identidad.nombre == persona["nombre"]:
            if similitud >= persona["similitud"]:
                persona.update(datos_identidad)
            persona["ultima_evidencia_facial"] = time.time()
            persona.setdefault("rostros_asociados", set()).add(
                rostro_tracker_id
            )
            persona["cambio_candidato"] = None
            persona["confirmaciones_cambio"] = 0
            return set()
        if similitud < self.config.similitud_cambio_identidad:
            persona["cambio_candidato"] = None
            persona["confirmaciones_cambio"] = 0
            return set()
        if persona.get("cambio_candidato") == identidad.nombre:
            persona["confirmaciones_cambio"] += 1
            if similitud >= persona["datos_cambio"]["similitud"]:
                persona["datos_cambio"].update(datos_identidad)
        else:
            persona["cambio_candidato"] = identidad.nombre
            persona["confirmaciones_cambio"] = 1
            persona["datos_cambio"] = datos_identidad
        if (
            persona["confirmaciones_cambio"]
            < self.config.confirmaciones_cambio_identidad
        ):
            return set()
        nueva = persona["datos_cambio"]
        revocados = self.resolver_propietarios(
            persona_id,
            nueva,
            historial_personas,
        )
        if revocados is None:
            return set()
        revocados.update(self.revocar_identidad(persona))
        self.asignar_identidad(persona, nueva, rostro_tracker_id)
        return revocados

    def actualizar_contradiccion(
        self,
        persona: dict,
        rostro: AnalisisRostro | None,
        referencias: list[ReferenciaFacial],
    ) -> bool:
        if (
            "nombre" not in persona
            or rostro is None
            or not rostro.reconocimiento_ejecutado
            or not rostro.evaluable
            or rostro.embedding is None
        ):
            return persona.get("identidad_suspendida", False)
        similitudes_propias = [
            float(np.dot(rostro.embedding, referencia.embedding))
            for referencia in referencias
            if referencia.nombre == persona["nombre"]
            and referencia.tipo == persona["tipo"]
        ]
        mejor_propia = max(similitudes_propias) if similitudes_propias else -1.0
        otra_fuerte = (
            rostro.reconocido
            and rostro.nombre != persona["nombre"]
            and rostro.similitud
            >= self.config.similitud_otra_identidad_fuerte
        )
        incompatible = (
            mejor_propia < self.config.similitud_maxima_incompatible
            or otra_fuerte
        )
        confirma = rostro.reconocido and rostro.nombre == persona["nombre"]
        if confirma:
            persona["identidad_suspendida"] = False
            persona["confirmaciones_contradiccion"] = 0
            return False
        if not incompatible:
            persona["confirmaciones_contradiccion"] = 0
            return persona.get("identidad_suspendida", False)
        persona["confirmaciones_contradiccion"] = (
            persona.get("confirmaciones_contradiccion", 0) + 1
        )
        if (
            persona["confirmaciones_contradiccion"]
            >= self.config.confirmaciones_contradiccion
        ):
            persona["identidad_suspendida"] = True
        return persona.get("identidad_suspendida", False)

    def resolver_propietarios(
        self,
        persona_id: int,
        nueva_identidad: dict,
        historial_personas: dict[int, dict],
    ) -> set[int] | None:
        ahora = time.time()
        propietarios = [
            datos
            for otro_id, datos in historial_personas.items()
            if otro_id != persona_id
            and datos.get("nombre") == nueva_identidad["nombre"]
        ]
        revocados = set()
        for propietario in propietarios:
            activo = (
                ahora - propietario.get("ultimo_visto", 0)
                <= self.config.tolerancia_identidad_corporal
            )
            evidencia_mas_fuerte = (
                nueva_identidad["similitud"]
                >= propietario.get("similitud", -1.0)
                + self.config.margen_traspaso_identidad
            )
            suficiente = (
                nueva_identidad["similitud"]
                >= self.config.similitud_traspaso_identidad
            )
            if not suficiente or (activo and not evidencia_mas_fuerte):
                return None
        for propietario in propietarios:
            revocados.update(self.revocar_identidad(propietario))
        return revocados

    @staticmethod
    def revocar_identidad(persona: dict) -> set[int]:
        asociados = set(persona.get("rostros_asociados", set()))
        for campo in (
            "nombre",
            "similitud",
            "tipo",
            "embedding",
            "ultima_evidencia_facial",
            "rostros_asociados",
            "identidad_candidata",
            "cambio_candidato",
            "confirmaciones_cambio",
            "datos_cambio",
            "identidad_suspendida",
            "confirmaciones_contradiccion",
        ):
            persona.pop(campo, None)
        return asociados

    @staticmethod
    def asignar_identidad(
        persona: dict,
        identidad: dict,
        rostro_tracker_id: int,
    ) -> None:
        persona.update(
            {
                "nombre": identidad["nombre"],
                "similitud": identidad["similitud"],
                "tipo": identidad["tipo"],
                "embedding": identidad["embedding"].copy(),
                "ultima_evidencia_facial": time.time(),
                "rostros_asociados": {rostro_tracker_id},
                "cambio_candidato": None,
                "confirmaciones_cambio": 0,
                "identidad_suspendida": False,
                "confirmaciones_contradiccion": 0,
            }
        )
        persona.pop("identidad_candidata", None)
        persona.pop("datos_cambio", None)

    @staticmethod
    def crear_resultados_personas(
        personas: list[DeteccionPersona],
        resultados_rostros: list[ResultadoVisual],
        historial_personas: dict[int, dict],
    ) -> list[ResultadoVisual]:
        resultados = []
        for persona in personas:
            x1, y1, x2, y2 = persona.bbox
            tiene_rostro = any(
                x1 <= (resultado.bbox[0] + resultado.bbox[2]) / 2.0 <= x2
                and y1 <= (resultado.bbox[1] + resultado.bbox[3]) / 2.0 <= y2
                for resultado in resultados_rostros
            )
            identidad = historial_personas.get(persona.tracker_id, {})
            if identidad.get("identidad_suspendida"):
                estado = "identidad en verificacion"
                etiqueta = "Persona detectada"
                color = (160, 160, 160)
            elif "nombre" in identidad:
                etiqueta = identidad["nombre"]
                estado = (
                    "Reconocida"
                    if identidad["tipo"] == "oficial"
                    else "Pendiente"
                )
                color = (
                    (0, 255, 0)
                    if identidad["tipo"] == "oficial"
                    else (0, 255, 255)
                )
            else:
                etiqueta = "Persona detectada"
                estado = (
                    "rostro detectado" if tiene_rostro else "sin rostro visible"
                )
                color = (255, 140, 0)
            resultados.append(
                ResultadoVisual(
                    persona.bbox,
                    f"{etiqueta} | {estado}",
                    color,
                )
            )
        return resultados

    def buscar_identidad_reciente(
        self,
        tracker_id: int,
        embedding: np.ndarray,
        bbox: tuple[int, int, int, int],
        historial_rostros: dict[int, dict],
        umbral_similitud: float,
    ) -> tuple[dict | None, float]:
        ahora = time.time()
        mejor = None
        mejor_similitud = -1.0
        for otro_id, historial in historial_rostros.items():
            if otro_id == tracker_id or "embedding" not in historial:
                continue
            if (
                ahora - historial["ultimo_visto"]
                > self.config.tolerancia_oclusion
            ):
                continue
            similitud = float(np.dot(embedding, historial["embedding"]))
            iou = calcular_iou(bbox, historial.get("bbox", bbox))
            if (
                similitud >= self.config.similitud_reidentificacion
                and (
                    iou >= self.config.iou_reidentificacion
                    or similitud >= umbral_similitud
                )
                and similitud > mejor_similitud
            ):
                mejor = historial
                mejor_similitud = similitud
        return mejor, mejor_similitud

    def buscar_identidad_por_posicion(
        self,
        tracker_id: int,
        bbox: tuple[int, int, int, int],
        historial_rostros: dict[int, dict],
    ) -> dict | None:
        ahora = time.time()
        mejor = None
        mejor_iou = self.config.iou_reidentificacion
        for otro_id, historial in historial_rostros.items():
            if otro_id == tracker_id:
                continue
            if (
                ahora - historial["ultimo_visto"]
                > self.config.tolerancia_oclusion
            ):
                continue
            iou = calcular_iou(bbox, historial.get("bbox", bbox))
            if iou >= mejor_iou:
                mejor = historial
                mejor_iou = iou
        return mejor
