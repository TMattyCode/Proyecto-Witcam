import json
import mimetypes
import time
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from backend.aplicacion.servicios import (
    ServicioGalerias,
    ServicioMonitoreo,
)
from backend.aplicacion.autenticacion import ServicioAutenticacion
from backend.api.serializacion import codificar_json
from backend.config import ConfiguracionVideo
from backend.exceptions import (
    CredencialesInvalidas,
    ErrorAutenticacion,
    RegistroDuplicado,
)
from backend.video.renderizado import crear_frame_mensaje


def crear_handler(
    raiz_proyecto: Path,
    monitoreo: ServicioMonitoreo,
    galerias: ServicioGalerias,
    config_video: ConfiguracionVideo,
    autenticacion: ServicioAutenticacion | None = None,
) -> type[BaseHTTPRequestHandler]:
    class WitcamHandler(BaseHTTPRequestHandler):
        def log_message(self, formato, *args):
            return

        def do_GET(self):
            url = urlparse(self.path)
            ruta = unquote(url.path)
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
            if ruta == "/api/auth/session":
                try:
                    self._exigir_autenticacion()
                    self._json(
                        autenticacion.obtener_sesion(self._token_sesion())
                    )
                except CredencialesInvalidas as error:
                    self._json(
                        {"ok": False, "error": str(error)},
                        estado=401,
                    )
                except ErrorAutenticacion as error:
                    self._json(
                        {"ok": False, "error": str(error)},
                        estado=503,
                    )
                return
            if ruta == "/api/cuenta/resumen":
                try:
                    self._exigir_autenticacion()
                    self._json(
                        autenticacion.obtener_resumen_cuenta(
                            self._token_sesion()
                        )
                    )
                except CredencialesInvalidas as error:
                    self._json(
                        {"ok": False, "error": str(error)},
                        estado=401,
                    )
                except ErrorAutenticacion as error:
                    self._json(
                        {"ok": False, "error": str(error)},
                        estado=400,
                    )
                return
            if ruta == "/api/subusuarios":
                try:
                    self._exigir_autenticacion()
                    filtros = {
                        clave: valores[0]
                        for clave, valores in parse_qs(
                            url.query,
                            keep_blank_values=True,
                        ).items()
                    }
                    self._json(
                        autenticacion.listar_subusuarios(
                            self._token_sesion(),
                            filtros,
                        )
                    )
                except CredencialesInvalidas as error:
                    self._json(
                        {"ok": False, "error": str(error)},
                        estado=401,
                    )
                except ErrorAutenticacion as error:
                    self._json(
                        {"ok": False, "error": str(error)},
                        estado=403,
                    )
                except ValueError as error:
                    self._json(
                        {"ok": False, "error": str(error)},
                        estado=400,
                    )
                return
            self._servir_archivo(ruta.lstrip("/"))

        def do_POST(self):
            ruta = urlparse(self.path).path
            try:
                datos = self._leer_json()
                if ruta == "/api/auth/register":
                    self._exigir_autenticacion()
                    self._json(autenticacion.registrar(datos), estado=201)
                    return
                if ruta == "/api/auth/login":
                    self._exigir_autenticacion()
                    self._json(autenticacion.iniciar_sesion(datos))
                    return
                if ruta == "/api/auth/logout":
                    self._exigir_autenticacion()
                    autenticacion.cerrar_sesion(self._token_sesion())
                    self._json({"ok": True})
                    return
                if ruta == "/api/subusuarios":
                    self._exigir_autenticacion()
                    self._json(
                        autenticacion.registrar_subusuario(
                            self._token_sesion(),
                            datos,
                        ),
                        estado=201,
                    )
                    return
                if ruta == "/api/subusuarios/estado":
                    self._exigir_autenticacion()
                    self._json(
                        autenticacion.actualizar_estado_subusuario(
                            self._token_sesion(),
                            datos,
                        )
                    )
                    return
                if ruta == "/api/subusuarios/editar":
                    self._exigir_autenticacion()
                    self._json(
                        autenticacion.editar_subusuario(
                            self._token_sesion(),
                            datos,
                        )
                    )
                    return
                if ruta == "/api/start":
                    fuente = datos.get("source")
                    analizar = datos.get("analysis", True)
                    if isinstance(fuente, bool) or (
                        fuente is not None
                        and not isinstance(fuente, (int, str))
                    ):
                        raise ValueError("La fuente de video no es valida")
                    if not isinstance(analizar, bool):
                        raise ValueError("El modo de analisis no es valido")
                    monitoreo.iniciar(fuente, analizar)
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
            except CredencialesInvalidas as error:
                self._json(
                    {"ok": False, "error": str(error)},
                    estado=401,
                )
            except RegistroDuplicado as error:
                self._json(
                    {"ok": False, "error": str(error)},
                    estado=409,
                )
            except ErrorAutenticacion as error:
                self._json(
                    {"ok": False, "error": str(error)},
                    estado=400,
                )
            except Exception as error:
                self._json(
                    {"ok": False, "error": str(error)},
                    estado=400,
                )

        def _exigir_autenticacion(self) -> None:
            if autenticacion is None:
                raise ErrorAutenticacion(
                    "El servicio de autenticacion no esta disponible"
                )

        def _token_sesion(self) -> str:
            autorizacion = self.headers.get("Authorization", "")
            prefijo = "Bearer "
            if not autorizacion.startswith(prefijo):
                raise CredencialesInvalidas("Falta el token de sesion")
            return autorizacion[len(prefijo):].strip()

        def _leer_json(self) -> dict:
            longitud = int(self.headers.get("Content-Length", "0"))
            if longitud == 0:
                return {}
            if longitud > 65_536:
                raise ValueError("La solicitud supera el tamano permitido")
            contenido = self.rfile.read(longitud).decode("utf-8")
            datos = json.loads(contenido)
            if not isinstance(datos, dict):
                raise ValueError("El cuerpo JSON debe ser un objeto")
            return datos

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
