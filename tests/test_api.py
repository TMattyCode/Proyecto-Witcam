import http.client
import json
import tempfile
import threading
import unittest
from dataclasses import replace
from http.server import ThreadingHTTPServer
from pathlib import Path

import cv2
import numpy as np

from backend.api.handler import crear_handler
from backend.aplicacion.servicios import ServicioGalerias
from backend.config import (
    ConfiguracionGalerias,
    ConfiguracionVideo,
)
from backend.galerias.repositorio import RepositorioGalerias
from backend.exceptions import (
    CredencialesInvalidas,
    ErrorAutenticacion,
    RegistroDuplicado,
)


JPEG_MINIMO = b"\xff\xd8\xff\xd9"


class MonitoreoFalso:
    def __init__(self):
        self.iniciado = False
        self.detenido = False
        self.fuente = None
        self.analizar = True
        self.id_camara = None

    def iniciar(
        self,
        fuente=None,
        analizar=True,
        id_camara=None,
        id_cuenta=None,
    ):
        self.iniciado = True
        self.fuente = fuente
        self.analizar = analizar
        self.id_camara = id_camara
        self.id_cuenta = id_cuenta

    def detener(self):
        self.detenido = True

    def estado(self):
        return {
            "running": self.iniciado and not self.detenido,
            "streaming": False,
            "last_error": None,
            "last_event": "Detenido",
            "detections": [],
            "references_count": 0,
            "has_frame": True,
            "references_files": 1,
            "pending_files": 1,
            "gallery_signature": "firma",
            "similarity_threshold": 0.45,
        }

    def frame(self):
        return JPEG_MINIMO


class AutenticacionFalsa:
    def __init__(self):
        self.usuario = {
            "id": 1,
            "idCuenta": 10,
            "nombreUsuario": "matias",
            "rol": "Administrador",
        }
        self.token = "token-prueba"

    def registrar(self, datos):
        if datos.get("nombreUsuario") == "duplicado":
            raise RegistroDuplicado("El usuario ya existe")
        return {"ok": True, "user": self.usuario}

    def iniciar_sesion(self, datos):
        if datos.get("nombreUsuario") == "no-existe":
            raise CredencialesInvalidas("Usuario o contrasena incorrectos")
        return {"ok": True, "token": self.token, "user": self.usuario}

    def obtener_sesion(self, token):
        if token != self.token:
            raise RuntimeError("Token incorrecto")
        return {"ok": True, "user": self.usuario}

    def exigir_permiso(self, token, codigo_permiso):
        return self.obtener_sesion(token)["user"]

    def obtener_resumen_cuenta(self, token):
        if token != self.token:
            raise CredencialesInvalidas("La sesion no es valida")
        return {
            "ok": True,
            "nombreCuenta": "Cuenta Prueba",
            "subusuariosActivos": 2,
        }

    def listar_subusuarios(self, token, filtros=None):
        if token != self.token:
            raise CredencialesInvalidas("La sesion no es valida")
        filtros = filtros or {}
        estado = filtros.get("estado", "activo")
        if estado != "activo":
            raise ValueError("Solo se pueden consultar subusuarios activos")
        return {
            "ok": True,
            "filtroEstado": estado,
            "total": 0,
            "pagina": int(filtros.get("pagina", 1)),
            "limite": int(filtros.get("limite", 25)),
            "permisos": [{"id": 1, "codigo": "ver", "nombre": "Ver"}],
            "subusuarios": [],
        }

    def registrar_subusuario(self, token, datos):
        if token != self.token:
            raise CredencialesInvalidas("La sesion no es valida")
        return {
            "ok": True,
            "subusuario": {
                "id": 2,
                "nombreUsuario": datos["nombreUsuario"],
                "estado": "Activo",
                "fechaCreacion": "2026-08-04T12:30:00",
                "ultimoAcceso": None,
                "permisos": datos.get("permisos", []),
            },
        }

    def actualizar_estado_subusuario(self, token, datos):
        if token != self.token:
            raise CredencialesInvalidas("La sesion no es valida")
        if datos["estado"] != "inactivo":
            raise ErrorAutenticacion("Los subusuarios solo se pueden desactivar")
        return {
            "ok": True,
            "id": datos["id"],
            "estado": "Inactivo",
        }

    def editar_subusuario(self, token, datos):
        if token != self.token:
            raise CredencialesInvalidas("La sesion no es valida")
        return {
            "ok": True,
            "subusuario": {
                "id": datos["id"],
                "estado": "Activo",
                "permisos": datos.get("permisos", []),
            },
        }

    def actualizar_perfil(self, token, datos):
        if token != self.token:
            raise CredencialesInvalidas("La sesion no es valida")
        self.usuario = {
            **self.usuario,
            "nombre": datos["nombre"],
            "apellido": datos["apellido"],
            "nombreUsuario": datos["nombreUsuario"],
            "correo": datos["correo"],
            "telefono": datos.get("telefono") or None,
        }
        return {"ok": True, "user": self.usuario}

    def cerrar_sesion(self, token):
        return None


