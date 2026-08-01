import unittest
from types import SimpleNamespace

from backend.aplicacion.autenticacion import (
    ServicioAutenticacion,
    crear_hash_password,
    verificar_password,
)
from backend.exceptions import CredencialesInvalidas


class RepositorioUsuariosFalso:
    def __init__(self):
        self.registrado = None
        self.hash_guardado = None
        self.ultimo_acceso = None

    def registrar_administrador(self, datos, password_hash):
        self.registrado = datos
        self.hash_guardado = password_hash
        return {
            "id": 1,
            "idCuenta": 1,
            "nombreUsuario": datos["nombre_usuario"],
        }

    def buscar_para_login(self, nombre_usuario):
        if self.registrado is None or nombre_usuario != "matias":
            return None
        return SimpleNamespace(
            id_usuario=1,
            id_cuenta=1,
            nombre="Matias",
            apellido="Prueba",
            nombre_usuario="matias",
            correo="matias@example.com",
            password_hash=self.hash_guardado,
            nombre_rol="Administrador",
            nombre_cuenta="Cuenta Prueba",
            nombre_estado="Activo",
        )

    def registrar_acceso(self, id_usuario):
        self.ultimo_acceso = id_usuario


class PruebasAutenticacion(unittest.TestCase):
    def setUp(self):
        self.repositorio = RepositorioUsuariosFalso()
        self.servicio = ServicioAutenticacion(self.repositorio)
        self.datos = {
            "nombreCuenta": "Cuenta Prueba",
            "nombreUsuario": "matias",
            "contrasena": "segura123",
            "correo": "MATIAS@example.com",
            "telefono": "",
            "nombre": "Matias",
            "apellido": "Prueba",
        }

    def test_hash_no_guarda_password_y_se_puede_verificar(self):
        password_hash = crear_hash_password("segura123")
        self.assertNotIn("segura123", password_hash)
        self.assertTrue(verificar_password("segura123", password_hash))
        self.assertFalse(verificar_password("incorrecta", password_hash))

    def test_registro_login_y_sesion(self):
        registro = self.servicio.registrar(self.datos)
        self.assertTrue(registro["ok"])
        self.assertEqual(self.repositorio.registrado["correo"], "matias@example.com")

        login = self.servicio.iniciar_sesion(
            {"nombreUsuario": "matias", "contrasena": "segura123"}
        )
        self.assertTrue(login["ok"])
        self.assertEqual(login["user"]["rol"], "Administrador")
        self.assertEqual(self.repositorio.ultimo_acceso, 1)
        self.assertEqual(
            self.servicio.obtener_sesion(login["token"])["user"]["id"],
            1,
        )

    def test_login_rechaza_password_incorrecto(self):
        self.servicio.registrar(self.datos)
        with self.assertRaises(CredencialesInvalidas):
            self.servicio.iniciar_sesion(
                {"nombreUsuario": "matias", "contrasena": "incorrecta"}
            )


if __name__ == "__main__":
    unittest.main()
