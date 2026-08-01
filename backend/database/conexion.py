from contextlib import contextmanager

import pyodbc

from backend.config import ConfiguracionBaseDatos


class FabricaConexionesSqlServer:
    def __init__(self, config: ConfiguracionBaseDatos):
        self.config = config

    @contextmanager
    def conectar(self):
        conexion = pyodbc.connect(
            self.config.cadena_conexion(),
            timeout=5,
            autocommit=False,
        )
        try:
            yield conexion
        except Exception:
            conexion.rollback()
            raise
        finally:
            conexion.close()