class IngresosFalso:
    def __init__(self, ruta_rostro):
        self.ruta_rostro = ruta_rostro

    def listar(self, token, filtros=None):
        if token != "token-prueba":
            raise CredencialesInvalidas("La sesion no es valida")
        filtros = filtros or {}
        return {
            "ok": True,
            "total": 1,
            "pagina": int(filtros.get("pagina", 1)),
            "limite": int(filtros.get("limite", 25)),
            "ingresos": [
                {
                    "idDeteccion": 35,
                    "idPersona": 12,
                    "nombrePersona": "Persona prueba",
                    "idCamara": 4,
                    "nombreCamara": "Acceso principal",
                    "fechaHora": "2026-08-07T14:30:15",
                    "tieneRostro": False,
                    "resultado": "Identificado",
                    "similitud": 0.87321,
                }
            ],
        }

    def listar_camaras(self, token):
        if token != "token-prueba":
            raise CredencialesInvalidas("La sesion no es valida")
        return {
            "ok": True,
            "camaras": [{"id": 4, "nombre": "Acceso principal"}],
        }

    def listar_historial(self, token, id_persona):
        if token != "token-prueba":
            raise CredencialesInvalidas("La sesion no es valida")
        return {
            "ok": True,
            "persona": {"id": int(id_persona), "nombre": "Persona prueba"},
            "detecciones": [],
        }

    def agregar_lista_observacion(self, token, datos):
        if token != "token-prueba":
            raise CredencialesInvalidas("La sesion no es valida")
        return {
            "ok": True,
            "idPersona": datos["idPersona"],
            "enListaObservacion": True,
            "motivo": datos.get("motivo", ""),
        }

    def listar_observacion(self, token, parametros=None):
        if token != "token-prueba":
            raise CredencialesInvalidas("La sesion no es valida")
        parametros = parametros or {}
        return {
            "ok": True,
            "total": 1,
            "pagina": int(parametros.get("pagina", 1)),
            "limite": int(parametros.get("limite", 25)),
            "registros": [
                {"idLista": 8, "idPersona": 12, "idCliente": 12}
            ],
        }

    def quitar_lista_observacion(self, token, datos):
        if token != "token-prueba":
            raise CredencialesInvalidas("La sesion no es valida")
        return {
            "ok": True,
            "idPersona": datos["idPersona"],
            "enListaObservacion": False,
        }

    def obtener_rostro(self, token, id_persona):
        if token != "token-prueba":
            raise CredencialesInvalidas("La sesion no es valida")
        if int(id_persona) != 12:
            raise ValueError("La persona no existe en esta cuenta")
        return self.ruta_rostro

    def obtener_rostro_deteccion(self, token, id_deteccion):
        if token != "token-prueba":
            raise CredencialesInvalidas("La sesion no es valida")
        if int(id_deteccion) != 35:
            raise ValueError("La deteccion no existe en esta cuenta")
        return self.ruta_rostro

    def eliminar_persona(self, token, datos):
        if token != "token-prueba":
            raise CredencialesInvalidas("La sesion no es valida")
        return {
            "ok": True,
            "idPersona": datos["idPersona"],
            "nombrePersona": "Persona prueba",
        }

    def renombrar_persona(self, token, datos):
        if token != "token-prueba":
            raise CredencialesInvalidas("La sesion no es valida")
        return {
            "ok": True,
            "idPersona": datos["idPersona"],
            "nombrePersona": datos["nombre"].strip(),
        }


