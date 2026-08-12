import pyodbc

from backend.database.conexion import FabricaConexionesSqlServer
from backend.exceptions import ErrorCamara


class RepositorioCamaras:
    def __init__(
        self,
        conexiones: FabricaConexionesSqlServer,
        secreto_camaras: str,
    ):
        self.conexiones = conexiones
        self.secreto_camaras = secreto_camaras

    def listar(
        self,
        id_cuenta: int,
        id_usuario: int,
        es_administrador: bool,
    ) -> dict:
        restriccion = "" if es_administrador else """
            AND EXISTS (
                SELECT 1
                FROM Usuario_GrupoCamara ugc
                WHERE ugc.id_grupo_camara = gc.id_grupo_camara
                  AND ugc.id_usuario = ?
            )
        """
        parametros = (
            (id_cuenta,)
            if es_administrador
            else (id_cuenta, id_usuario)
        )
        with self.conexiones.conectar() as conexion:
            filas = conexion.cursor().execute(
                f"""
                SELECT
                    gc.id_grupo_camara,
                    gc.nombre_grupo,
                    gc.descripcion,
                    c.id_camara,
                    c.nombre_camara,
                    c.tipo_fuente,
                    c.direccion_ip,
                    c.puerto_onvif,
                    c.usuario_conexion,
                    c.fuente_video,
                    c.indice_dispositivo,
                    c.escena_simulada
                FROM GrupoCamara gc
                LEFT JOIN Camara c
                    ON c.id_grupo_camara = gc.id_grupo_camara
                   AND c.activa = 1
                WHERE gc.id_cuenta = ?
                  AND gc.activo = 1
                  {restriccion}
                ORDER BY gc.nombre_grupo, c.nombre_camara
                """,
                *parametros,
            ).fetchall()

        grupos: dict[int, dict] = {}
        camaras = []
        for fila in filas:
            grupos.setdefault(
                fila.id_grupo_camara,
                {
                    "id": fila.id_grupo_camara,
                    "nombre": fila.nombre_grupo,
                    "descripcion": fila.descripcion,
                },
            )
            if fila.id_camara is None:
                continue
            camaras.append(
                {
                    "id": fila.id_camara,
                    "nombre": fila.nombre_camara,
                    "tipo": fila.tipo_fuente,
                    "grupoCamaraId": fila.id_grupo_camara,
                    "direccionIp": fila.direccion_ip,
                    "puertoOnvif": fila.puerto_onvif,
                    "usuarioConexion": fila.usuario_conexion,
                    "fuenteVideo": fila.fuente_video,
                    "fuente": fila.indice_dispositivo,
                    "escena": fila.escena_simulada,
                    "tienePassword": fila.tipo_fuente == "onvif",
                }
            )
        return {"grupos": list(grupos.values()), "camaras": camaras}

    def guardar_grupos(self, id_cuenta: int, grupos: list[dict]) -> None:
        if not grupos:
            raise ErrorCamara(
                "Debe existir al menos un grupo de camaras"
            )
        with self.conexiones.conectar() as conexion:
            cursor = conexion.cursor()
            existentes = {
                fila.id_grupo_camara
                for fila in cursor.execute(
                    """
                    SELECT id_grupo_camara
                    FROM GrupoCamara WITH (UPDLOCK, HOLDLOCK)
                    WHERE id_cuenta = ? AND activo = 1
                    """,
                    id_cuenta,
                ).fetchall()
            }
            recibidos = {
                grupo["id"]
                for grupo in grupos
                if isinstance(grupo["id"], int)
            }
            if not recibidos.issubset(existentes):
                raise ErrorCamara(
                    "Uno de los grupos no pertenece a esta cuenta"
                )
            try:
                for grupo in grupos:
                    if isinstance(grupo["id"], int):
                        cursor.execute(
                            """
                            UPDATE GrupoCamara
                            SET nombre_grupo = ?, descripcion = ?
                            WHERE id_grupo_camara = ?
                              AND id_cuenta = ?
                              AND activo = 1
                            """,
                            grupo["nombre"],
                            grupo["descripcion"],
                            grupo["id"],
                            id_cuenta,
                        )
                    else:
                        cursor.execute(
                            """
                            INSERT INTO GrupoCamara (
                                id_cuenta, nombre_grupo, descripcion
                            ) VALUES (?, ?, ?)
                            """,
                            id_cuenta,
                            grupo["nombre"],
                            grupo["descripcion"],
                        )
                for id_grupo in existentes - recibidos:
                    cursor.execute(
                        """
                        UPDATE gc
                        SET gc.activo = 0
                        FROM GrupoCamara gc
                        WHERE gc.id_grupo_camara = ?
                          AND gc.id_cuenta = ?
                          AND gc.activo = 1
                          AND NOT EXISTS (
                              SELECT 1
                              FROM Camara c
                              WHERE c.id_grupo_camara = gc.id_grupo_camara
                                AND c.activa = 1
                          )
                        """,
                        id_grupo,
                        id_cuenta,
                    )
                    if cursor.rowcount == 0:
                        raise ErrorCamara(
                            "No se puede desactivar un grupo con camaras activas"
                        )
                cantidad_grupos = cursor.execute(
                    """
                    SELECT COUNT(*)
                    FROM GrupoCamara
                    WHERE id_cuenta = ? AND activo = 1
                    """,
                    id_cuenta,
                ).fetchval()
                if not cantidad_grupos:
                    raise ErrorCamara(
                        "Debe existir al menos un grupo de camaras"
                    )
                conexion.commit()
            except pyodbc.IntegrityError as error:
                raise ErrorCamara(
                    "Ya existe un grupo con ese nombre"
                ) from error

    def crear(self, id_cuenta: int, datos: dict) -> int:
        self._exigir_secreto_si_onvif(datos)
        with self.conexiones.conectar() as conexion:
            cursor = conexion.cursor()
            self._validar_grupo(cursor, id_cuenta, datos["id_grupo"])
            try:
                id_camara = cursor.execute(
                    """
                    INSERT INTO Camara (
                        id_grupo_camara, nombre_camara, tipo_fuente,
                        direccion_ip, puerto_onvif, usuario_conexion,
                        password_conexion_cifrada, fuente_video,
                        indice_dispositivo, escena_simulada
                    )
                    OUTPUT INSERTED.id_camara
                    VALUES (
                        ?, ?, ?, ?, ?, ?,
                        CASE WHEN ? IS NULL THEN NULL
                             ELSE EncryptByPassPhrase(?, ?) END,
                        ?, ?, ?
                    )
                    """,
                    datos["id_grupo"],
                    datos["nombre"],
                    datos["tipo"],
                    datos["direccion_ip"],
                    datos["puerto_onvif"],
                    datos["usuario_conexion"],
                    datos["password"],
                    self.secreto_camaras,
                    datos["password"],
                    datos["fuente_video"],
                    datos["indice_dispositivo"],
                    datos["escena_simulada"],
                ).fetchval()
                conexion.commit()
                return int(id_camara)
            except pyodbc.IntegrityError as error:
                raise ErrorCamara(
                    "Ya existe una camara con ese nombre en el grupo"
                ) from error

    def editar(
        self,
        id_cuenta: int,
        id_camara: int,
        datos: dict,
    ) -> bool:
        self._exigir_secreto_si_onvif(datos)
        with self.conexiones.conectar() as conexion:
            cursor = conexion.cursor()
            self._validar_grupo(cursor, id_cuenta, datos["id_grupo"])
            password = datos["password"]
            try:
                cursor.execute(
                    """
                    UPDATE c
                    SET
                        c.id_grupo_camara = ?,
                        c.nombre_camara = ?,
                        c.tipo_fuente = ?,
                        c.direccion_ip = ?,
                        c.puerto_onvif = ?,
                        c.usuario_conexion = ?,
                        c.password_conexion_cifrada = CASE
                            WHEN ? IS NULL THEN c.password_conexion_cifrada
                            ELSE EncryptByPassPhrase(?, ?)
                        END,
                        c.fuente_video = ?,
                        c.indice_dispositivo = ?,
                        c.escena_simulada = ?
                    FROM Camara c
                    INNER JOIN GrupoCamara gc
                        ON gc.id_grupo_camara = c.id_grupo_camara
                    WHERE c.id_camara = ?
                      AND gc.id_cuenta = ?
                      AND c.activa = 1
                    """,
                    datos["id_grupo"],
                    datos["nombre"],
                    datos["tipo"],
                    datos["direccion_ip"],
                    datos["puerto_onvif"],
                    datos["usuario_conexion"],
                    password,
                    self.secreto_camaras,
                    password,
                    datos["fuente_video"],
                    datos["indice_dispositivo"],
                    datos["escena_simulada"],
                    id_camara,
                    id_cuenta,
                )
                if cursor.rowcount == 0:
                    return False
                conexion.commit()
                return True
            except pyodbc.IntegrityError as error:
                raise ErrorCamara(
                    "Ya existe una camara con ese nombre en el grupo"
                ) from error

    def eliminar(self, id_cuenta: int, id_camara: int) -> bool:
        with self.conexiones.conectar() as conexion:
            cursor = conexion.cursor()
            cursor.execute(
                """
                UPDATE c
                SET c.activa = 0
                FROM Camara c
                INNER JOIN GrupoCamara gc
                    ON gc.id_grupo_camara = c.id_grupo_camara
                WHERE c.id_camara = ?
                  AND gc.id_cuenta = ?
                  AND c.activa = 1
                """,
                id_camara,
                id_cuenta,
            )
            if cursor.rowcount == 0:
                return False
            conexion.commit()
            return True

    @staticmethod
    def _validar_grupo(cursor, id_cuenta: int, id_grupo: int) -> None:
        existe = cursor.execute(
            """
            SELECT COUNT(*)
            FROM GrupoCamara
            WHERE id_grupo_camara = ?
              AND id_cuenta = ?
              AND activo = 1
            """,
            id_grupo,
            id_cuenta,
        ).fetchval()
        if not existe:
            raise ErrorCamara(
                "El grupo no existe o no pertenece a esta cuenta"
            )

    def _exigir_secreto_si_onvif(self, datos: dict) -> None:
        if datos["tipo"] == "onvif" and not self.secreto_camaras:
            raise ErrorCamara(
                "Configura WITCAM_CAMERA_SECRET antes de guardar camaras ONVIF"
            )
