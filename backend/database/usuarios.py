import pyodbc

from backend.database.conexion import FabricaConexionesSqlServer
from backend.exceptions import RegistroDuplicado


class RepositorioUsuarios:
    def __init__(self, conexiones: FabricaConexionesSqlServer):
        self.conexiones = conexiones

    def registrar_administrador(self, datos: dict, password_hash: str) -> dict:
        try:
            with self.conexiones.conectar() as conexion:
                cursor = conexion.cursor()
                rol = cursor.execute(
                    "SELECT id_rol FROM Rol WHERE nombre_rol = ?",
                    "Administrador",
                ).fetchone()
                if rol is None:
                    raise RuntimeError(
                        "La base de datos no contiene el rol Administrador"
                    )
                id_cuenta = cursor.execute(
                    """
                    INSERT INTO Cuenta (nombre_cuenta)
                    OUTPUT INSERTED.id_cuenta
                    VALUES (?)
                    """,
                    datos["nombre_cuenta"],
                ).fetchval()
                id_usuario = cursor.execute(
                    """
                    INSERT INTO Usuario (
                        id_cuenta,
                        id_rol,
                        nombre,
                        apellido,
                        nombre_usuario,
                        correo,
                        telefono,
                        password_hash
                    )
                    OUTPUT INSERTED.id_usuario
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    id_cuenta,
                    rol.id_rol,
                    datos["nombre"],
                    datos["apellido"],
                    datos["nombre_usuario"],
                    datos["correo"],
                    datos["telefono"],
                    password_hash,
                ).fetchval()
                conexion.commit()
                return {
                    "id": id_usuario,
                    "idCuenta": id_cuenta,
                    "nombreCuenta": datos["nombre_cuenta"],
                    "nombreUsuario": datos["nombre_usuario"],
                    "nombre": datos["nombre"],
                    "apellido": datos["apellido"],
                    "correo": datos["correo"],
                    "rol": "Administrador",
                }
        except pyodbc.IntegrityError as error:
            raise RegistroDuplicado(
                "El nombre de usuario o correo ya esta registrado"
            ) from error

    def buscar_para_login(self, nombre_usuario: str):
        with self.conexiones.conectar() as conexion:
            return conexion.cursor().execute(
                """
                SELECT
                    u.id_usuario,
                    u.id_cuenta,
                    u.nombre,
                    u.apellido,
                    u.nombre_usuario,
                    u.correo,
                    u.password_hash,
                    r.nombre_rol,
                    c.nombre_cuenta,
                    eu.nombre_estado
                FROM Usuario u
                INNER JOIN Rol r ON r.id_rol = u.id_rol
                INNER JOIN Cuenta c ON c.id_cuenta = u.id_cuenta
                INNER JOIN EstadoUsuario eu
                    ON eu.id_estado_usuario = u.id_estado_usuario
                WHERE u.nombre_usuario = ?
                """,
                nombre_usuario,
            ).fetchone()

    def registrar_acceso(self, id_usuario: int) -> None:
        with self.conexiones.conectar() as conexion:
            conexion.cursor().execute(
                """
                UPDATE Usuario
                SET ultimo_acceso = GETDATE()
                WHERE id_usuario = ?
                """,
                id_usuario,
            )
            conexion.commit()
