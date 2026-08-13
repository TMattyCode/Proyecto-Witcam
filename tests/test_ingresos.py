import unittest
from contextlib import contextmanager
from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace

from backend.aplicacion.ingresos import ServicioIngresos
from backend.database.ingresos import RepositorioIngresos


class CursorIngresosFalso:
    def __init__(self):
        self.consulta = ""
        self.parametros = ()
        self.consultas = []

    def execute(self, consulta, *parametros):
        self.consulta = consulta
        self.parametros = parametros
        self.consultas.append((consulta, parametros))
        return self

    def fetchval(self):
        return 1

    def fetchone(self):
        return SimpleNamespace(
            id_persona=12,
            nombre_persona="Persona prueba",
        )

    def fetchall(self):
        if (
            "FROM ListaObservacion lo" in self.consulta
            and "SELECT\n                    lo.id_lista_observacion" in self.consulta
        ):
            return [
                SimpleNamespace(
                    id_lista_observacion=8,
                    id_persona=12,
                    nombre_persona="Persona prueba",
                    motivo="En progreso",
                    fecha_ingreso_lista=datetime(2026, 8, 13, 19, 20, 0),
                    nombre="Admin",
                    apellido="Prueba",
                )
            ]
        if "FROM Camara c" in self.consulta and "FROM Deteccion" not in self.consulta:
            return [
                SimpleNamespace(
                    id_camara=4,
                    nombre_camara="Acceso principal",
                )
            ]
        return [
            SimpleNamespace(
                id_deteccion=35,
                id_persona=12,
                nombre_persona="Persona prueba",
                id_camara=4,
                nombre_camara="Acceso principal",
                fecha_hora=datetime(2026, 8, 7, 14, 30, 15),
                ruta_imagen_detectada=None,
                resultado="Identificado",
                similitud=Decimal("0.87321"),
            )
        ]


class FabricaIngresosFalsa:
    def __init__(self):
        self.cursor = CursorIngresosFalso()

    @contextmanager
    def conectar(self):
        yield SimpleNamespace(cursor=lambda: self.cursor)


class AutenticacionIngresosFalsa:
    def obtener_sesion(self, token):
        if token != "token-prueba":
            raise RuntimeError("Token inesperado")
        return {
            "ok": True,
            "user": {"id": 1, "idCuenta": 7},
        }


class RepositorioIngresosFalso:
    def __init__(self):
        self.argumentos = None

    def listar(self, id_cuenta, pagina, limite, filtros=None):
        self.argumentos = (id_cuenta, pagina, limite, filtros)
        return {
            "total": 0,
            "pagina": pagina,
            "limite": limite,
            "ingresos": [],
        }

    def listar_camaras(self, id_cuenta):
        self.argumentos = (id_cuenta,)
        return [{"id": 4, "nombre": "Acceso principal"}]

    def listar_historial(self, id_cuenta, id_persona):
        self.argumentos = (id_cuenta, id_persona)
        return {
            "persona": {"id": id_persona, "nombre": "Persona prueba"},
            "detecciones": [],
        }

    def agregar_lista_observacion(
        self, id_cuenta, id_usuario, id_persona, motivo
    ):
        self.argumentos = (
            id_cuenta, id_usuario, id_persona, motivo
        )
        return True

    def listar_observacion(self, id_cuenta):
        self.argumentos = (id_cuenta,)
        return []


