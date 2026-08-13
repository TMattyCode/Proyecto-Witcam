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


class CapturadorConError(CapturadorFalso):
    def iniciar(self):
        raise RuntimeError("detalle tecnico sensible")


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
            motor.iniciar(0, analizar=False, id_camara=17)
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
        self.assertEqual(estado["camera_id"], 17)
        self.assertIsNone(motor.obtener_estado()["camera_id"])
        self.assertEqual(
            estado["last_event"],
            "Transmision activa sin analisis",
        )

    def test_error_del_motor_no_expone_el_detalle_tecnico(self):
        config = ConfiguracionApp()
        motor = MotorReconocimiento(
            config,
            RepositorioFalso(),
            FabricaPipelineProhibida(),
        )

        with (
            patch("backend.video.motor.CapturadorFrames", CapturadorConError),
            self.assertLogs("backend.video.motor", level="ERROR"),
        ):
            motor.iniciar(0, analizar=False, id_camara=17)
            motor.hilo.join(timeout=1.0)

        error_publico = motor.obtener_estado()["last_error"]
        self.assertIn("transmision de video", error_publico)
        self.assertNotIn("detalle tecnico sensible", error_publico)


if __name__ == "__main__":
    unittest.main()
