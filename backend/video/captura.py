import os
import threading
import time
from pathlib import Path

import cv2
import numpy as np

from backend.config import ConfiguracionVideo, PROJECT_ROOT


class CapturadorFrames:
    def __init__(
        self,
        fuente: int | str,
        evento_detencion: threading.Event,
        config: ConfiguracionVideo,
    ):
        self.fuente = fuente
        self.es_archivo_local = self._es_archivo_local(fuente)
        self.evento_detencion = evento_detencion
        self.config = config
        self.evento_detencion_local = threading.Event()
        self.bloqueo = threading.Lock()
        self.camara: cv2.VideoCapture | None = None
        self.hilo: threading.Thread | None = None
        self.ultimo_frame: np.ndarray | None = None
        self.secuencia = 0
        self.error: str | None = None
        self.fps = 15.0

    @staticmethod
    def _es_archivo_local(fuente: int | str) -> bool:
        if not isinstance(fuente, (str, Path)):
            return False
        normalizada = str(fuente).lower()
        return not normalizada.startswith(
            ("rtsp://", "rtmp://", "http://", "https://")
        )

    def iniciar(self) -> None:
        self._abrir_camara()
        self.hilo = threading.Thread(target=self._ejecutar, daemon=True)
        self.hilo.start()

    def _abrir_camara(self) -> None:
        if self.es_archivo_local:
            ruta = Path(self.fuente).expanduser()
            if not ruta.is_absolute():
                ruta = PROJECT_ROOT / ruta
            if not ruta.is_file():
                raise RuntimeError(f"No existe el archivo de video: {ruta}")
            self.camara = cv2.VideoCapture(str(ruta), cv2.CAP_FFMPEG)
        elif isinstance(self.fuente, str):
            os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"
            self.camara = cv2.VideoCapture(
                self.fuente,
                cv2.CAP_FFMPEG,
                [
                    cv2.CAP_PROP_OPEN_TIMEOUT_MSEC,
                    5000,
                    cv2.CAP_PROP_READ_TIMEOUT_MSEC,
                    2000,
                ],
            )
        else:
            self.camara = cv2.VideoCapture(self.fuente, cv2.CAP_DSHOW)
            self.camara.set(
                cv2.CAP_PROP_FOURCC,
                cv2.VideoWriter_fourcc(*"MJPG"),
            )
            self.camara.set(cv2.CAP_PROP_FPS, 15)
            self.camara.set(
                cv2.CAP_PROP_FRAME_WIDTH,
                self.config.ancho_camara,
            )
            self.camara.set(
                cv2.CAP_PROP_FRAME_HEIGHT,
                self.config.alto_camara,
            )
        self.camara.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        if not self.camara.isOpened():
            raise RuntimeError(
                f"No se pudo abrir la fuente de video: {self.fuente}"
            )
        fps = self.camara.get(cv2.CAP_PROP_FPS)
        if fps > 0:
            self.fps = fps

    def _ejecutar(self) -> None:
        intentos = 0
        siguiente_frame = time.perf_counter()
        while (
            not self.evento_detencion.is_set()
            and not self.evento_detencion_local.is_set()
        ):
            correcto, frame = self.camara.read()
            if not correcto:
                if self.es_archivo_local:
                    with self.bloqueo:
                        self.error = "El video de prueba finalizo."
                    return
                intentos += 1
                if self.camara is not None:
                    self.camara.release()
                if intentos > self.config.max_intentos_reconexion:
                    with self.bloqueo:
                        self.error = (
                            "No se pudo leer la transmision de video."
                        )
                    return
                if self.evento_detencion.wait(
                    self.config.intervalo_reconexion
                ):
                    return
                try:
                    self._abrir_camara()
                except RuntimeError:
                    continue
                continue
            intentos = 0
            with self.bloqueo:
                self.ultimo_frame = frame
                self.secuencia += 1
            if self.es_archivo_local:
                siguiente_frame += 1.0 / max(self.fps, 1.0)
                espera = siguiente_frame - time.perf_counter()
                if espera > 0:
                    self.evento_detencion.wait(espera)
                else:
                    siguiente_frame = time.perf_counter()

    def obtener(self) -> tuple[int, np.ndarray | None, str | None]:
        with self.bloqueo:
            frame = (
                None
                if self.ultimo_frame is None
                else self.ultimo_frame.copy()
            )
            return self.secuencia, frame, self.error

    def secuencia_actual(self) -> int:
        with self.bloqueo:
            return self.secuencia

    def detener(self) -> None:
        self.evento_detencion_local.set()
        if self.hilo and self.hilo.is_alive():
            self.hilo.join(timeout=2.5)
        if self.camara is not None:
            self.camara.release()
        if self.hilo and self.hilo.is_alive():
            self.hilo.join(timeout=1.0)