class PruebasIngresos(unittest.TestCase):
    def test_repositorio_aisla_por_cuenta_y_serializa_datos(self):
        conexiones = FabricaIngresosFalsa()
        resultado = RepositorioIngresos(conexiones).listar(7, 2, 25)

        consulta_total, parametros_total = conexiones.cursor.consultas[0]
        consulta_listado, parametros_listado = conexiones.cursor.consultas[1]
        self.assertIn("p.id_cuenta = ?", consulta_total)
        self.assertIn("gc.id_cuenta = ?", consulta_total)
        self.assertIn("d.id_persona IS NOT NULL", consulta_listado)
        self.assertIn("PARTITION BY d.id_persona", consulta_listado)
        self.assertIn("WHERE posicion = 1", consulta_listado)
        self.assertEqual(parametros_total, (7, 7))
        self.assertEqual(parametros_listado, (7, 7, 25, 25))
        self.assertEqual(resultado["ingresos"][0]["idDeteccion"], 35)
        self.assertEqual(resultado["ingresos"][0]["similitud"], 0.87321)
        self.assertEqual(
            resultado["ingresos"][0]["fechaHora"],
            "2026-08-07T14:30:15",
        )

    def test_repositorio_aplica_fechas_y_camara_como_parametros(self):
        conexiones = FabricaIngresosFalsa()
        desde = datetime(2026, 8, 7, 8, 0, 0)
        hasta = datetime(2026, 8, 7, 18, 30, 59)
        RepositorioIngresos(conexiones).listar(
            7,
            1,
            25,
            {
                "fecha_desde": desde,
                "fecha_hasta": hasta,
                "id_camara": 4,
            },
        )

        consulta_total, parametros_total = conexiones.cursor.consultas[0]
        consulta_listado, parametros_listado = conexiones.cursor.consultas[1]
        self.assertIn("d.fecha_hora >= ?", consulta_total)
        self.assertIn("d.fecha_hora <= ?", consulta_total)
        self.assertIn("d.id_camara = ?", consulta_listado)
        self.assertEqual(
            parametros_total,
            (7, 7, desde, hasta, 4),
        )
        self.assertEqual(
            parametros_listado,
            (7, 7, desde, hasta, 4, 0, 25),
        )

    def test_repositorio_lista_solo_camaras_activas_de_la_cuenta(self):
        conexiones = FabricaIngresosFalsa()
        camaras = RepositorioIngresos(conexiones).listar_camaras(7)
        consulta, parametros = conexiones.cursor.consultas[0]
        self.assertIn("gc.id_cuenta = ?", consulta)
        self.assertIn("c.activa = 1", consulta)
        self.assertEqual(parametros, (7,))
        self.assertEqual(camaras[0]["nombre"], "Acceso principal")

    def test_repositorio_lista_observacion_activa_de_la_cuenta(self):
        conexiones = FabricaIngresosFalsa()
        registros = RepositorioIngresos(conexiones).listar_observacion(7)

        consulta, parametros = conexiones.cursor.consultas[0]
        self.assertIn("lo.activa = 1", consulta)
        self.assertEqual(parametros, (7, 7))
        self.assertEqual(registros[0]["motivo"], "En progreso")
        self.assertEqual(registros[0]["registradoPor"], "Admin Prueba")

    def test_repositorio_historial_usa_la_misma_persona_y_cuenta(self):
        conexiones = FabricaIngresosFalsa()
        historial = RepositorioIngresos(conexiones).listar_historial(7, 12)

        consulta_persona, parametros_persona = conexiones.cursor.consultas[0]
        consulta_historial, parametros_historial = conexiones.cursor.consultas[1]
        self.assertIn("id_persona = ? AND id_cuenta = ?", consulta_persona)
        self.assertEqual(parametros_persona, (12, 7))
        self.assertIn("ORDER BY d.fecha_hora DESC", consulta_historial)
        self.assertEqual(parametros_historial, (12, 7, 7))
        self.assertEqual(historial["persona"]["id"], 12)

    def test_servicio_usa_cuenta_autenticada_y_valida_paginacion(self):
        repositorio = RepositorioIngresosFalso()
        servicio = ServicioIngresos(
            repositorio,
            AutenticacionIngresosFalsa(),
        )

        respuesta = servicio.listar(
            "token-prueba",
            {
                "pagina": "2",
                "limite": "10",
                "fechaDesde": "2026-08-07T08:00:00",
                "fechaHasta": "2026-08-07T18:30:59",
                "idCamara": "4",
            },
        )
        self.assertTrue(respuesta["ok"])
        self.assertEqual(repositorio.argumentos[:3], (7, 2, 10))
        self.assertEqual(
            repositorio.argumentos[3]["id_camara"],
            4,
        )

        for filtros in (
            {"pagina": "0"},
            {"pagina": "texto"},
            {"limite": "101"},
            {"idCamara": "texto"},
            {
                "fechaDesde": "2026-08-08T12:00:00",
                "fechaHasta": "2026-08-07T12:00:00",
            },
        ):
            with self.assertRaises(ValueError):
                servicio.listar("token-prueba", filtros)

        respuesta_camaras = servicio.listar_camaras("token-prueba")
        self.assertEqual(respuesta_camaras["camaras"][0]["id"], 4)
        self.assertEqual(repositorio.argumentos, (7,))

        historial = servicio.listar_historial("token-prueba", "12")
        self.assertTrue(historial["ok"])
        self.assertEqual(historial["persona"]["id"], 12)
        self.assertEqual(repositorio.argumentos, (7, 12))

        agregado = servicio.agregar_lista_observacion(
            "token-prueba",
            {"idPersona": 12},
        )
        self.assertTrue(agregado["enListaObservacion"])
        self.assertEqual(agregado["motivo"], "En progreso")
        self.assertEqual(
            repositorio.argumentos,
            (7, 1, 12, "En progreso"),
        )


if __name__ == "__main__":
    unittest.main()
