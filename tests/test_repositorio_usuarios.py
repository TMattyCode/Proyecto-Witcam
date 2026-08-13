import unittest
from types import SimpleNamespace
from unittest.mock import patch

import pyodbc

from backend.config import ConfiguracionBaseDatos
from backend.database.conexion import FabricaConexionesSqlServer
from backend.database.usuarios import RepositorioUsuarios
from backend.exceptions import RegistroDuplicado


class CursorFalso:
    def __init__(self, error_usuario=None, filas_afectadas=1):
        self.error_usuario = error_usuario
        self.consulta = ""
        self.parametros = ()
        self.rowcount = filas_afectadas
        self.consultas = []

    def execute(self, consulta, *parametros):
        self.consulta = consulta
        self.parametros = parametros
        self.consultas.append((consulta, parametros))
        if "INSERT INTO Usuario" in consulta and self.error_usuario:
            raise self.error_usuario
        return self

    def fetchone(self):
        return SimpleNamespace(id_rol=1)

    def fetchval(self):
        if "INSERT INTO Cuenta" in self.consulta:
            return 10
        if "INSERT INTO Usuario" in self.consulta:
            return 20
        return None


class ConexionFalsa:
    def __init__(self, error_usuario=None, filas_afectadas=1):
        self._cursor = CursorFalso(error_usuario, filas_afectadas)
        self.confirmada = False
        self.revertida = False
        self.cerrada = False

    def cursor(self):
        return self._cursor

    def commit(self):
        self.confirmada = True

    def rollback(self):
        self.revertida = True

    def close(self):
        self.cerrada = True


class PruebasRepositorioUsuarios(unittest.TestCase):
    def setUp(self):
        self.datos = {
            "nombre_cuenta": "Cuenta Prueba",
            "nombre_usuario": "matias",
            "correo": "matias@example.com",
            "telefono": None,
            "nombre": "Matias",
            "apellido": "Prueba",
        }
        fabrica = FabricaConexionesSqlServer(ConfiguracionBaseDatos())
        self.repositorio = RepositorioUsuarios(fabrica)

    def test_confirma_cuenta_y_usuario_como_una_sola_operacion(self):
        conexion = ConexionFalsa()
        with patch("backend.database.conexion.pyodbc.connect", return_value=conexion):
            usuario = self.repositorio.registrar_administrador(
                self.datos,
                "hash-seguro",
            )
        self.assertEqual(usuario["id"], 20)
        self.assertTrue(conexion.confirmada)
        self.assertFalse(conexion.revertida)
        self.assertTrue(conexion.cerrada)
        consultas = conexion._cursor.consultas
        inserciones_grupo = [
            parametros
            for consulta, parametros in consultas
            if "INSERT INTO GrupoCamara" in consulta
        ]
        self.assertEqual(
            inserciones_grupo,
            [(10, "Grupo 1", "Grupo predeterminado")],
        )

    def test_login_solo_busca_usuarios_activos(self):
        conexion = ConexionFalsa()
        with patch("backend.database.conexion.pyodbc.connect", return_value=conexion):
            self.repositorio.buscar_para_login("matias")

        self.assertIn(
            "eu.nombre_estado = 'Activo'",
            conexion._cursor.consulta,
        )

    def test_duplicado_revierte_la_cuenta_y_no_confirma(self):
        error = pyodbc.IntegrityError(
            "23000",
            "Violation of UNIQUE KEY constraint (2627)",
        )
        conexion = ConexionFalsa(error)
        with patch("backend.database.conexion.pyodbc.connect", return_value=conexion):
            with self.assertRaises(RegistroDuplicado):
                self.repositorio.registrar_administrador(
                    self.datos,
                    "hash-seguro",
                )
        self.assertFalse(conexion.confirmada)
        self.assertTrue(conexion.revertida)
        self.assertTrue(conexion.cerrada)

    def test_otro_error_de_integridad_no_se_disfraza_de_duplicado(self):
        error = pyodbc.IntegrityError(
            "23000",
            "The INSERT statement conflicted with a FOREIGN KEY constraint",
        )
        conexion = ConexionFalsa(error)
        with patch("backend.database.conexion.pyodbc.connect", return_value=conexion):
            with self.assertRaises(pyodbc.IntegrityError):
                self.repositorio.registrar_administrador(
                    self.datos,
                    "hash-seguro",
                )
        self.assertTrue(conexion.revertida)
        self.assertFalse(conexion.confirmada)

    def test_estado_solo_se_actualiza_para_subusuario_de_la_cuenta(self):
        conexion = ConexionFalsa()
        with patch("backend.database.conexion.pyodbc.connect", return_value=conexion):
            actualizado = self.repositorio.actualizar_estado_subusuario(
                10,
                20,
                "Inactivo",
            )
        self.assertTrue(actualizado)
        self.assertEqual(conexion._cursor.parametros, (20, 10, "Inactivo"))
        self.assertIn("r.nombre_rol = 'Subusuario'", conexion._cursor.consulta)
        self.assertTrue(conexion.confirmada)

    def test_estado_no_confirma_si_el_subusuario_no_pertenece_a_la_cuenta(self):
        conexion = ConexionFalsa(filas_afectadas=0)
        with patch("backend.database.conexion.pyodbc.connect", return_value=conexion):
            actualizado = self.repositorio.actualizar_estado_subusuario(
                10,
                999,
                "Activo",
            )
        self.assertFalse(actualizado)
        self.assertFalse(conexion.confirmada)

    def test_administracion_reemplaza_solo_permisos_en_una_transaccion(self):
        conexion = ConexionFalsa()
        with patch("backend.database.conexion.pyodbc.connect", return_value=conexion):
            actualizado = self.repositorio.actualizar_permisos_subusuario(
                10,
                20,
                [],
            )
        consultas = "\n".join(consulta for consulta, _ in conexion._cursor.consultas)
        self.assertTrue(actualizado)
        self.assertIn("eu.nombre_estado = 'Activo'", consultas)
        self.assertIn("DELETE FROM Usuario_Permiso", consultas)
        self.assertNotIn("SET u.nombre", consultas)
        self.assertNotIn("password_hash", consultas)
        self.assertTrue(conexion.confirmada)


if __name__ == "__main__":
    unittest.main()
