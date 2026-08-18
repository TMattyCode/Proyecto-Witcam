import pyodbc
from datetime import datetime

from backend.database.conexion import FabricaConexionesSqlServer
from backend.exceptions import RegistroDuplicado


def _es_error_duplicado(error: pyodbc.IntegrityError) -> bool:
    detalle = " ".join(str(argumento) for argumento in error.args)
    return "2601" in detalle or "2627" in detalle


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
                cursor.execute(
                    """
                    INSERT INTO GrupoCamara (
                        id_cuenta,
                        nombre_grupo,
                        descripcion
                    )
                    VALUES (?, ?, ?)
                    """,
                    id_cuenta,
                    "Grupo 1",
                    "Grupo predeterminado",
                )
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
            if not _es_error_duplicado(error):
                raise
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
                  AND eu.nombre_estado = 'Activo'
                """,
                nombre_usuario,
            ).fetchone()

    def obtener_resumen_cuenta(self, id_cuenta: int) -> dict | None:
        with self.conexiones.conectar() as conexion:
            fila = conexion.cursor().execute(
                """
                SELECT
                    c.nombre_cuenta,
                    SUM(
                        CASE
                            WHEN r.nombre_rol = 'Subusuario'
                                AND eu.nombre_estado = 'Activo'
                            THEN 1
                            ELSE 0
                        END
                    ) AS subusuarios_activos
                FROM Cuenta c
                LEFT JOIN Usuario u ON u.id_cuenta = c.id_cuenta
                LEFT JOIN Rol r ON r.id_rol = u.id_rol
                LEFT JOIN EstadoUsuario eu
                    ON eu.id_estado_usuario = u.id_estado_usuario
                WHERE c.id_cuenta = ?
                GROUP BY c.nombre_cuenta
                """,
                id_cuenta,
            ).fetchone()
        if fila is None:
            return None
        return {
            "nombreCuenta": fila.nombre_cuenta,
            "subusuariosActivos": int(fila.subusuarios_activos or 0),
        }

    def listar_subusuarios(self, id_cuenta: int, filtros: dict) -> dict:
        with self.conexiones.conectar() as conexion:
            cursor = conexion.cursor()
            permisos = [
                {
                    "id": fila.id_permiso,
                    "codigo": fila.codigo_permiso,
                    "nombre": fila.nombre_permiso,
                    "descripcion": fila.descripcion,
                }
                for fila in cursor.execute(
                    """
                    SELECT id_permiso, codigo_permiso, nombre_permiso, descripcion
                    FROM Permiso
                    ORDER BY id_permiso
                    """
                ).fetchall()
            ]
            condiciones = [
                "u.id_cuenta = ?",
                "r.nombre_rol = 'Subusuario'",
                "eu.nombre_estado = ?",
            ]
            parametros = [id_cuenta, filtros["estado"]]
            if filtros["usuario"]:
                condiciones.append("u.nombre_usuario LIKE ?")
                parametros.append(f"%{filtros['usuario']}%")
            if filtros["permiso"]:
                condiciones.append(
                    """
                    EXISTS (
                        SELECT 1
                        FROM Usuario_Permiso upf
                        INNER JOIN Permiso pf
                            ON pf.id_permiso = upf.id_permiso
                        WHERE upf.id_usuario = u.id_usuario
                            AND upf.permitido = 1
                            AND pf.codigo_permiso = ?
                    )
                    """
                )
                parametros.append(filtros["permiso"])
            if filtros["registro_desde"]:
                condiciones.append("u.fecha_creacion >= CAST(? AS DATE)")
                parametros.append(filtros["registro_desde"])
            if filtros["registro_hasta"]:
                condiciones.append(
                    "u.fecha_creacion < DATEADD(DAY, 1, CAST(? AS DATE))"
                )
                parametros.append(filtros["registro_hasta"])
            if filtros["sin_acceso"]:
                condiciones.append("u.ultimo_acceso IS NULL")
            else:
                if filtros["acceso_desde"]:
                    condiciones.append("u.ultimo_acceso >= CAST(? AS DATE)")
                    parametros.append(filtros["acceso_desde"])
                if filtros["acceso_hasta"]:
                    condiciones.append(
                        "u.ultimo_acceso < DATEADD(DAY, 1, CAST(? AS DATE))"
                    )
                    parametros.append(filtros["acceso_hasta"])

            clausula_where = " AND ".join(condiciones)
            total = cursor.execute(
                f"""
                SELECT COUNT(*)
                FROM Usuario u
                INNER JOIN Rol r ON r.id_rol = u.id_rol
                INNER JOIN EstadoUsuario eu
                    ON eu.id_estado_usuario = u.id_estado_usuario
                WHERE {clausula_where}
                """,
                *parametros,
            ).fetchval()
            desplazamiento = (filtros["pagina"] - 1) * filtros["limite"]
            filas_usuarios = cursor.execute(
                f"""
                SELECT
                    u.id_usuario,
                    u.nombre,
                    u.apellido,
                    u.nombre_usuario,
                    u.correo,
                    u.telefono,
                    u.fecha_creacion,
                    u.fecha_eliminacion,
                    u.ultimo_acceso,
                    eu.nombre_estado
                FROM Usuario u
                INNER JOIN Rol r ON r.id_rol = u.id_rol
                INNER JOIN EstadoUsuario eu
                    ON eu.id_estado_usuario = u.id_estado_usuario
                WHERE {clausula_where}
                ORDER BY u.fecha_creacion DESC, u.id_usuario DESC
                OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
                """,
                *parametros,
                desplazamiento,
                filtros["limite"],
            ).fetchall()
            ids = [fila.id_usuario for fila in filas_usuarios]
            permisos_por_usuario = {id_usuario: [] for id_usuario in ids}
            if ids:
                marcadores = ", ".join("?" for _ in ids)
                filas_asignaciones = cursor.execute(
                    f"""
                    SELECT up.id_usuario, p.codigo_permiso
                    FROM Usuario_Permiso up
                    INNER JOIN Permiso p ON p.id_permiso = up.id_permiso
                    WHERE up.permitido = 1
                        AND up.id_usuario IN ({marcadores})
                    """,
                    *ids,
                ).fetchall()
                for fila in filas_asignaciones:
                    permisos_por_usuario[fila.id_usuario].append(
                        fila.codigo_permiso
                    )
        return {
            "total": int(total or 0),
            "pagina": filtros["pagina"],
            "limite": filtros["limite"],
            "permisos": permisos,
            "subusuarios": [
                {
                    "id": fila.id_usuario,
                    "nombre": fila.nombre,
                    "apellido": fila.apellido,
                    "nombreUsuario": fila.nombre_usuario,
                    "correo": fila.correo,
                    "telefono": fila.telefono,
                    "estado": fila.nombre_estado,
                    "fechaCreacion": fila.fecha_creacion.isoformat(
                        timespec="seconds"
                    ),
                    "ultimoAcceso": (
                        fila.ultimo_acceso.isoformat(timespec="seconds")
                        if fila.ultimo_acceso
                        else None
                    ),
                    "fechaEliminacion": (
                        fila.fecha_eliminacion.isoformat(timespec="seconds")
                        if fila.fecha_eliminacion
                        else None
                    ),
                    "permisos": permisos_por_usuario[fila.id_usuario],
                }
                for fila in filas_usuarios
            ],
        }

    def registrar_subusuario(
        self,
        id_cuenta: int,
        datos: dict,
        password_hash: str,
        codigos_permisos: list[str],
    ) -> dict:
        try:
            with self.conexiones.conectar() as conexion:
                cursor = conexion.cursor()
                rol = cursor.execute(
                    "SELECT id_rol FROM Rol WHERE nombre_rol = ?",
                    "Subusuario",
                ).fetchone()
                if rol is None:
                    raise RuntimeError(
                        "La base de datos no contiene el rol Subusuario"
                    )

                permisos = []
                if codigos_permisos:
                    marcadores = ", ".join("?" for _ in codigos_permisos)
                    permisos = cursor.execute(
                        f"""
                        SELECT id_permiso, codigo_permiso
                        FROM Permiso
                        WHERE codigo_permiso IN ({marcadores})
                        """,
                        *codigos_permisos,
                    ).fetchall()
                    encontrados = {fila.codigo_permiso for fila in permisos}
                    if encontrados != set(codigos_permisos):
                        raise ValueError("Uno o mas permisos no existen")

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

                for permiso in permisos:
                    cursor.execute(
                        """
                        INSERT INTO Usuario_Permiso (
                            id_usuario,
                            id_permiso,
                            permitido
                        )
                        VALUES (?, ?, 1)
                        """,
                        id_usuario,
                        permiso.id_permiso,
                    )
                conexion.commit()
        except pyodbc.IntegrityError as error:
            if not _es_error_duplicado(error):
                raise
            raise RegistroDuplicado(
                "El nombre de usuario o correo ya esta registrado"
            ) from error

        return {
            "id": id_usuario,
            "nombre": datos["nombre"],
            "apellido": datos["apellido"],
            "nombreUsuario": datos["nombre_usuario"],
            "correo": datos["correo"],
            "telefono": datos["telefono"],
            "estado": "Activo",
            "fechaCreacion": datetime.now().isoformat(timespec="seconds"),
            "ultimoAcceso": None,
            "permisos": codigos_permisos,
        }

    def actualizar_estado_subusuario(
        self,
        id_cuenta: int,
        id_usuario: int,
        estado: str,
    ) -> bool:
        with self.conexiones.conectar() as conexion:
            cursor = conexion.cursor()
            cursor.execute(
                """
                UPDATE u
                SET u.id_estado_usuario = eu.id_estado_usuario,
                    u.fecha_eliminacion = CASE
                        WHEN eu.nombre_estado = 'Inactivo' THEN GETDATE()
                        ELSE NULL
                    END
                FROM Usuario u
                INNER JOIN Rol r ON r.id_rol = u.id_rol
                CROSS JOIN EstadoUsuario eu
                WHERE u.id_usuario = ?
                    AND u.id_cuenta = ?
                    AND r.nombre_rol = 'Subusuario'
                    AND eu.nombre_estado = ?
                """,
                id_usuario,
                id_cuenta,
                estado,
            )
            actualizado = cursor.rowcount > 0
            if actualizado:
                conexion.commit()
            return actualizado

    def actualizar_permisos_subusuario(
        self,
        id_cuenta: int,
        id_usuario: int,
        codigos_permisos: list[str],
    ) -> bool:
        with self.conexiones.conectar() as conexion:
            cursor = conexion.cursor()
            permisos = []
            if codigos_permisos:
                marcadores = ", ".join("?" for _ in codigos_permisos)
                permisos = cursor.execute(
                    f"""
                    SELECT id_permiso, codigo_permiso
                    FROM Permiso
                    WHERE codigo_permiso IN ({marcadores})
                    """,
                    *codigos_permisos,
                ).fetchall()
                encontrados = {fila.codigo_permiso for fila in permisos}
                if encontrados != set(codigos_permisos):
                    raise ValueError("Uno o mas permisos no existen")

            usuario = cursor.execute(
                """
                SELECT u.id_usuario
                FROM Usuario u WITH (UPDLOCK, HOLDLOCK)
                INNER JOIN Rol r ON r.id_rol = u.id_rol
                INNER JOIN EstadoUsuario eu
                    ON eu.id_estado_usuario = u.id_estado_usuario
                WHERE u.id_usuario = ?
                    AND u.id_cuenta = ?
                    AND r.nombre_rol = 'Subusuario'
                    AND eu.nombre_estado = 'Activo'
                """,
                id_usuario,
                id_cuenta,
            ).fetchone()
            if usuario is None:
                return False

            cursor.execute(
                "DELETE FROM Usuario_Permiso WHERE id_usuario = ?",
                id_usuario,
            )
            for permiso in permisos:
                cursor.execute(
                    """
                    INSERT INTO Usuario_Permiso (
                        id_usuario,
                        id_permiso,
                        permitido
                    )
                    VALUES (?, ?, 1)
                    """,
                    id_usuario,
                    permiso.id_permiso,
                )
            conexion.commit()
            return True

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

    def tiene_permiso(self, id_usuario: int, codigo_permiso: str) -> bool:
        with self.conexiones.conectar() as conexion:
            valor = conexion.cursor().execute(
                """
                SELECT CASE
                    WHEN r.nombre_rol = 'Administrador' THEN 1
                    WHEN EXISTS (
                        SELECT 1
                        FROM Usuario_Permiso up
                        INNER JOIN Permiso p
                            ON p.id_permiso = up.id_permiso
                        WHERE up.id_usuario = u.id_usuario
                          AND up.permitido = 1
                          AND p.codigo_permiso = ?
                    ) THEN 1
                    ELSE 0
                END
                FROM Usuario u
                INNER JOIN Rol r ON r.id_rol = u.id_rol
                INNER JOIN EstadoUsuario eu
                    ON eu.id_estado_usuario = u.id_estado_usuario
                WHERE u.id_usuario = ?
                  AND eu.nombre_estado = 'Activo'
                """,
                codigo_permiso,
                id_usuario,
            ).fetchval()
        return bool(valor)

<<<<<<< HEAD
    def obtener_permisos(self, id_usuario: int) -> list[str]:
=======
    def obtener_permisos_usuario(self, id_usuario: int) -> list[str]:
>>>>>>> 10d0c3dcda1141aa5c15e11ed78790cc56564e68
        with self.conexiones.conectar() as conexion:
            filas = conexion.cursor().execute(
                """
                SELECT p.codigo_permiso
<<<<<<< HEAD
                FROM Usuario u
                INNER JOIN Rol r ON r.id_rol = u.id_rol
                INNER JOIN EstadoUsuario eu
                    ON eu.id_estado_usuario = u.id_estado_usuario
                CROSS JOIN Permiso p
                WHERE u.id_usuario = ?
                  AND eu.nombre_estado = 'Activo'
                  AND (
                      r.nombre_rol = 'Administrador'
                      OR EXISTS (
                          SELECT 1
                          FROM Usuario_Permiso up
                          WHERE up.id_usuario = u.id_usuario
                            AND up.id_permiso = p.id_permiso
                            AND up.permitido = 1
                      )
                  )
=======
                FROM Usuario_Permiso up
                INNER JOIN Permiso p ON p.id_permiso = up.id_permiso
                WHERE up.id_usuario = ? AND up.permitido = 1
>>>>>>> 10d0c3dcda1141aa5c15e11ed78790cc56564e68
                ORDER BY p.id_permiso
                """,
                id_usuario,
            ).fetchall()
        return [fila.codigo_permiso for fila in filas]
