import unittest
from contextlib import contextmanager
from types import SimpleNamespace

from backend.aplicacion.camaras import ServicioCamaras
from backend.database.camaras import RepositorioCamaras, _es_error_duplicado
from backend.exceptions import ErrorCamara
import pyodbc


class AutenticacionCamarasFalsa:
    def __init__(self, rol="Administrador"):
        self.usuario = {
            "id": 5,
            "idCuenta": 7,
            "rol": rol,
        }

    def obtener_sesion(self, token):
        if token != "token-prueba":
            raise RuntimeError("Token inesperado")
        return {"ok": True, "user": self.usuario}


class RepositorioCamarasFalso:
    def __init__(self):
        self.llamada = None
        self.ultima_creacion = None

    def listar(self, id_cuenta, id_usuario, es_administrador):
        self.llamada = ("listar", id_cuenta, id_usuario, es_administrador)
        return {
            "grupos": [{"id": 3, "nombre": "Entrada"}],
            "camaras": [
                {
                    "id": 9,
                    "nombre": "Acceso",
                    "tipo": "onvif",
                    "grupoCamaraId": 3,
                    "direccionIp": "192.168.1.20",
                    "usuarioConexion": "operador",
                    "tienePassword": True,
                },
                {
                    "id": 10,
                    "nombre": "Webcam",
                    "tipo": "webcam",
                    "grupoCamaraId": 3,
                    "fuente": 0,
                },
            ],
        }

    def guardar_grupos(self, id_cuenta, grupos):
        self.llamada = ("grupos", id_cuenta, grupos)

    def crear(self, id_cuenta, datos):
        self.llamada = ("crear", id_cuenta, datos)
        self.ultima_creacion = (id_cuenta, datos)
        return 9

    def editar(self, id_cuenta, id_camara, datos):
        self.llamada = ("editar", id_cuenta, id_camara, datos)
        return id_camara == 9

    def eliminar(self, id_cuenta, id_camara):
        self.llamada = ("eliminar", id_cuenta, id_camara)
        return id_camara == 9


class CursorPersistenciaFalso:
    def __init__(self, *, camaras_activas=False):
        self.camaras_activas = camaras_activas
        self.consulta = ""
        self.parametros = ()
        self.consultas = []
        self.rowcount = 1

    def execute(self, consulta, *parametros):
        self.consulta = consulta
        self.parametros = parametros
        self.consultas.append((consulta, parametros))
        if "SET gc.activo = 0" in consulta:
            self.rowcount = 0 if self.camaras_activas else 1
        else:
            self.rowcount = 1
        return self

    def fetchall(self):
        if "WITH (UPDLOCK, HOLDLOCK)" in self.consulta:
            return [
                SimpleNamespace(id_grupo_camara=1),
                SimpleNamespace(id_grupo_camara=2),
            ]
        return []

    def fetchval(self):
        if "SELECT COUNT(*)" in self.consulta:
            return 1
        return None


class ConexionPersistenciaFalsa:
    def __init__(self, *, camaras_activas=False):
        self.cursor_falso = CursorPersistenciaFalso(
            camaras_activas=camaras_activas,
        )
        self.confirmada = False
        self.revertida = False

    def cursor(self):
        return self.cursor_falso

    def commit(self):
        self.confirmada = True

    def rollback(self):
        self.revertida = True


class ConexionesPersistenciaFalsas:
    def __init__(self, *, camaras_activas=False):
        self.conexion = ConexionPersistenciaFalsa(
            camaras_activas=camaras_activas,
        )

    @contextmanager
    def conectar(self):
        try:
            yield self.conexion
        except Exception:
            self.conexion.rollback()
            raise


