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


JPEG_MINIMO = b"\xff\xd8\xff\xd9"


class MonitoreoFalso:
    def __init__(self):
        self.iniciado = False
        self.detenido = False

    def iniciar(self):
        self.iniciado = True

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
            "nombreUsuario": "matias",
            "rol": "Administrador",
        }
        self.token = "token-prueba"

    def registrar(self, datos):
        return {"ok": True, "user": self.usuario}

    def iniciar_sesion(self, datos):
        return {"ok": True, "token": self.token, "user": self.usuario}

    def obtener_sesion(self, token):
        if token != self.token:
            raise RuntimeError("Token incorrecto")
        return {"ok": True, "user": self.usuario}

    def cerrar_sesion(self, token):
        return None


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

    def _solicitar(self, metodo, ruta, datos=None):
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
        estado, _, cuerpo = self._solicitar("GET", "/api/status")
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
        estado, _, cuerpo = self._solicitar("GET", "/api/list")
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

        conexion = http.client.HTTPConnection(
            "127.0.0.1",
            self.puerto,
            timeout=3,
        )
        conexion.request("GET", "/video_feed")
        respuesta = conexion.getresponse()
        fragmento = respuesta.read(60)
        self.assertEqual(respuesta.status, 200)
        self.assertIn(b"--frame", fragmento)
        conexion.close()

    def test_contratos_post_y_operaciones(self):
        for ruta in ("/api/start", "/api/stop"):
            estado, _, cuerpo = self._solicitar("POST", ruta, {})
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
            estado, _, cuerpo = self._solicitar("POST", ruta, datos)
            self.assertEqual(estado, 200)
            self.assertEqual(json.loads(cuerpo), {"ok": True})
        estado, _, cuerpo = self._solicitar(
            "POST",
            "/api/reject",
            {"file": "NoExiste"},
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


if __name__ == "__main__":
    unittest.main()
