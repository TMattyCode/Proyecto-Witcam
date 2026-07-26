import json
import mimetypes
import time
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import unquote, urlparse

from backend.aplicacion.servicios import (
    ServicioGalerias,
    ServicioMonitoreo,
)
from backend.api.serializacion import codificar_json
from backend.config import ConfiguracionVideo
from backend.video.renderizado import crear_frame_mensaje


def crear_handler(
    raiz_proyecto: Path,
    monitoreo: ServicioMonitoreo,
    galerias: ServicioGalerias,
    config_video: ConfiguracionVideo,
) -> type[BaseHTTPRequestHandler]:
    class WitcamHandler(BaseHTTPRequestHandler):
        def log_message(self, formato, *args):
            return

        def do_GET(self):
            ruta = unquote(urlparse(self.path).path)
            if ruta == "/":
                self._servir_archivo("index.html")
                return
            if ruta == "/video_feed":
                self._servir_video()
                return
            if ruta == "/placeholder":
                self._servir_jpeg(
                    crear_frame_mensaje(
                        "Presiona Iniciar en la interfaz",
                        config_video,
                    )
                )
                return
            if ruta == "/api/status":
                self._json(monitoreo.estado())
                return
            if ruta == "/api/list":
                self._json(galerias.listar())
                return
            self._servir_archivo(ruta.lstrip("/"))

        def do_POST(self):
            ruta = urlparse(self.path).path
            datos = self._leer_json()
            try:
                if ruta == "/api/start":
                    monitoreo.iniciar()
                    self._json({"ok": True})
                    return
                if ruta == "/api/stop":
                    monitoreo.detener()
                    self._json({"ok": True})
                    return
                if ruta == "/api/approve":
                    galerias.aprobar(datos.get("file", ""))
                    self._json({"ok": True})
                    return
                if ruta == "/api/unapprove":
                    galerias.devolver_a_pendiente(datos.get("file", ""))
                    self._json({"ok": True})
                    return
                if ruta == "/api/rename":
                    galerias.renombrar(
                        datos.get("type", ""),
                        datos.get("file", ""),
                        datos.get("newName", ""),
                    )
                    self._json({"ok": True})
                    return
                if ruta == "/api/reject":
                    galerias.rechazar(datos.get("file", ""))
                    self._json({"ok": True})
                    return
                self.send_error(404)
            except Exception as error:
                self._json(
                    {"ok": False, "error": str(error)},
                    estado=400,
                )

        def _leer_json(self) -> dict:
            longitud = int(self.headers.get("Content-Length", "0"))
            if longitud == 0:
                return {}
            contenido = self.rfile.read(longitud).decode("utf-8")
            return json.loads(contenido)

        def _json(self, datos: object, estado: int = 200) -> None:
            cuerpo = codificar_json(datos)
            self.send_response(estado)
            self.send_header(
                "Content-Type",
                "application/json; charset=utf-8",
            )
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(cuerpo)))
            self.end_headers()
            self.wfile.write(cuerpo)

        def _servir_archivo(self, ruta_relativa: str) -> None:
            ruta = (raiz_proyecto / ruta_relativa).resolve()
            if not ruta.is_relative_to(raiz_proyecto.resolve()):
                self.send_error(403)
                return
            if not ruta.exists() or not ruta.is_file():
                self.send_error(404)
                return
            tipo = (
                mimetypes.guess_type(str(ruta))[0]
                or "application/octet-stream"
            )
            contenido = ruta.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", tipo)
            if ruta.suffix.lower() in galerias.repositorio.config.extensiones:
                self.send_header("Cache-Control", "no-store, max-age=0")
                self.send_header("Pragma", "no-cache")
            self.send_header("Content-Length", str(len(contenido)))
            self.end_headers()
            self.wfile.write(contenido)

        def _servir_video(self) -> None:
            self.send_response(200)
            self.send_header(
                "Content-Type",
                "multipart/x-mixed-replace; boundary=frame",
            )
            self.end_headers()
            while True:
                frame = monitoreo.frame()
                if frame is None:
                    frame = crear_frame_mensaje(
                        "Presiona Iniciar en la interfaz",
                        config_video,
                    )
                try:
                    self.wfile.write(b"--frame\r\n")
                    self.wfile.write(b"Content-Type: image/jpeg\r\n\r\n")
                    self.wfile.write(frame)
                    self.wfile.write(b"\r\n")
                    time.sleep(0.08)
                except (
                    BrokenPipeError,
                    ConnectionResetError,
                    ConnectionAbortedError,
                ):
                    break

        def _servir_jpeg(self, frame: bytes) -> None:
            self.send_response(200)
            self.send_header("Content-Type", "image/jpeg")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(frame)))
            self.end_headers()
            self.wfile.write(frame)

    return WitcamHandler
