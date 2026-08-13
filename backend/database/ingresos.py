from backend.database.conexion import FabricaConexionesSqlServer


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
                    similitud
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
        }

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
