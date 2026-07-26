import unittest

import numpy as np

import app
from backend.config import ConfiguracionRostro
from backend.utilidades.geometria import calcular_iou
from backend.utilidades.rostros import evaluar_calidad_rostro


class PruebasGeometria(unittest.TestCase):
    def test_iou_conserva_resultados_de_app_original(self):
        casos = [
            ((0, 0, 10, 10), (0, 0, 10, 10)),
            ((0, 0, 10, 10), (5, 5, 15, 15)),
            ((0, 0, 10, 10), (20, 20, 30, 30)),
            ((2, 3, 9, 12), (4, 1, 8, 8)),
        ]
        for caja_a, caja_b in casos:
            with self.subTest(caja_a=caja_a, caja_b=caja_b):
                self.assertAlmostEqual(
                    calcular_iou(caja_a, caja_b),
                    app.calcular_iou(caja_a, caja_b),
                )

    def test_calidad_rostro_conserva_resultados_originales(self):
        config = ConfiguracionRostro()
        puntos = np.array(
            [[30, 30], [70, 30], [50, 48], [36, 67], [64, 67]],
            dtype=np.float32,
        )
        casos = [
            ((0, 0, 100, 100), puntos, 0.9, True),
            ((0, 0, 40, 40), puntos, 0.9, True),
            ((0, 0, 100, 100), puntos, 0.2, True),
            ((0, 0, 100, 100), None, 0.9, True),
        ]
        for caja, landmarks, confianza, validar in casos:
            with self.subTest(caja=caja, confianza=confianza):
                self.assertEqual(
                    evaluar_calidad_rostro(
                        caja,
                        landmarks,
                        confianza,
                        config,
                        validar,
                    ),
                    app.evaluar_calidad_rostro(
                        caja,
                        landmarks,
                        confianza,
                        validar,
                    ),
                )


if __name__ == "__main__":
    unittest.main()
