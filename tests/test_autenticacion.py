import unittest
from types import SimpleNamespace

from backend.aplicacion.autenticacion import (
    ServicioAutenticacion,
    crear_hash_password,
    verificar_password,
)
from backend.exceptions import (
    CredencialesInvalidas,
    ErrorAutenticacion,
    RegistroDuplicado,
)


class RepositorioUsuariosFalso:
    def __init__(self):
        self.registrado = None
        self.hash_guardado = None
        self.ultimo_acceso = None
        self.cantidad_registros = 0

    def registrar_administrador(self, datos, password_hash):
        if self.registrado is not None and (
            datos["nombre_usuario"].casefold()
            == self.registrado["nombre_usuario"].casefold()
            or datos["correo"].casefold() == self.registrado["correo"].casefold()
        ):
            raise RegistroDuplicado("Registro duplicado")
        self.cantidad_registros += 1
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
            "confirmarContrasena": "segura123",
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

    def test_registro_rechaza_datos_invalidos_sin_llamar_repositorio(self):
        casos = (
            ("valor nulo", {"nombre": None}),
            ("password distinta", {"confirmarContrasena": "otra1234"}),
            ("correo invalido", {"correo": "correo-sin-dominio"}),
            ("usuario con espacios", {"nombreUsuario": "matias prueba"}),
            ("telefono invalido", {"telefono": "llamame pronto"}),
            ("campo demasiado largo", {"nombre": "a" * 101}),
        )
        for nombre_caso, cambio in casos:
            with self.subTest(nombre_caso):
                datos = {**self.datos, **cambio}
                with self.assertRaises(ErrorAutenticacion):
                    self.servicio.registrar(datos)
                self.assertEqual(self.repositorio.cantidad_registros, 0)

    def test_registro_duplicado_no_crea_un_segundo_usuario(self):
        self.servicio.registrar(self.datos)
        duplicado_usuario = {
            **self.datos,
            "nombreUsuario": "MATIAS",
            "correo": "otro@example.com",
        }
        with self.assertRaises(RegistroDuplicado):
            self.servicio.registrar(duplicado_usuario)
        self.assertEqual(self.repositorio.cantidad_registros, 1)

        duplicado_correo = {
            **self.datos,
            "nombreUsuario": "otro",
            "correo": "MATIAS@EXAMPLE.COM",
        }
        with self.assertRaises(RegistroDuplicado):
            self.servicio.registrar(duplicado_correo)
        self.assertEqual(self.repositorio.cantidad_registros, 1)

    def test_login_inexistente_no_crea_usuario_ni_sesion(self):
        with self.assertRaises(CredencialesInvalidas):
            self.servicio.iniciar_sesion(
                {"nombreUsuario": "no-existe", "contrasena": "segura123"}
            )
        self.assertEqual(self.repositorio.cantidad_registros, 0)
        self.assertEqual(self.servicio._sesiones, {})

    def test_login_rechaza_valores_nulos(self):
        with self.assertRaises(CredencialesInvalidas):
            self.servicio.iniciar_sesion(
                {"nombreUsuario": None, "contrasena": None}
            )


if __name__ == "__main__":
    unittest.main()