class PruebasServicioCamaras(unittest.TestCase):
    def test_solo_los_codigos_sql_de_unicidad_se_tratan_como_duplicados(self):
        self.assertTrue(
            _es_error_duplicado(pyodbc.IntegrityError("23000", "Error 2627"))
        )
        self.assertFalse(
            _es_error_duplicado(pyodbc.IntegrityError("23000", "Error 547"))
        )

    def setUp(self):
        self.repositorio = RepositorioCamarasFalso()
        self.servicio = ServicioCamaras(
            self.repositorio,
            AutenticacionCamarasFalsa(),
        )

    def test_listado_usa_cuenta_y_usuario_de_la_sesion(self):
        respuesta = self.servicio.listar("token-prueba")
        self.assertEqual(
            self.repositorio.llamada,
            ("listar", 7, 5, True),
        )
        self.assertNotIn("passwordConexion", respuesta["camaras"][0])

    def test_crea_webcam_en_cuenta_autenticada(self):
        respuesta = self.servicio.crear(
            "token-prueba",
            {
                "idCuenta": 999,
                "nombre": "Webcam local",
                "tipo": "webcam",
                "grupoCamaraId": 3,
                "fuente": 0,
            },
        )
        llamada = self.repositorio.llamada
        self.assertTrue(respuesta["ok"])
        self.assertEqual(llamada[1], 7)

    def test_transmision_valida_webcam_asignada_y_su_fuente(self):
        self.servicio.validar_transmision("token-prueba", 10, 0)

        with self.assertRaisesRegex(ErrorCamara, "fuente"):
            self.servicio.validar_transmision("token-prueba", 10, 1)
        with self.assertRaisesRegex(ErrorCamara, "Solo la webcam"):
            self.servicio.validar_transmision("token-prueba", 9, None)
        with self.assertRaisesRegex(ErrorCamara, "no existe"):
            self.servicio.validar_transmision("token-prueba", 999, 0)

    def test_valida_onvif_y_password_solo_es_obligatoria_al_crear(self):
        datos = {
            "nombre": "Acceso",
            "tipo": "onvif",
            "grupoCamaraId": 3,
            "direccionIp": "192.168.1.20",
            "puertoOnvif": 80,
            "usuarioConexion": "operador",
            "passwordConexion": "",
        }
        with self.assertRaisesRegex(ValueError, "obligatoria"):
            self.servicio.crear("token-prueba", datos)

        respuesta = self.servicio.editar(
            "token-prueba",
            {**datos, "id": 9},
        )
        self.assertTrue(respuesta["ok"])

    def test_rtsp_requiere_una_url_valida_sin_datos_onvif(self):
        with self.assertRaisesRegex(ValueError, "URL RTSP"):
            self.servicio.crear(
                "token-prueba",
                {
                    "nombre": "Canal NVR",
                    "tipo": "rtsp",
                    "grupoCamaraId": 3,
                    "fuenteVideo": "http://127.0.0.1/video",
                },
            )

        self.servicio.crear(
            "token-prueba",
            {
                "nombre": "Canal NVR",
                "tipo": "rtsp",
                "grupoCamaraId": 3,
                "fuenteVideo": "rtsp://127.0.0.1:8554/camara1",
            },
        )
        datos = self.repositorio.ultima_creacion[1]
        self.assertEqual(
            datos["fuente_video"],
            "rtsp://127.0.0.1:8554/camara1",
        )
        self.assertIsNone(datos["direccion_ip"])

    def test_subusuario_solo_puede_listar(self):
        servicio = ServicioCamaras(
            self.repositorio,
            AutenticacionCamarasFalsa("Subusuario"),
        )
        listado = servicio.listar("token-prueba")
        self.assertTrue(listado["ok"])
        self.assertEqual(
            self.repositorio.llamada,
            ("listar", 7, 5, False),
        )
        with self.assertRaisesRegex(ErrorCamara, "administrador"):
            servicio.eliminar("token-prueba", {"id": 9})

    def test_camara_en_transmision_no_se_puede_editar_ni_eliminar(self):
        servicio = ServicioCamaras(
            self.repositorio,
            AutenticacionCamarasFalsa(),
            lambda id_camara: id_camara == 9,
        )
        datos = {
            "id": 9,
            "nombre": "Acceso",
            "tipo": "onvif",
            "grupoCamaraId": 3,
            "direccionIp": "192.168.1.20",
            "puertoOnvif": 80,
            "usuarioConexion": "operador",
            "passwordConexion": "",
        }

        with self.assertRaisesRegex(ErrorCamara, "mientras transmite"):
            servicio.editar("token-prueba", datos)
        with self.assertRaisesRegex(ErrorCamara, "mientras transmite"):
            servicio.eliminar("token-prueba", {"id": 9})
        self.assertIsNone(self.repositorio.llamada)

    def test_grupos_rechazan_duplicados(self):
        with self.assertRaisesRegex(ValueError, "mismo nombre"):
            self.servicio.guardar_grupos(
                "token-prueba",
                {
                    "grupos": [
                        {"id": 1, "nombre": "Entrada"},
                        {"id": "nuevo-1", "nombre": "entrada"},
                    ]
                },
            )

    def test_repositorio_impide_eliminar_todos_los_grupos(self):
        repositorio = RepositorioCamaras(None, "")
        with self.assertRaisesRegex(ErrorCamara, "al menos un grupo"):
            repositorio.guardar_grupos(7, [])

    def test_eliminar_camara_solo_la_marca_como_inactiva(self):
        conexiones = ConexionesPersistenciaFalsas()
        repositorio = RepositorioCamaras(conexiones, "")

        self.assertTrue(repositorio.eliminar(7, 9))

        consulta = conexiones.conexion.cursor_falso.consulta
        self.assertIn("SET c.activa = 0", consulta)
        self.assertNotIn("DELETE", consulta)
        self.assertTrue(conexiones.conexion.confirmada)

    def test_grupo_con_camaras_activas_no_se_desactiva(self):
        conexiones = ConexionesPersistenciaFalsas(camaras_activas=True)
        repositorio = RepositorioCamaras(conexiones, "")

        with self.assertRaisesRegex(ErrorCamara, "camaras activas"):
            repositorio.guardar_grupos(
                7,
                [{"id": 2, "nombre": "Caja", "descripcion": None}],
            )

        consultas = "\n".join(
            consulta
            for consulta, _ in conexiones.conexion.cursor_falso.consultas
        )
        self.assertIn("SET gc.activo = 0", consultas)
        self.assertIn("AND c.activa = 1", consultas)
        self.assertFalse(conexiones.conexion.confirmada)
        self.assertTrue(conexiones.conexion.revertida)


if __name__ == "__main__":
    unittest.main()
