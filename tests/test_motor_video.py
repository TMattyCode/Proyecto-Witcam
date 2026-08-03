import time
import unittest
from dataclasses import replace
from unittest.mock import patch

import numpy as np

from backend.config import ConfiguracionApp, ConfiguracionVideo
from backend.video.motor import MotorReconocimiento


class FabricaPipelineProhibida:
    def __init__(self):
        self.llamadas = 0

    def preparar_modelos(self):
        self.llamadas += 1
        raise AssertionError("No se deben preparar modelos en modo video")

    def __call__(self, fps, registrar_evento):
        self.llamadas += 1
        raise AssertionError("No se debe crear el pipeline en modo video")


class CapturadorFalso:
    def __init__(self, fuente, evento_detencion, config):
        self.fuente = fuente
        self.evento_detencion = evento_detencion
        self.fps = 15.0
        self.secuencia = 1
        self.frame = np.zeros((48, 64, 3), dtype=np.uint8)

    @staticmethod
    def _es_archivo_local(fuente):
        return False

    def iniciar(self):
        return None

    def obtener(self):
        return self.secuencia, self.frame.copy(), None

    def secuencia_actual(self):
        return self.secuencia

    def detener(self):
        return None


class RepositorioFalso:
    def contar(self, carpeta):
        return 0

    def firma(self):
        return ""


class PruebasMotorVideo(unittest.TestCase):
    def test_transmite_webcam_sin_cargar_modelos(self):
        video = replace(
            ConfiguracionVideo(),
            ancho_maximo_web=64,
            alto_maximo_web=48,
            fps_video_web=30,
        )
        config = replace(ConfiguracionApp(), video=video)
        fabrica = FabricaPipelineProhibida()
        motor = MotorReconocimiento(config, RepositorioFalso(), fabrica)

        with patch("backend.video.motor.CapturadorFrames", CapturadorFalso):
            motor.iniciar(0, analizar=False)
            limite = time.time() + 1.0
            while not motor.obtener_estado()["streaming"]:
                if time.time() >= limite:
                    self.fail("El motor no publico el frame de prueba")
                time.sleep(0.01)
            estado = motor.obtener_estado()
            motor.detener()

        self.assertEqual(fabrica.llamadas, 0)
        self.assertTrue(estado["running"])
        self.assertTrue(estado["streaming"])
        self.assertEqual(
            estado["last_event"],
            "Transmision activa sin analisis",
        )


if __name__ == "__main__":
    unittest.main()
