import json
import logging
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
from backend.aplicacion.ingresos import ServicioIngresos
from backend.aplicacion.camaras import ServicioCamaras
from backend.api.serializacion import codificar_json
from backend.config import ConfiguracionVideo
from backend.exceptions import (
    CredencialesInvalidas,
    ErrorAutenticacion,
    ErrorGaleria,
    PermisoDenegado,
    RegistroDuplicado,
    ErrorCamara,
)
from backend.video.renderizado import crear_frame_mensaje


LOGGER = logging.getLogger(__name__)
MENSAJE_ERROR_INTERNO = (
    "No se pudo completar la operacion por un error interno. "
    "Intentalo nuevamente."
)


def crear_handler(
    raiz_proyecto: Path,
    monitoreo: ServicioMonitoreo,
    galerias: ServicioGalerias,
    config_video: ConfiguracionVideo,
    autenticacion: ServicioAutenticacion | None = None,
    ingresos: ServicioIngresos | None = None,
    camaras: ServicioCamaras | None = None,
) -> type[BaseHTTPRequestHandler]:
    class WitcamHandler(BaseHTTPRequestHandler):
        def log_message(self, formato, *args):
            return

        def do_GET(self):
            try:
                self._procesar_get()
            except PermisoDenegado as error:
                self._json({"ok": False, "error": str(error)}, estado=403)
            except CredencialesInvalidas as error:
                self._json(
                    {"ok": False, "error": str(error)},
                    estado=401,
                )
            except (ErrorGaleria, FileNotFoundError, ValueError) as error:
                self._json(
                    {"ok": False, "error": str(error)},
                    estado=404,
                )
            except Exception:
                LOGGER.exception("Error inesperado al procesar GET %s", self.path)
                try:
                    self._json(
                        {"ok": False, "error": MENSAJE_ERROR_INTERNO},
                        estado=500,
                    )
                except (BrokenPipeError, ConnectionResetError):
                    return

        def _procesar_get(self):
            url = urlparse(self.path)
            ruta = unquote(url.path)
            if ruta == "/":
                self._servir_archivo("index.html")
                return
            if ruta == "/video_feed":
                self._exigir_autenticacion()
                token = self._token_consulta(url)
                autenticacion.exigir_permiso(token, "ver_camaras")
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
                self._exigir_autenticacion()
                autenticacion.exigir_permiso(
                    self._token_sesion(), "ver_camaras"
                )
                self._json(monitoreo.estado())
                return
            if ruta == "/api/list":
                self._exigir_autenticacion()
                self._json(galerias.listar(self._token_sesion()))
                return
            if ruta == "/api/galerias/imagen":
                self._exigir_autenticacion()
                parametros = parse_qs(url.query, keep_blank_values=True)
                imagen = galerias.obtener_imagen(
                    self._token_sesion(),
                    parametros.get("type", [""])[0],
                    parametros.get("name", [""])[0],
                )
                self._servir_ruta(imagen, sin_cache=True)
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
            if ruta == "/api/subusuarios/historial":
                try:
                    self._exigir_autenticacion()
                    self._json(
                        autenticacion.listar_subusuarios_eliminados(
                            self._token_sesion()
                        )
                    )
                except CredencialesInvalidas as error:
                    self._json({"ok": False, "error": str(error)}, estado=401)
                except ErrorAutenticacion as error:
                    self._json({"ok": False, "error": str(error)}, estado=403)
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
            if ruta == "/api/ingresos/camaras":
                try:
                    self._exigir_autenticacion()
                    if ingresos is None:
                        raise ErrorAutenticacion(
                            "El servicio de ingresos no esta disponible"
                        )
                    self._json(
                        ingresos.listar_camaras(self._token_sesion())
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
            if ruta == "/api/alertas":
                self._exigir_autenticacion()
                if ingresos is None:
                    raise ErrorAutenticacion(
                        "El servicio de ingresos no esta disponible"
                    )
                parametros = parse_qs(url.query, keep_blank_values=True)
                self._json(ingresos.listar_alertas(
                    self._token_sesion(),
                    parametros.get("limite", [50])[0],
                ))
                return
            if ruta == "/api/ingresos/ultimos":
                self._exigir_autenticacion()
                if ingresos is None:
                    raise ErrorAutenticacion(
                        "El servicio de ingresos no esta disponible"
                    )
                parametros = parse_qs(url.query, keep_blank_values=True)
                self._json(ingresos.listar_ultimos(
                    self._token_sesion(),
                    parametros.get("limite", [5])[0],
                ))
                return
            if ruta == "/api/ingresos/historial":
                try:
                    self._exigir_autenticacion()
                    if ingresos is None:
                        raise ErrorAutenticacion(
                            "El servicio de ingresos no esta disponible"
                        )
                    parametros = parse_qs(url.query, keep_blank_values=True)
                    self._json(
                        ingresos.listar_historial(
                            self._token_sesion(),
                            parametros.get("idPersona", [""])[0],
                        )
                    )
                except CredencialesInvalidas as error:
                    self._json({"ok": False, "error": str(error)}, estado=401)
                except ErrorAutenticacion as error:
                    self._json({"ok": False, "error": str(error)}, estado=503)
                except ValueError as error:
                    self._json({"ok": False, "error": str(error)}, estado=400)
                return
            if ruta == "/api/ingresos/deteccion-rostro":
                try:
                    self._exigir_autenticacion()
                    if ingresos is None:
                        raise ErrorAutenticacion(
                            "El servicio de ingresos no esta disponible"
                        )
                    parametros = parse_qs(url.query, keep_blank_values=True)
                    rostro = ingresos.obtener_rostro_deteccion(
                        self._token_sesion(),
                        parametros.get("idDeteccion", [""])[0],
                    )
                    self._servir_ruta(rostro, sin_cache=True)
                except CredencialesInvalidas as error:
                    self._json({"ok": False, "error": str(error)}, estado=401)
                except ErrorAutenticacion as error:
                    self._json({"ok": False, "error": str(error)}, estado=503)
                except (FileNotFoundError, ValueError) as error:
                    self._json({"ok": False, "error": str(error)}, estado=404)
                return
            if ruta == "/api/ingresos/rostro":
                try:
                    self._exigir_autenticacion()
                    if ingresos is None:
                        raise ErrorAutenticacion(
                            "El servicio de ingresos no esta disponible"
                        )
                    parametros = parse_qs(url.query, keep_blank_values=True)
                    rostro = ingresos.obtener_rostro(
                        self._token_sesion(),
                        parametros.get("idPersona", [""])[0],
                    )
                    self._servir_ruta(rostro, sin_cache=True)
                except CredencialesInvalidas as error:
                    self._json({"ok": False, "error": str(error)}, estado=401)
                except ErrorAutenticacion as error:
                    self._json({"ok": False, "error": str(error)}, estado=503)
                except (FileNotFoundError, ValueError) as error:
                    self._json({"ok": False, "error": str(error)}, estado=404)
                return
            if ruta == "/api/lista-observacion":
                try:
                    self._exigir_autenticacion()
                    if ingresos is None:
                        raise ErrorAutenticacion(
                            "El servicio de ingresos no esta disponible"
                        )
                    parametros = parse_qs(
                        url.query,
                        keep_blank_values=True,
                    )
                    self._json(
                        ingresos.listar_observacion(
                            self._token_sesion(),
                            {
                                "pagina": parametros.get("pagina", [1])[0],
                                "limite": parametros.get("limite", [25])[0],
                            },
                        )
                    )
                except CredencialesInvalidas as error:
                    self._json({"ok": False, "error": str(error)}, estado=401)
                except ErrorAutenticacion as error:
                    self._json({"ok": False, "error": str(error)}, estado=503)
                except ValueError as error:
                    self._json({"ok": False, "error": str(error)}, estado=400)
                return
            if ruta == "/api/camaras":
                try:
                    self._exigir_autenticacion()
                    if camaras is None:
                        raise ErrorCamara(
                            "El servicio de camaras no esta disponible"
                        )
                    self._json(camaras.listar(self._token_sesion()))
                except CredencialesInvalidas as error:
                    self._json(
                        {"ok": False, "error": str(error)},
                        estado=401,
                    )
                except (ErrorAutenticacion, ErrorCamara) as error:
                    self._json(
                        {"ok": False, "error": str(error)},
                        estado=403,
                    )
                return
            if ruta == "/api/ingresos":
                try:
                    self._exigir_autenticacion()
                    if ingresos is None:
                        raise ErrorAutenticacion(
                            "El servicio de ingresos no esta disponible"
                        )
                    filtros = {
                        clave: valores[0]
                        for clave, valores in parse_qs(
                            url.query,
                            keep_blank_values=True,
                        ).items()
                    }
                    self._json(
                        ingresos.listar(
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
                        estado=503,
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
                if ruta == "/api/ingresos/lista-observacion":
                    self._exigir_autenticacion()
                    if ingresos is None:
                        raise ErrorAutenticacion(
                            "El servicio de ingresos no esta disponible"
                        )
                    self._json(
                        ingresos.agregar_lista_observacion(
                            self._token_sesion(),
                            datos,
                        ),
                        estado=201,
                    )
                    return
                if ruta == "/api/ingresos/quitar-lista-observacion":
                    self._exigir_autenticacion()
                    if ingresos is None:
                        raise ErrorAutenticacion(
                            "El servicio de ingresos no esta disponible"
                        )
                    self._json(
                        ingresos.quitar_lista_observacion(
                            self._token_sesion(),
                            datos,
                        )
                    )
                    return
                if ruta == "/api/ingresos/renombrar-persona":
                    self._exigir_autenticacion()
                    if ingresos is None:
                        raise ErrorAutenticacion(
                            "El servicio de ingresos no esta disponible"
                        )
                    self._json(
                        ingresos.renombrar_persona(
                            self._token_sesion(),
                            datos,
                        )
                    )
                    return
                if ruta == "/api/ingresos/eliminar-persona":
                    self._exigir_autenticacion()
                    if ingresos is None:
                        raise ErrorAutenticacion(
                            "El servicio de ingresos no esta disponible"
                        )
                    self._json(
                        ingresos.eliminar_persona(
                            self._token_sesion(),
                            datos,
                        )
                    )
                    return
                if ruta == "/api/grupos-camara/guardar":
                    self._exigir_autenticacion()
                    if camaras is None:
                        raise ErrorCamara(
                            "El servicio de camaras no esta disponible"
                        )
                    self._json(
                        camaras.guardar_grupos(
                            self._token_sesion(),
                            datos,
                        )
                    )
                    return
                if ruta == "/api/camaras/crear":
                    self._exigir_autenticacion()
                    if camaras is None:
                        raise ErrorCamara(
                            "El servicio de camaras no esta disponible"
                        )
                    self._json(
                        camaras.crear(self._token_sesion(), datos),
                        estado=201,
                    )
                    return
                if ruta == "/api/camaras/editar":
                    self._exigir_autenticacion()
                    if camaras is None:
                        raise ErrorCamara(
                            "El servicio de camaras no esta disponible"
                        )
                    self._json(
                        camaras.editar(self._token_sesion(), datos)
                    )
                    return
                if ruta == "/api/camaras/eliminar":
                    self._exigir_autenticacion()
                    if camaras is None:
                        raise ErrorCamara(
                            "El servicio de camaras no esta disponible"
                        )
                    self._json(
                        camaras.eliminar(self._token_sesion(), datos)
                    )
                    return
                if ruta == "/api/start":
                    fuente = datos.get("source")
                    analizar = datos.get("analysis", True)
                    id_camara = datos.get("cameraId")
                    if isinstance(fuente, bool) or (
                        fuente is not None
                        and not isinstance(fuente, (int, str))
                    ):
                        raise ValueError("La fuente de video no es valida")
                    if not isinstance(analizar, bool):
                        raise ValueError("El modo de analisis no es valido")
                    if id_camara is None or (
                        isinstance(id_camara, bool)
                        or not isinstance(id_camara, int)
                        or id_camara <= 0
                    ):
                        raise ValueError("La camara no es valida")
                    if camaras is None:
                        raise ErrorCamara(
                            "El servicio de camaras no esta disponible"
                        )
                    id_cuenta = camaras.validar_transmision(
                        self._token_sesion(),
                        id_camara,
                        fuente,
                    )
                    monitoreo.iniciar(
                        fuente,
                        analizar,
                        id_camara,
                        id_cuenta,
                    )
                    self._json({"ok": True})
                    return
                if ruta == "/api/stop":
                    self._exigir_autenticacion()
                    if camaras is None:
                        raise ErrorCamara(
                            "El servicio de camaras no esta disponible"
                        )
                    camaras.validar_detencion(
                        self._token_sesion(),
                        monitoreo.estado().get("camera_id"),
                    )
                    monitoreo.detener()
                    self._json({"ok": True})
                    return
                if ruta == "/api/approve":
                    self._exigir_autenticacion()
                    galerias.aprobar(
                        datos.get("file", ""),
                        self._token_sesion(),
                    )
                    self._json({"ok": True})
                    return
                if ruta == "/api/unapprove":
                    self._exigir_autenticacion()
                    galerias.devolver_a_pendiente(
                        datos.get("file", ""),
                        self._token_sesion(),
                    )
                    self._json({"ok": True})
                    return
                if ruta == "/api/rename":
                    galerias.renombrar(
                        datos.get("type", ""),
                        datos.get("file", ""),
                        datos.get("newName", ""),
                        self._token_sesion(),
                    )
                    self._json({"ok": True})
                    return
                if ruta == "/api/reject":
                    self._exigir_autenticacion()
                    galerias.rechazar(
                        datos.get("file", ""),
                        self._token_sesion(),
                    )
                    self._json({"ok": True})
                    return
                self.send_error(404)
            except PermisoDenegado as error:
                self._json(
                    {"ok": False, "error": str(error)},
                    estado=403,
                )
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
            except ErrorCamara as error:
                self._json(
                    {"ok": False, "error": str(error)},
                    estado=409,
                )
            except (ErrorGaleria, FileNotFoundError, ValueError) as error:
                self._json(
                    {"ok": False, "error": str(error)},
                    estado=400,
                )
            except Exception:
                LOGGER.exception("Error inesperado al procesar POST %s", ruta)
                self._json(
                    {"ok": False, "error": MENSAJE_ERROR_INTERNO},
                    estado=500,
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

        @staticmethod
        def _token_consulta(url) -> str:
            token = parse_qs(url.query).get("token", [""])[0].strip()
            if not token:
                raise CredencialesInvalidas("Falta el token de sesion")
            return token

        def _leer_json(self) -> dict:
            try:
                longitud = int(self.headers.get("Content-Length", "0"))
            except (TypeError, ValueError) as error:
                raise ValueError(
                    "El tamano de la solicitud no es valido"
                ) from error
            if longitud == 0:
                return {}
            if longitud > 65_536:
                raise ValueError("La solicitud supera el tamano permitido")
            try:
                contenido = self.rfile.read(longitud).decode("utf-8")
                datos = json.loads(contenido)
            except (UnicodeDecodeError, json.JSONDecodeError) as error:
                raise ValueError(
                    "El contenido de la solicitud no es un JSON valido"
                ) from error
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
            self._servir_ruta(ruta)

        def _servir_ruta(
            self,
            ruta: Path,
            sin_cache: bool = False,
        ) -> None:
            tipo = mimetypes.guess_type(str(ruta))[0] or (
                "application/octet-stream"
            )
            contenido = ruta.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", tipo)
            if sin_cache:
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