class CamarasFalso:
    def _validar(self, token):
        if token != "token-prueba":
            raise CredencialesInvalidas("La sesion no es valida")

    def listar(self, token):
        self._validar(token)
        return {
            "ok": True,
            "grupos": [{"id": 3, "nombre": "Entrada"}],
            "camaras": [{"id": 9, "nombre": "Acceso", "tipo": "onvif"}],
        }

    def guardar_grupos(self, token, datos):
        self._validar(token)
        return self.listar(token)

    def crear(self, token, datos):
        self._validar(token)
        return {"ok": True, "id": 9, **self.listar(token)}

    def editar(self, token, datos):
        self._validar(token)
        return self.listar(token)

    def eliminar(self, token, datos):
        self._validar(token)
        return {"ok": True, "grupos": [], "camaras": []}

    def validar_transmision(self, token, id_camara, fuente):
        self._validar(token)
        if id_camara != 17 or fuente != 0:
            raise ErrorCamara("La camara no es valida")
        return 10

    def validar_detencion(self, token, id_camara):
        self._validar(token)


class PruebasApi(unittest.TestCase):
    def setUp(self):
        self.temporal = tempfile.TemporaryDirectory()
        self.raiz = Path(self.temporal.name)
        (self.raiz / "index.html").write_text("witcam", encoding="utf-8")
        config = ConfiguracionGalerias(
            carpeta_referencias=self.raiz / "referencias_reconocimiento",
            carpeta_pendientes=self.raiz / "referencias_pendientes",
        )
        self.repositorio = RepositorioGalerias(config, self.raiz)
        self.repositorio.preparar()
        self._crear_galeria(config.carpeta_referencias, "Bob")
        self._crear_galeria(config.carpeta_pendientes, "Alice")
        self.ruta_rostro = self.raiz / "rostro.jpg"
        cv2.imwrite(
            str(self.ruta_rostro),
            np.zeros((20, 20, 3), dtype=np.uint8),
        )
        self.monitoreo = MonitoreoFalso()
        handler = crear_handler(
            self.raiz,
            self.monitoreo,
            ServicioGalerias(self.repositorio),
            replace(
                ConfiguracionVideo(),
                ancho_maximo_web=64,
                alto_maximo_web=48,
            ),
            AutenticacionFalsa(),
            IngresosFalso(self.ruta_rostro),
            CamarasFalso(),
        )
        self.servidor = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        self.hilo = threading.Thread(
            target=self.servidor.serve_forever,
            daemon=True,
        )
        self.hilo.start()
        self.puerto = self.servidor.server_address[1]

    def tearDown(self):
        self.servidor.shutdown()
        self.servidor.server_close()
        self.hilo.join(timeout=2)
        self.temporal.cleanup()

    @staticmethod
    def _crear_galeria(carpeta: Path, nombre: str):
        galeria = carpeta / nombre
        galeria.mkdir()
        imagen = np.zeros((20, 20, 3), dtype=np.uint8)
        cv2.imwrite(str(galeria / "muestra.jpg"), imagen)

    def _solicitar(self, metodo, ruta, datos=None, cabeceras_extra=None):
        conexion = http.client.HTTPConnection(
            "127.0.0.1",
            self.puerto,
            timeout=3,
        )
        cuerpo = None if datos is None else json.dumps(datos)
        cabeceras = (
            {}
            if datos is None
            else {"Content-Type": "application/json"}
        )
        cabeceras.update(cabeceras_extra or {})
        conexion.request(metodo, ruta, cuerpo, cabeceras)
        respuesta = conexion.getresponse()
        contenido = respuesta.read()
        estado = respuesta.status
        cabeceras_respuesta = dict(respuesta.getheaders())
        conexion.close()
        return estado, cabeceras_respuesta, contenido

    def test_contratos_get_y_mjpeg(self):
        estado, _, cuerpo = self._solicitar("GET", "/")
        self.assertEqual((estado, cuerpo), (200, b"witcam"))
        estado, cabeceras, cuerpo = self._solicitar(
            "GET",
            "/placeholder",
        )
        self.assertEqual(estado, 200)
        self.assertEqual(cabeceras["Content-Type"], "image/jpeg")
        self.assertTrue(cuerpo.startswith(b"\xff\xd8"))
        estado, _, cuerpo = self._solicitar(
            "GET",
            "/api/status",
            cabeceras_extra={"Authorization": "Bearer token-prueba"},
        )
        datos = json.loads(cuerpo)
        self.assertEqual(estado, 200)
        self.assertEqual(
            set(datos),
            {
                "running",
                "streaming",
                "last_error",
                "last_event",
                "detections",
                "references_count",
                "has_frame",
                "references_files",
                "pending_files",
                "gallery_signature",
                "similarity_threshold",
            },
        )
        estado, _, cuerpo = self._solicitar(
            "GET",
            "/api/list",
            cabeceras_extra={"Authorization": "Bearer token-prueba"},
        )
        listado = json.loads(cuerpo)
        self.assertEqual(estado, 200)
        self.assertEqual(
            set(listado),
            {"references", "pending", "gallery_signature"},
        )
        self.assertEqual(
            set(listado["references"][0]),
            {"name", "url", "modified", "sampleCount"},
        )
        estado, cabeceras, cuerpo = self._solicitar(
            "GET",
            listado["references"][0]["url"],
            cabeceras_extra={"Authorization": "Bearer token-prueba"},
        )
        self.assertEqual(estado, 200)
        self.assertEqual(cabeceras["Content-Type"], "image/jpeg")
        self.assertTrue(cuerpo.startswith(b"\xff\xd8"))

        conexion = http.client.HTTPConnection(
            "127.0.0.1",
            self.puerto,
            timeout=3,
        )
        conexion.request("GET", "/video_feed?token=token-prueba")
        respuesta = conexion.getresponse()
        fragmento = respuesta.read(60)
        self.assertEqual(respuesta.status, 200)
        self.assertIn(b"--frame", fragmento)
        conexion.close()

        estado, _, cuerpo = self._solicitar("GET", "/video_feed")
        self.assertEqual(estado, 401)
        self.assertFalse(json.loads(cuerpo)["ok"])

    def test_error_inesperado_get_no_expone_detalles_internos(self):
        with self.assertLogs("backend.api.handler", level="ERROR"):
            estado, _, cuerpo = self._solicitar(
                "GET",
                "/api/auth/session",
                cabeceras_extra={"Authorization": "Bearer token-invalido"},
            )
        respuesta = json.loads(cuerpo)
        self.assertEqual(estado, 500)
        self.assertIn("error interno", respuesta["error"])
        self.assertNotIn("Token incorrecto", respuesta["error"])

    def test_json_malformado_recibe_un_mensaje_publico(self):
        conexion = http.client.HTTPConnection(
            "127.0.0.1",
            self.puerto,
            timeout=3,
        )
        conexion.request(
            "POST",
            "/api/auth/login",
            "{json-incompleto",
            {"Content-Type": "application/json"},
        )
        respuesta = conexion.getresponse()
        contenido = json.loads(respuesta.read())
        conexion.close()
        self.assertEqual(respuesta.status, 400)
        self.assertEqual(
            contenido["error"],
            "El contenido de la solicitud no es un JSON valido",
        )

    def test_contratos_post_y_operaciones(self):
        estado, _, cuerpo = self._solicitar(
            "POST",
            "/api/start",
            {"source": 0, "analysis": False, "cameraId": 17},
            {"Authorization": "Bearer token-prueba"},
        )
        self.assertEqual(estado, 200)
        self.assertEqual(json.loads(cuerpo), {"ok": True})
        self.assertEqual(self.monitoreo.fuente, 0)
        self.assertFalse(self.monitoreo.analizar)
        self.assertEqual(self.monitoreo.id_camara, 17)

        estado, _, cuerpo = self._solicitar("POST", "/api/stop", {})
        self.assertEqual(estado, 401)
        self.assertFalse(json.loads(cuerpo)["ok"])

        estado, _, cuerpo = self._solicitar(
            "POST",
            "/api/stop",
            {},
            {"Authorization": "Bearer token-prueba"},
        )
        self.assertEqual(estado, 200)
        self.assertEqual(json.loads(cuerpo), {"ok": True})
        operaciones = [
            ("/api/approve", {"file": "Alice"}),
            ("/api/unapprove", {"file": "Alice"}),
            (
                "/api/rename",
                {
                    "file": "Alice",
                    "newName": "Alice Nueva",
                    "type": "pending",
                },
            ),
            ("/api/reject", {"file": "Alice_Nueva"}),
        ]
        for ruta, datos in operaciones:
            estado, _, cuerpo = self._solicitar(
                "POST",
                ruta,
                datos,
                {"Authorization": "Bearer token-prueba"},
            )
            self.assertEqual(estado, 200)
            self.assertEqual(json.loads(cuerpo), {"ok": True})
        estado, _, cuerpo = self._solicitar(
            "POST",
            "/api/reject",
            {"file": "NoExiste"},
            {"Authorization": "Bearer token-prueba"},
        )
        self.assertEqual(estado, 400)
        self.assertEqual(json.loads(cuerpo)["ok"], False)

    def test_contratos_autenticacion(self):
        estado, _, cuerpo = self._solicitar(
            "POST",
            "/api/auth/register",
            {"nombreUsuario": "matias"},
        )
        self.assertEqual(estado, 201)
        self.assertTrue(json.loads(cuerpo)["ok"])

        estado, _, cuerpo = self._solicitar(
            "POST",
            "/api/auth/login",
            {"nombreUsuario": "matias", "contrasena": "segura123"},
        )
        login = json.loads(cuerpo)
        self.assertEqual(estado, 200)
        self.assertEqual(login["token"], "token-prueba")

        conexion = http.client.HTTPConnection(
            "127.0.0.1",
            self.puerto,
            timeout=3,
        )
        conexion.request(
            "GET",
            "/api/auth/session",
            headers={"Authorization": "Bearer token-prueba"},
        )
        respuesta = conexion.getresponse()
        sesion = json.loads(respuesta.read())
        conexion.close()
        self.assertEqual(respuesta.status, 200)
        self.assertEqual(sesion["user"]["nombreUsuario"], "matias")

        estado, _, cuerpo = self._solicitar(
            "POST",
            "/api/perfil",
            {
                "nombre": "Matias",
                "apellido": "Actualizado",
                "nombreUsuario": "matias.nuevo",
                "correo": "nuevo@example.com",
                "telefono": "",
            },
            {"Authorization": "Bearer token-prueba"},
        )
        perfil = json.loads(cuerpo)
        self.assertEqual(estado, 200)
        self.assertEqual(perfil["user"]["nombreUsuario"], "matias.nuevo")

    def test_registro_duplicado_responde_conflicto(self):
        estado, _, cuerpo = self._solicitar(
            "POST",
            "/api/auth/register",
            {"nombreUsuario": "duplicado"},
        )
        respuesta = json.loads(cuerpo)
        self.assertEqual(estado, 409)
        self.assertFalse(respuesta["ok"])

    def test_login_inexistente_no_entrega_token(self):
        estado, _, cuerpo = self._solicitar(
            "POST",
            "/api/auth/login",
            {"nombreUsuario": "no-existe", "contrasena": "segura123"},
        )
        respuesta = json.loads(cuerpo)
        self.assertEqual(estado, 401)
        self.assertFalse(respuesta["ok"])
        self.assertNotIn("token", respuesta)

    def test_resumen_cuenta_exige_sesion_y_devuelve_datos_reales(self):
        estado, _, cuerpo = self._solicitar("GET", "/api/cuenta/resumen")
        self.assertEqual(estado, 401)
        self.assertFalse(json.loads(cuerpo)["ok"])

        conexion = http.client.HTTPConnection(
            "127.0.0.1",
            self.puerto,
            timeout=3,
        )
        conexion.request(
            "GET",
            "/api/cuenta/resumen",
            headers={"Authorization": "Bearer token-prueba"},
        )
        respuesta = conexion.getresponse()
        resumen = json.loads(respuesta.read())
        conexion.close()
        self.assertEqual(respuesta.status, 200)
        self.assertEqual(resumen["nombreCuenta"], "Cuenta Prueba")
        self.assertEqual(resumen["subusuariosActivos"], 2)

    def test_subusuarios_exigen_sesion_y_conservan_contrato(self):
        estado, _, _ = self._solicitar("GET", "/api/subusuarios")
        self.assertEqual(estado, 401)

        conexion = http.client.HTTPConnection("127.0.0.1", self.puerto, timeout=3)
        conexion.request(
            "GET",
            "/api/subusuarios",
            headers={"Authorization": "Bearer token-prueba"},
        )
        respuesta = conexion.getresponse()
        listado = json.loads(respuesta.read())
        conexion.close()
        self.assertEqual(respuesta.status, 200)
        self.assertEqual(listado["permisos"][0]["codigo"], "ver")
        self.assertEqual(listado["filtroEstado"], "activo")

        conexion = http.client.HTTPConnection("127.0.0.1", self.puerto, timeout=3)
        conexion.request(
            "GET",
            "/api/subusuarios?estado=inactivo",
            headers={"Authorization": "Bearer token-prueba"},
        )
        respuesta = conexion.getresponse()
        error = json.loads(respuesta.read())
        conexion.close()
        self.assertEqual(respuesta.status, 400)
        self.assertFalse(error["ok"])

        conexion = http.client.HTTPConnection("127.0.0.1", self.puerto, timeout=3)
        conexion.request(
            "GET",
            "/api/subusuarios?estado=activo&usuario=ana&permiso=ver&pagina=2",
            headers={"Authorization": "Bearer token-prueba"},
        )
        respuesta = conexion.getresponse()
        listado = json.loads(respuesta.read())
        conexion.close()
        self.assertEqual(respuesta.status, 200)
        self.assertEqual(listado["pagina"], 2)

        conexion = http.client.HTTPConnection("127.0.0.1", self.puerto, timeout=3)
        conexion.request(
            "GET",
            "/api/subusuarios?estado=todos",
            headers={"Authorization": "Bearer token-prueba"},
        )
        respuesta = conexion.getresponse()
        error = json.loads(respuesta.read())
        conexion.close()
        self.assertEqual(respuesta.status, 400)
        self.assertFalse(error["ok"])

        conexion = http.client.HTTPConnection("127.0.0.1", self.puerto, timeout=3)
        conexion.request(
            "POST",
            "/api/subusuarios",
            json.dumps({"nombreUsuario": "ana", "permisos": ["ver"]}),
            {
                "Authorization": "Bearer token-prueba",
                "Content-Type": "application/json",
            },
        )
        respuesta = conexion.getresponse()
        creado = json.loads(respuesta.read())
        conexion.close()
        self.assertEqual(respuesta.status, 201)
        self.assertEqual(creado["subusuario"]["nombreUsuario"], "ana")

        conexion = http.client.HTTPConnection("127.0.0.1", self.puerto, timeout=3)
        conexion.request(
            "POST",
            "/api/subusuarios/estado",
            json.dumps({"id": 2, "estado": "inactivo"}),
            {
                "Authorization": "Bearer token-prueba",
                "Content-Type": "application/json",
            },
        )
        respuesta = conexion.getresponse()
        actualizado = json.loads(respuesta.read())
        conexion.close()
        self.assertEqual(respuesta.status, 200)
        self.assertEqual(actualizado["estado"], "Inactivo")

        conexion = http.client.HTTPConnection("127.0.0.1", self.puerto, timeout=3)
        conexion.request(
            "POST",
            "/api/subusuarios/editar",
            json.dumps({
                "id": 2,
                "permisos": ["ver"],
            }),
            {
                "Authorization": "Bearer token-prueba",
                "Content-Type": "application/json",
            },
        )
        respuesta = conexion.getresponse()
        editado = json.loads(respuesta.read())
        conexion.close()
        self.assertEqual(respuesta.status, 200)
        self.assertEqual(editado["subusuario"]["permisos"], ["ver"])

    def test_ingresos_exigen_sesion_y_devuelven_datos_paginados(self):
        estado, _, cuerpo = self._solicitar("GET", "/api/ingresos")
        self.assertEqual(estado, 401)
        self.assertFalse(json.loads(cuerpo)["ok"])

        conexion = http.client.HTTPConnection(
            "127.0.0.1",
            self.puerto,
            timeout=3,
        )
        conexion.request(
            "GET",
            "/api/ingresos?pagina=2&limite=10",
            headers={"Authorization": "Bearer token-prueba"},
        )
        respuesta = conexion.getresponse()
        listado = json.loads(respuesta.read())
        conexion.close()
        self.assertEqual(respuesta.status, 200)
        self.assertEqual(listado["pagina"], 2)
        self.assertEqual(listado["limite"], 10)
        self.assertEqual(listado["ingresos"][0]["idDeteccion"], 35)

        conexion = http.client.HTTPConnection(
            "127.0.0.1",
            self.puerto,
            timeout=3,
        )
        conexion.request(
            "GET",
            "/api/ingresos/camaras",
            headers={"Authorization": "Bearer token-prueba"},
        )
        respuesta = conexion.getresponse()
        camaras = json.loads(respuesta.read())
        conexion.close()
        self.assertEqual(respuesta.status, 200)
        self.assertEqual(camaras["camaras"][0]["id"], 4)

        estado, _, cuerpo = self._solicitar(
            "GET",
            "/api/ingresos/historial?idPersona=12",
            cabeceras_extra={"Authorization": "Bearer token-prueba"},
        )
        historial = json.loads(cuerpo)
        self.assertEqual(estado, 200)
        self.assertEqual(historial["persona"]["id"], 12)

        estado, cabeceras, cuerpo = self._solicitar(
            "GET",
            "/api/ingresos/deteccion-rostro?idDeteccion=35",
            cabeceras_extra={"Authorization": "Bearer token-prueba"},
        )
        self.assertEqual(estado, 200)
        self.assertEqual(cabeceras["Content-Type"], "image/jpeg")
        self.assertTrue(cuerpo.startswith(b"\xff\xd8"))

        estado, cabeceras, cuerpo = self._solicitar(
            "GET",
            "/api/ingresos/rostro?idPersona=12",
            cabeceras_extra={"Authorization": "Bearer token-prueba"},
        )
        self.assertEqual(estado, 200)
        self.assertEqual(cabeceras["Content-Type"], "image/jpeg")
        self.assertTrue(cuerpo.startswith(b"\xff\xd8"))

        estado, _, cuerpo = self._solicitar(
            "POST",
            "/api/ingresos/lista-observacion",
            {"idPersona": 12, "motivo": "Conducta sospechosa"},
            {"Authorization": "Bearer token-prueba"},
        )
        agregado = json.loads(cuerpo)
        self.assertEqual(estado, 201)
        self.assertTrue(agregado["enListaObservacion"])
        self.assertEqual(agregado["motivo"], "Conducta sospechosa")

        estado, _, cuerpo = self._solicitar(
            "GET",
            "/api/lista-observacion?pagina=2&limite=10",
            cabeceras_extra={"Authorization": "Bearer token-prueba"},
        )
        listado_observacion = json.loads(cuerpo)
        self.assertEqual(estado, 200)
        self.assertEqual(listado_observacion["registros"][0]["idLista"], 8)
        self.assertEqual(listado_observacion["pagina"], 2)
        self.assertEqual(listado_observacion["limite"], 10)

        estado, _, cuerpo = self._solicitar(
            "POST",
            "/api/ingresos/quitar-lista-observacion",
            {"idPersona": 12},
            {"Authorization": "Bearer token-prueba"},
        )
        quitado = json.loads(cuerpo)
        self.assertEqual(estado, 200)
        self.assertFalse(quitado["enListaObservacion"])

        estado, _, cuerpo = self._solicitar(
            "POST",
            "/api/ingresos/renombrar-persona",
            {"idPersona": 12, "nombre": "Matias"},
            {"Authorization": "Bearer token-prueba"},
        )
        renombrada = json.loads(cuerpo)
        self.assertEqual(estado, 200)
        self.assertEqual(renombrada["nombrePersona"], "Matias")

        estado, _, cuerpo = self._solicitar(
            "POST",
            "/api/ingresos/eliminar-persona",
            {"idPersona": 12},
            {"Authorization": "Bearer token-prueba"},
        )
        eliminada = json.loads(cuerpo)
        self.assertEqual(estado, 200)
        self.assertTrue(eliminada["ok"])
        self.assertEqual(eliminada["idPersona"], 12)

    def test_camaras_exigen_sesion_y_exponen_crud(self):
        estado, _, _ = self._solicitar("GET", "/api/camaras")
        self.assertEqual(estado, 401)

        for ruta, datos, esperado in (
            ("/api/grupos-camara/guardar", {"grupos": []}, 200),
            ("/api/camaras/crear", {"nombre": "Acceso"}, 201),
            ("/api/camaras/editar", {"id": 9}, 200),
            ("/api/camaras/eliminar", {"id": 9}, 200),
        ):
            conexion = http.client.HTTPConnection(
                "127.0.0.1",
                self.puerto,
                timeout=3,
            )
            conexion.request(
                "POST",
                ruta,
                json.dumps(datos),
                {
                    "Content-Type": "application/json",
                    "Authorization": "Bearer token-prueba",
                },
            )
            respuesta = conexion.getresponse()
            cuerpo = json.loads(respuesta.read())
            conexion.close()
            self.assertEqual(respuesta.status, esperado)
            self.assertTrue(cuerpo["ok"])


if __name__ == "__main__":
    unittest.main()
