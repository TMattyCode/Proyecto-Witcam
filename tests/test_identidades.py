import time
import unittest
from dataclasses import replace

import numpy as np

from interfaz_prueba import app
from backend.config import (
    ConfiguracionDesconocidos,
    ConfiguracionGalerias,
    ConfiguracionRostro,
    ConfiguracionTracking,
)
from backend.dominio.modelos import (
    AnalisisRostro,
    DeteccionPersona,
    EstadoSeguimiento,
    ReferenciaFacial,
)
from backend.ia.desconocidos import GestorDesconocidos
from backend.ia.identidades import GestorIdentidades


class MuestrasFalsas:
    def agregar(self, *args, **kwargs):
        return False


class PruebasIdentidades(unittest.TestCase):
    def setUp(self):
        self.config = ConfiguracionTracking()
        self.gestor = GestorIdentidades(self.config)

    def test_identidad_inicial_requiere_confirmaciones(self):
        historial = {}
        rostro = AnalisisRostro(
            bbox=(10, 10, 80, 80),
            embedding=np.array([1.0, 0.0]),
            nombre="Matias",
            similitud=0.70,
            tipo="oficial",
            reconocido=True,
        )
        self.assertEqual(
            self.gestor.registrar_identidad(1, rostro, historial, 10),
            set(),
        )
        self.assertNotIn("nombre", historial[1])
        self.gestor.registrar_identidad(1, rostro, historial, 10)
        self.assertEqual(historial[1]["nombre"], "Matias")

    def test_una_identidad_activa_no_se_asigna_a_dos_cuerpos(self):
        ahora = time.time()
        historial = {
            1: {
                "nombre": "Matias",
                "similitud": 0.70,
                "tipo": "oficial",
                "embedding": np.array([1.0, 0.0]),
                "ultimo_visto": ahora,
            },
            2: {},
        }
        nueva = {
            "nombre": "Matias",
            "similitud": 0.75,
            "tipo": "oficial",
            "embedding": np.array([1.0, 0.0]),
        }
        self.assertIsNone(
            self.gestor.resolver_propietarios(2, nueva, historial)
        )

    def test_candidato_corporal_sobrevive_al_cambio_de_tracker_facial(self):
        desconocidos = GestorDesconocidos(
            replace(
                ConfiguracionDesconocidos(),
                tiempo_confirmacion=100.0,
            ),
            ConfiguracionGalerias(),
            ConfiguracionRostro(),
            self.config,
            MuestrasFalsas(),
            self.gestor,
            lambda evento: None,
        )
        estado = EstadoSeguimiento()
        rostro = AnalisisRostro(
            bbox=(30, 20, 90, 90),
            embedding=np.array([1.0, 0.0]),
            nombre="Desconocido",
            similitud=0.1,
            evaluable=True,
            reconocimiento_ejecutado=True,
        )
        frame = np.zeros((160, 160, 3), dtype=np.uint8)
        desconocidos.manejar(
            frame,
            10,
            rostro.bbox,
            rostro,
            [],
            estado,
            5,
            {10},
        )
        candidato = estado.candidatos_desconocidos[("persona", 5)]
        desconocidos.manejar(
            frame,
            11,
            rostro.bbox,
            rostro,
            [],
            estado,
            5,
            {11},
        )
        self.assertIs(
            estado.candidatos_desconocidos[("persona", 5)],
            candidato,
        )
        self.assertEqual(candidato.rostro_tracker_id, 11)

    def test_asociacion_prefiere_el_cuerpo_que_contiene_la_cabeza(self):
        personas = [
            DeteccionPersona((0, 0, 100, 220), 1),
            DeteccionPersona((120, 0, 220, 220), 2),
        ]
        persona = self.gestor.buscar_persona_para_rostro(
            (145, 20, 195, 80),
            personas,
        )
        self.assertEqual(persona.tracker_id, 2)

    def test_contradiccion_conserva_resultado_de_v1(self):
        persona_v1 = {
            "nombre": "Matias",
            "similitud": 0.8,
            "tipo": "oficial",
            "embedding": np.array([1.0, 0.0]),
        }
        persona_v2 = dict(persona_v1)
        dato_v1 = {
            "nombre": "Otra",
            "similitud": 0.7,
            "reconocido": True,
            "reconocimiento_ejecutado": True,
            "evaluable": True,
            "embedding": np.array([0.0, 1.0]),
        }
        dato_v2 = AnalisisRostro(
            bbox=(0, 0, 100, 100),
            nombre="Otra",
            similitud=0.7,
            reconocido=True,
            reconocimiento_ejecutado=True,
            evaluable=True,
            embedding=np.array([0.0, 1.0]),
        )
        referencias_v1 = [
            {
                "nombre": "Matias",
                "tipo": "oficial",
                "embedding": np.array([1.0, 0.0]),
            }
        ]
        referencias_v2 = [
            ReferenciaFacial(
                "Matias",
                np.array([1.0, 0.0]),
                "oficial",
            )
        ]
        resultados_v1 = []
        resultados_v2 = []
        for _ in range(2):
            resultados_v1.append(
                app.MotorReconocimiento
                ._actualizar_contradiccion_identidad(
                    persona_v1,
                    dato_v1,
                    referencias_v1,
                )
            )
            resultados_v2.append(
                self.gestor.actualizar_contradiccion(
                    persona_v2,
                    dato_v2,
                    referencias_v2,
                )
            )
        self.assertEqual(resultados_v2, resultados_v1)
        self.assertEqual(
            persona_v2["confirmaciones_contradiccion"],
            persona_v1["confirmaciones_contradiccion"],
        )

    def test_transferencia_conserva_resultado_de_v1(self):
        anterior = {
            "nombre": "Matias",
            "similitud": 0.65,
            "tipo": "oficial",
            "embedding": np.array([1.0, 0.0]),
            "ultimo_visto": time.time() - 10,
            "rostros_asociados": {8},
        }
        nueva = {
            "nombre": "Matias",
            "similitud": 0.80,
            "tipo": "oficial",
            "embedding": np.array([1.0, 0.0]),
        }
        historial_v1 = {1: dict(anterior), 2: {}}
        historial_v2 = {
            1: {
                **anterior,
                "rostros_asociados": set(anterior["rostros_asociados"]),
            },
            2: {},
        }
        resultado_v1 = (
            app.MotorReconocimiento._resolver_propietarios_identidad(
                2,
                nueva,
                historial_v1,
            )
        )
        resultado_v2 = self.gestor.resolver_propietarios(
            2,
            nueva,
            historial_v2,
        )
        self.assertEqual(resultado_v2, resultado_v1)
        self.assertNotIn("nombre", historial_v2[1])


if __name__ == "__main__":
    unittest.main()
