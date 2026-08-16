from dataclasses import dataclass

from backend.database.conexion import FabricaConexionesSqlServer


@dataclass(frozen=True)
class ResultadoEliminacionPersona:
    id_persona: int
    nombre: str
    rutas_archivos: tuple[str, ...]


class RepositorioIngresos:
    def __init__(self, conexiones: FabricaConexionesSqlServer):
        self.conexiones = conexiones

    def listar(
        self,
        id_cuenta: int,
        pagina: int,
        limite: int,
        filtros: dict | None = None,
    ) -> dict:
        filtros = filtros or {}
        condiciones = [
            "p.id_cuenta = ?",
            "gc.id_cuenta = ?",
            "d.id_persona IS NOT NULL",
        ]
        parametros = [id_cuenta, id_cuenta]
        if filtros.get("fecha_desde") is not None:
            condiciones.append("d.fecha_hora >= ?")
            parametros.append(filtros["fecha_desde"])
        if filtros.get("fecha_hasta") is not None:
            condiciones.append("d.fecha_hora <= ?")
            parametros.append(filtros["fecha_hasta"])
        if filtros.get("id_camara") is not None:
            condiciones.append("d.id_camara = ?")
            parametros.append(filtros["id_camara"])
        clausula_condiciones = "\n                    AND ".join(condiciones)
        desplazamiento = (pagina - 1) * limite

        with self.conexiones.conectar() as conexion:
            cursor = conexion.cursor()
            total = cursor.execute(
                f"""
                SELECT COUNT(DISTINCT d.id_persona)
                FROM Deteccion d
                INNER JOIN Persona p
                    ON p.id_persona = d.id_persona
                INNER JOIN Camara c
                    ON c.id_camara = d.id_camara
                INNER JOIN GrupoCamara gc
                    ON gc.id_grupo_camara = c.id_grupo_camara
                WHERE {clausula_condiciones}
                """,
                *parametros,
            ).fetchval()
            filas = cursor.execute(
                f"""
                WITH detecciones_filtradas AS (
                    SELECT
                        d.id_deteccion,
                        d.id_persona,
                        p.nombre_persona,
                        d.id_camara,
                        c.nombre_camara,
                        d.fecha_hora,
                        d.ruta_imagen_detectada,
                        d.resultado,
                        d.similitud,
                        CASE WHEN EXISTS (
                            SELECT 1
                            FROM ListaObservacion lo
                            WHERE lo.id_persona = d.id_persona
                              AND lo.activa = 1
                        ) THEN 1 ELSE 0 END AS en_lista_observacion,
                        ROW_NUMBER() OVER (
                            PARTITION BY d.id_persona
                            ORDER BY d.fecha_hora DESC, d.id_deteccion DESC
                        ) AS posicion
                    FROM Deteccion d
                    INNER JOIN Persona p
                        ON p.id_persona = d.id_persona
                    INNER JOIN Camara c
                        ON c.id_camara = d.id_camara
                    INNER JOIN GrupoCamara gc
                        ON gc.id_grupo_camara = c.id_grupo_camara
                    WHERE {clausula_condiciones}
                )
                SELECT
                    id_deteccion,
                    id_persona,
                    nombre_persona,
                    id_camara,
                    nombre_camara,
                    fecha_hora,
                    ruta_imagen_detectada,
                    resultado,
                    similitud,
                    en_lista_observacion
                FROM detecciones_filtradas
                WHERE posicion = 1
                ORDER BY fecha_hora DESC, id_deteccion DESC
                OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
                """,
                *parametros,
                desplazamiento,
                limite,
            ).fetchall()

        return {
            "total": int(total or 0),
            "pagina": pagina,
            "limite": limite,
            "ingresos": [self._serializar(fila) for fila in filas],
        }

    def listar_historial(self, id_cuenta: int, id_persona: int) -> dict | None:
        with self.conexiones.conectar() as conexion:
            cursor = conexion.cursor()
            persona = cursor.execute(
                """
                SELECT id_persona, nombre_persona
                FROM Persona
                WHERE id_persona = ? AND id_cuenta = ?
                """,
                id_persona,
                id_cuenta,
            ).fetchone()
            if persona is None:
                return None
            filas = cursor.execute(
                """
                SELECT
                    d.id_deteccion,
                    d.id_persona,
                    p.nombre_persona,
                    d.id_camara,
                    c.nombre_camara,
                    d.fecha_hora,
                    d.ruta_imagen_detectada,
                    d.resultado,
                    d.similitud
                FROM Deteccion d
                INNER JOIN Persona p ON p.id_persona = d.id_persona
                INNER JOIN Camara c ON c.id_camara = d.id_camara
                INNER JOIN GrupoCamara gc
                    ON gc.id_grupo_camara = c.id_grupo_camara
                WHERE d.id_persona = ?
                  AND p.id_cuenta = ?
                  AND gc.id_cuenta = ?
                ORDER BY d.fecha_hora DESC, d.id_deteccion DESC
                """,
                id_persona,
                id_cuenta,
                id_cuenta,
            ).fetchall()
        return {
            "persona": {
                "id": persona.id_persona,
                "nombre": persona.nombre_persona,
            },
            "detecciones": [self._serializar(fila) for fila in filas],
        }

    @staticmethod
    def _serializar(fila) -> dict:
        return {
            "idDeteccion": fila.id_deteccion,
            "idPersona": fila.id_persona,
            "nombrePersona": fila.nombre_persona,
            "idCamara": fila.id_camara,
            "nombreCamara": fila.nombre_camara,
            "fechaHora": fila.fecha_hora.isoformat(timespec="seconds"),
            "rutaImagen": fila.ruta_imagen_detectada,
            "resultado": fila.resultado,
            "similitud": (
                float(fila.similitud)
                if fila.similitud is not None
                else None
            ),
            "enListaObservacion": bool(
                getattr(fila, "en_lista_observacion", False)
            ),
        }

    def agregar_lista_observacion(
        self,
        id_cuenta: int,
        id_usuario: int,
        id_persona: int,
        motivo: str,
    ) -> bool:
        with self.conexiones.conectar() as conexion:
            cursor = conexion.cursor()
            persona = cursor.execute(
                """
                SELECT id_persona
                FROM Persona
                WHERE id_persona = ? AND id_cuenta = ?
                """,
                id_persona,
                id_cuenta,
            ).fetchone()
            if persona is None:
                return False
            existente = cursor.execute(
                """
                SELECT id_lista_observacion
                FROM ListaObservacion WITH (UPDLOCK, HOLDLOCK)
                WHERE id_persona = ?
                """,
                id_persona,
            ).fetchone()
            if existente is None:
                cursor.execute(
                    """
                    INSERT INTO ListaObservacion (
                        id_persona, id_usuario_registro, motivo
                    ) VALUES (?, ?, ?)
                    """,
                    id_persona,
                    id_usuario,
                    motivo,
                )
            else:
                cursor.execute(
                    """
                    UPDATE ListaObservacion
                    SET activa = 1,
                        motivo = ?,
                        id_usuario_registro = ?,
                        fecha_ingreso_lista = GETDATE()
                    WHERE id_persona = ? AND activa = 0
                    """,
                    motivo,
                    id_usuario,
                    id_persona,
                )
            conexion.commit()
            return True

    def listar_observacion(self, id_cuenta: int) -> list[dict]:
        with self.conexiones.conectar() as conexion:
            filas = conexion.cursor().execute(
                """
                SELECT
                    lo.id_lista_observacion,
                    p.id_persona,
                    p.nombre_persona,
                    lo.motivo,
                    lo.fecha_ingreso_lista,
                    u.nombre,
                    u.apellido
                FROM ListaObservacion lo
                INNER JOIN Persona p ON p.id_persona = lo.id_persona
                INNER JOIN Usuario u
                    ON u.id_usuario = lo.id_usuario_registro
                WHERE p.id_cuenta = ?
                  AND u.id_cuenta = ?
                  AND lo.activa = 1
                ORDER BY lo.fecha_ingreso_lista DESC,
                         lo.id_lista_observacion DESC
                """,
                id_cuenta,
                id_cuenta,
            ).fetchall()
        return [
            {
                "idLista": fila.id_lista_observacion,
                "idCliente": fila.id_persona,
                "nombrePersona": fila.nombre_persona,
                "motivo": fila.motivo,
                "fechaIngreso": fila.fecha_ingreso_lista.isoformat(
                    timespec="seconds"
                ),
                "registradoPor": f"{fila.nombre} {fila.apellido}".strip(),
                "imagen": None,
            }
            for fila in filas
        ]

    def listar_camaras(self, id_cuenta: int) -> list[dict]:
        with self.conexiones.conectar() as conexion:
            filas = conexion.cursor().execute(
                """
                SELECT
                    c.id_camara,
                    c.nombre_camara
                FROM Camara c
                INNER JOIN GrupoCamara gc
                    ON gc.id_grupo_camara = c.id_grupo_camara
                WHERE gc.id_cuenta = ?
                  AND c.activa = 1
                  AND gc.activo = 1
                ORDER BY c.nombre_camara, c.id_camara
                """,
                id_cuenta,
            ).fetchall()
        return [
            {
                "id": fila.id_camara,
                "nombre": fila.nombre_camara,
            }
            for fila in filas
        ]

    def eliminar_persona(
        self,
        id_cuenta: int,
        id_persona: int,
    ) -> ResultadoEliminacionPersona | None:
        """Elimina la identidad y conserva sus detecciones anonimizadas."""
        with self.conexiones.conectar() as conexion:
            cursor = conexion.cursor()
            persona = cursor.execute(
                """
                SELECT id_persona, nombre_persona
                FROM Persona WITH (UPDLOCK, HOLDLOCK)
                WHERE id_persona = ? AND id_cuenta = ?
                """,
                id_persona,
                id_cuenta,
            ).fetchone()
            if persona is None:
                return None
            observacion_activa = cursor.execute(
                """
                SELECT TOP 1 id_lista_observacion
                FROM ListaObservacion WITH (UPDLOCK, HOLDLOCK)
                WHERE id_persona = ? AND activa = 1
                """,
                id_persona,
            ).fetchone()
            if observacion_activa is not None:
                raise ValueError(
                    "La persona esta en la lista de observacion y no puede eliminarse"
                )

            detecciones = cursor.execute(
                """
                SELECT ruta_imagen_detectada AS ruta_archivo
                FROM Deteccion
                WHERE id_persona = ?
                  AND ruta_imagen_detectada IS NOT NULL
                """,
                id_persona,
            ).fetchall()
            muestras = cursor.execute(
                """
                SELECT ruta_archivo
                FROM MuestraFacial
                WHERE id_persona = ?
                """,
                id_persona,
            ).fetchall()
            rutas = tuple(
                dict.fromkeys(
                    str(fila.ruta_archivo)
                    for fila in (*detecciones, *muestras)
                    if getattr(fila, "ruta_archivo", None)
                )
            )

            cursor.execute(
                """
                DELETE a
                FROM Alerta a
                INNER JOIN Deteccion d
                    ON d.id_deteccion = a.id_deteccion
                WHERE d.id_persona = ?
                """,
                id_persona,
            )
            cursor.execute(
                """
                DELETE a
                FROM Alerta a
                INNER JOIN ListaObservacion lo
                    ON lo.id_lista_observacion = a.id_lista_observacion
                WHERE lo.id_persona = ?
                """,
                id_persona,
            )
            cursor.execute(
                "DELETE FROM ListaObservacion WHERE id_persona = ?",
                id_persona,
            )
            cursor.execute(
                "DELETE FROM MuestraFacial WHERE id_persona = ?",
                id_persona,
            )
            cursor.execute(
                """
                UPDATE Deteccion
                SET id_persona = NULL,
                    ruta_imagen_detectada = NULL,
                    resultado = 'Anonimizado',
                    similitud = NULL
                WHERE id_persona = ?
                """,
                id_persona,
            )
            cursor.execute(
                "DELETE FROM Persona WHERE id_persona = ? AND id_cuenta = ?",
                id_persona,
                id_cuenta,
            )
            conexion.commit()
            return ResultadoEliminacionPersona(
                id_persona=id_persona,
                nombre=str(persona.nombre_persona),
                rutas_archivos=rutas,
            )
