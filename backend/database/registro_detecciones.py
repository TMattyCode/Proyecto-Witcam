from dataclasses import dataclass
from datetime import timedelta

from backend.database.conexion import FabricaConexionesSqlServer
from backend.dominio.modelos import EventoIdentidadEstable


@dataclass(frozen=True)
class ResultadoRegistroDeteccion:
    id_cuenta: int
    id_persona: int
    insertada: bool


class RepositorioRegistroDetecciones:
    def __init__(self, conexiones: FabricaConexionesSqlServer):
        self.conexiones = conexiones

    def registrar(
        self,
        evento: EventoIdentidadEstable,
        personas_por_cuenta: dict[str, int],
        ruta_imagen: str | None,
        cooldown_segundos: int,
    ) -> ResultadoRegistroDeteccion:
        with self.conexiones.conectar() as conexion:
            cursor = conexion.cursor()
            camara = cursor.execute(
                """
                SELECT gc.id_cuenta, c.id_grupo_camara
                FROM Camara c
                INNER JOIN GrupoCamara gc
                    ON gc.id_grupo_camara = c.id_grupo_camara
                WHERE c.id_camara = ?
                  AND c.activa = 1
                  AND gc.activo = 1
                """,
                evento.id_camara,
            ).fetchone()
            if camara is None:
                raise ValueError("La camara no esta activa o no existe")

            id_cuenta = int(camara.id_cuenta)
            if id_cuenta != evento.id_cuenta:
                raise ValueError("La camara no pertenece a la cuenta indicada")
            id_persona = personas_por_cuenta.get(str(id_cuenta))
            persona = None
            if id_persona is not None:
                persona = cursor.execute(
                    """
                    SELECT id_persona
                    FROM Persona WITH (UPDLOCK, HOLDLOCK)
                    WHERE id_persona = ? AND id_cuenta = ?
                    """,
                    id_persona,
                    id_cuenta,
                ).fetchone()
            if persona is None:
                id_persona = int(
                    cursor.execute(
                        """
                        INSERT INTO Persona (id_cuenta, nombre_persona)
                        OUTPUT INSERTED.id_persona
                        VALUES (?, ?)
                        """,
                        id_cuenta,
                        evento.nombre,
                    ).fetchval()
                )
            else:
                cursor.execute(
                    """
                    UPDATE Persona
                    SET nombre_persona = ?
                    WHERE id_persona = ? AND id_cuenta = ?
                    """,
                    evento.nombre,
                    id_persona,
                    id_cuenta,
                )

            limite = evento.fecha_hora - timedelta(
                seconds=cooldown_segundos
            )
            reciente = cursor.execute(
                """
                SELECT TOP 1 d.id_deteccion
                FROM Deteccion d
                INNER JOIN Camara c
                    ON c.id_camara = d.id_camara
                WHERE d.id_persona = ?
                  AND c.id_grupo_camara = ?
                  AND d.fecha_hora >= ?
                ORDER BY d.fecha_hora DESC, d.id_deteccion DESC
                """,
                id_persona,
                camara.id_grupo_camara,
                limite,
            ).fetchone()

            lista = cursor.execute(
                """
                SELECT id_lista_observacion, fecha_ingreso_lista
                FROM ListaObservacion
                WHERE id_persona = ? AND activa = 1
                """,
                id_persona,
            ).fetchone()
            alerta_reciente = None
            if lista is not None:
                alerta_reciente = cursor.execute(
                    """
                    SELECT TOP 1 a.id_alerta
                    FROM Alerta a WITH (UPDLOCK, HOLDLOCK)
                    INNER JOIN Deteccion anterior
                        ON anterior.id_deteccion = a.id_deteccion
                    WHERE anterior.id_persona = ?
                      AND a.fecha_hora >= ?
                      AND a.fecha_hora >= ?
                    ORDER BY a.fecha_hora DESC, a.id_alerta DESC
                    """,
                    id_persona,
                    limite,
                    lista.fecha_ingreso_lista,
                ).fetchone()

            debe_alertar = lista is not None and alerta_reciente is None
            debe_insertar = reciente is None or debe_alertar
            if debe_insertar:
                id_deteccion = cursor.execute(
                    """
                    INSERT INTO Deteccion (
                        id_camara, id_persona, fecha_hora,
                        ruta_imagen_detectada, resultado, similitud
                    )
                    OUTPUT INSERTED.id_deteccion
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    evento.id_camara,
                    id_persona,
                    evento.fecha_hora,
                    ruta_imagen,
                    "Identificado",
                    max(0.0, min(1.0, evento.similitud)),
                ).fetchval()
                if debe_alertar:
                    cursor.execute(
                        """
                        INSERT INTO Alerta (
                            id_deteccion, id_lista_observacion,
                            fecha_hora, atendida
                        ) VALUES (?, ?, ?, 0)
                        """,
                        id_deteccion,
                        lista.id_lista_observacion,
                        evento.fecha_hora,
                    )
            conexion.commit()
            return ResultadoRegistroDeteccion(
                id_cuenta=id_cuenta,
                id_persona=id_persona,
                insertada=debe_insertar,
            )
