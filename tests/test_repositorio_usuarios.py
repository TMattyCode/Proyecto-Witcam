import unittest
from types import SimpleNamespace
from unittest.mock import patch

import pyodbc

from backend.config import ConfiguracionBaseDatos
from backend.database.conexion import FabricaConexionesSqlServer
from backend.database.usuarios import RepositorioUsuarios
from backend.exceptions import RegistroDuplicado


class CursorFalso:
    def __init__(self, error_usuario=None):
        self.error_usuario = error_usuario
        self.consulta = ""

    def execute(self, consulta, *parametros):
        self.consulta = consulta
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
    def __init__(self, error_usuario=None):
        self._cursor = CursorFalso(error_usuario)
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


if __name__ == "__main__":
    unittest.main()
