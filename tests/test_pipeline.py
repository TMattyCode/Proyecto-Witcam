import unittest

import numpy as np

from backend.config import ConfiguracionApp
from backend.dominio.modelos import (
    DeteccionPersona,
    DeteccionRostro,
    EstadoSeguimiento,
    ReferenciaFacial,
)
from backend.ia.identidades import GestorIdentidades
from backend.ia.pipeline import PipelineReconocimiento


class DetectorFalso:
    def detectar(self, frame):
        return [
            DeteccionRostro(
                bbox=(0, 0, 300, 300),
                confianza=0.9,
                puntos_clave=np.array(
                    [
                        [90, 90],
                        [210, 90],
                        [150, 144],
                        [108, 201],
                        [192, 201],
                    ],
                    dtype=np.float32,
                ),
            )
        ]


class ReconocedorFalso:
    def __init__(self):
        self.llamadas = 0

    def generar_embeddings(self, frame, puntos_clave):
        self.llamadas += 1
        return [np.array([1.0, 0.0]) for _ in puntos_clave]

    def analizar(self, imagen):
        return []


class RastreadorFalso:
    def actualizar(self, cajas, confianzas):
        if not cajas:
            return []
        return [DeteccionPersona(tuple(cajas[0].astype(int)), 7)]


class DesconocidosFalso:
    @staticmethod
    def clave(tracker_id, persona_id=None):
        return ("rostro", tracker_id)

    @staticmethod
    def eliminar(*args, **kwargs):
        return None

    def manejar(self, *args, **kwargs):
        raise AssertionError("No debio tratar un rostro reconocido como nuevo")


class MuestrasFalsas:
    def agregar(self, *args, **kwargs):
        return False


class PruebasPipeline(unittest.TestCase):
    def setUp(self):
        self.config = ConfiguracionApp()
        self.reconocedor = ReconocedorFalso()
        self.pipeline = PipelineReconocimiento(
            self.config,
            DetectorFalso(),
            self.reconocedor,
            RastreadorFalso(),
            GestorIdentidades(self.config.tracking),
            DesconocidosFalso(),
            MuestrasFalsas(),
        )
        self.frame = np.zeros((100, 100, 3), dtype=np.uint8)
        self.referencias = [
            ReferenciaFacial(
                nombre="Matias",
                embedding=np.array([1.0, 0.0]),
                tipo="oficial",
            )
        ]

    def test_reconoce_con_adaptadores_falsos(self):
        resultados = self.pipeline.analizar_frame(
            self.frame,
            self.referencias,
            True,
            [],
            EstadoSeguimiento(),
        )
        self.assertEqual(len(resultados), 1)
        self.assertEqual(
            resultados[0].texto,
            "ID 7 | Matias | 1.00",
        )
        self.assertEqual(self.reconocedor.llamadas, 1)

    def test_no_genera_embeddings_fuera_del_intervalo(self):
        resultados = self.pipeline.analizar_frame(
            self.frame,
            self.referencias,
            False,
            [],
            EstadoSeguimiento(),
        )
        self.assertEqual(
            resultados[0].texto,
            "ID 7 | Rostro detectado",
        )
        self.assertEqual(self.reconocedor.llamadas, 0)


if __name__ == "__main__":
    unittest.main()
