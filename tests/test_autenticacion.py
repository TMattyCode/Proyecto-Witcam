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
    PermisoDenegado,
    RegistroDuplicado,
)


class RepositorioUsuariosFalso:
    def __init__(self):
        self.registrado = None
        self.hash_guardado = None
        self.ultimo_acceso = None
        self.cantidad_registros = 0
        self.cuenta_resumen_solicitada = None
        self.subusuario_registrado = None
        self.subusuarios_cuenta_solicitada = None
        self.subusuarios_estado_solicitado = None
        self.filtros_subusuarios = None
        self.cambio_estado_solicitado = None
        self.edicion_solicitada = None

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

    def obtener_permisos(self, id_usuario):
        return ["ver", "anadir", "editar", "eliminar", "configuracion"]

    def obtener_resumen_cuenta(self, id_cuenta):
        self.cuenta_resumen_solicitada = id_cuenta
        return {
            "nombreCuenta": "Cuenta Prueba",
            "subusuariosActivos": 2,
        }

    def listar_subusuarios(self, id_cuenta, filtros):
        self.subusuarios_cuenta_solicitada = id_cuenta
        self.subusuarios_estado_solicitado = filtros["estado"]
        self.filtros_subusuarios = filtros
        return {
            "total": 0,
            "pagina": filtros["pagina"],
            "limite": filtros["limite"],
            "permisos": [
                {"id": 1, "codigo": "ver", "nombre": "Ver", "descripcion": None}
            ],
            "subusuarios": [],
        }

    def registrar_subusuario(
        self,
        id_cuenta,
        datos,
        password_hash,
        codigos_permisos,
    ):
        self.subusuario_registrado = {
            "idCuenta": id_cuenta,
            "datos": datos,
            "password_hash": password_hash,
            "permisos": codigos_permisos,
        }
        return {
            "id": 2,
            "nombre": datos["nombre"],
            "apellido": datos["apellido"],
            "nombreUsuario": datos["nombre_usuario"],
            "correo": datos["correo"],
            "telefono": datos["telefono"],
            "estado": "Activo",
            "fechaCreacion": "2026-08-04T12:30:00",
            "ultimoAcceso": None,
            "permisos": codigos_permisos,
        }

    def actualizar_estado_subusuario(self, id_cuenta, id_usuario, estado):
        self.cambio_estado_solicitado = (id_cuenta, id_usuario, estado)
        return id_usuario == 2

    def actualizar_permisos_subusuario(
        self,
        id_cuenta,
        id_usuario,
        permisos,
    ):
        self.edicion_solicitada = {
            "idCuenta": id_cuenta,
            "idUsuario": id_usuario,
            "permisos": permisos,
        }
        return id_usuario == 2


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
        self.assertEqual(
            login["user"]["permisos"],
            ["ver", "anadir", "editar", "eliminar", "configuracion"],
        )
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

    def test_resumen_usa_la_cuenta_de_la_sesion(self):
        self.servicio.registrar(self.datos)
        login = self.servicio.iniciar_sesion(
            {"nombreUsuario": "matias", "contrasena": "segura123"}
        )
        resumen = self.servicio.obtener_resumen_cuenta(login["token"])
        self.assertEqual(self.repositorio.cuenta_resumen_solicitada, 1)
        self.assertEqual(resumen["nombreCuenta"], "Cuenta Prueba")
        self.assertEqual(resumen["subusuariosActivos"], 2)

    def test_administrador_lista_y_crea_subusuario_en_su_cuenta(self):
        self.servicio.registrar(self.datos)
        login = self.servicio.iniciar_sesion(
            {"nombreUsuario": "matias", "contrasena": "segura123"}
        )
        listado = self.servicio.listar_subusuarios(login["token"])
        self.assertEqual(self.repositorio.subusuarios_cuenta_solicitada, 1)
        self.assertEqual(self.repositorio.subusuarios_estado_solicitado, "Activo")
        self.assertEqual(listado["permisos"][0]["codigo"], "ver")

        self.servicio.listar_subusuarios(
            login["token"],
            {
                "estado": "activo",
                "usuario": "ana",
                "permiso": "ver",
                "registroDesde": "2026-08-01",
                "sinAcceso": "true",
                "pagina": "2",
                "limite": "25",
            },
        )
        filtros = self.repositorio.filtros_subusuarios
        self.assertEqual(filtros["usuario"], "ana")
        self.assertEqual(filtros["permiso"], "ver")
        self.assertTrue(filtros["sin_acceso"])
        self.assertEqual(filtros["pagina"], 2)

        datos_subusuario = {
            "nombre": "Ana",
            "apellido": "Prueba",
            "nombreUsuario": "ana",
            "correo": "ANA@example.com",
            "telefono": "",
            "contrasena": "segura123",
            "confirmarContrasena": "segura123",
            "permisos": ["ver", "ver"],
            "idCuenta": 999,
            "rol": "Administrador",
        }
        resultado = self.servicio.registrar_subusuario(
            login["token"],
            datos_subusuario,
        )
        guardado = self.repositorio.subusuario_registrado
        self.assertEqual(guardado["idCuenta"], 1)
        self.assertEqual(guardado["permisos"], ["ver"])
        self.assertEqual(guardado["datos"]["correo"], "ana@example.com")
        self.assertNotIn("segura123", guardado["password_hash"])
        self.assertEqual(resultado["subusuario"]["estado"], "Activo")

    def test_subusuario_no_puede_gestionar_otros_subusuarios(self):
        self.servicio.registrar(self.datos)
        login = self.servicio.iniciar_sesion(
            {"nombreUsuario": "matias", "contrasena": "segura123"}
        )
        self.servicio._sesiones[login["token"]]["rol"] = "Subusuario"
        with self.assertRaises(ErrorAutenticacion):
            self.servicio.listar_subusuarios(login["token"])

    def test_sesion_solo_autoriza_permisos_efectivos(self):
        self.servicio.registrar(self.datos)
        login = self.servicio.iniciar_sesion(
            {"nombreUsuario": "matias", "contrasena": "segura123"}
        )
        self.servicio._sesiones[login["token"]]["rol"] = "Subusuario"
        self.servicio._sesiones[login["token"]]["permisos"] = ["ver"]

        usuario = self.servicio.exigir_permiso(login["token"], "ver")
        self.assertEqual(usuario["id"], 1)
        with self.assertRaises(PermisoDenegado):
            self.servicio.exigir_permiso(login["token"], "eliminar")

    def test_rechaza_filtro_de_subusuarios_desconocido(self):
        self.servicio.registrar(self.datos)
        login = self.servicio.iniciar_sesion(
            {"nombreUsuario": "matias", "contrasena": "segura123"}
        )
        with self.assertRaisesRegex(ValueError, "subusuarios activos"):
            self.servicio.listar_subusuarios(login["token"], "todos")

        with self.assertRaisesRegex(ValueError, "rango de fecha de registro"):
            self.servicio.listar_subusuarios(
                login["token"],
                {
                    "registroDesde": "2026-08-10",
                    "registroHasta": "2026-08-01",
                },
            )
        with self.assertRaisesRegex(ValueError, "Nunca se ha conectado"):
            self.servicio.listar_subusuarios(
                login["token"],
                {"sinAcceso": "true", "accesoDesde": "2026-08-01"},
            )
        with self.assertRaisesRegex(ValueError, "limite"):
            self.servicio.listar_subusuarios(
                login["token"],
                {"limite": "101"},
            )

    def test_desactiva_subusuario_de_la_cuenta_y_cierra_sus_sesiones(self):
        self.servicio.registrar(self.datos)
        login = self.servicio.iniciar_sesion(
            {"nombreUsuario": "matias", "contrasena": "segura123"}
        )
        self.servicio._sesiones["token-subusuario"] = {
            "id": 2,
            "idCuenta": 1,
            "rol": "Subusuario",
        }

        resultado = self.servicio.actualizar_estado_subusuario(
            login["token"],
            {"id": 2, "estado": "inactivo"},
        )

        self.assertEqual(self.repositorio.cambio_estado_solicitado, (1, 2, "Inactivo"))
        self.assertEqual(resultado["estado"], "Inactivo")
        with self.assertRaises(CredencialesInvalidas):
            self.servicio.obtener_sesion("token-subusuario")

    def test_reactivar_se_rechaza_y_valida_identificador(self):
        self.servicio.registrar(self.datos)
        login = self.servicio.iniciar_sesion(
            {"nombreUsuario": "matias", "contrasena": "segura123"}
        )
        with self.assertRaisesRegex(ErrorAutenticacion, "solo se pueden desactivar"):
            self.servicio.actualizar_estado_subusuario(
                login["token"],
                {"id": 2, "estado": "activo"},
            )

        for id_invalido in (None, True, 0, "2"):
            with self.subTest(id=id_invalido):
                with self.assertRaises(ErrorAutenticacion):
                    self.servicio.actualizar_estado_subusuario(
                        login["token"],
                        {"id": id_invalido, "estado": "inactivo"},
                    )

    def test_administrador_solo_actualiza_permisos_del_subusuario(self):
        self.servicio.registrar(self.datos)
        login = self.servicio.iniciar_sesion(
            {"nombreUsuario": "matias", "contrasena": "segura123"}
        )
        datos = {
            "id": 2,
            "permisos": ["ver"],
        }
        resultado = self.servicio.editar_subusuario(login["token"], datos)
        guardado = self.repositorio.edicion_solicitada
        self.assertEqual(guardado["idCuenta"], 1)
        self.assertEqual(guardado["permisos"], ["ver"])
        self.assertEqual(resultado["subusuario"]["permisos"], ["ver"])

        with self.assertRaisesRegex(ErrorAutenticacion, "solo puede modificar"):
            self.servicio.editar_subusuario(
                login["token"],
                {**datos, "correo": "otro@example.com"},
            )


if __name__ == "__main__":
    unittest.main()
