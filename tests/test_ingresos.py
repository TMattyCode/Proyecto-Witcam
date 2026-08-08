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

    def fetchall(self):
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


class PruebasIngresos(unittest.TestCase):
    def test_repositorio_aisla_por_cuenta_y_serializa_datos(self):
        conexiones = FabricaIngresosFalsa()
        resultado = RepositorioIngresos(conexiones).listar(7, 2, 25)

        consulta_total, parametros_total = conexiones.cursor.consultas[0]
        consulta_listado, parametros_listado = conexiones.cursor.consultas[1]
        self.assertIn("p.id_cuenta = ?", consulta_total)
        self.assertIn("gc.id_cuenta = ?", consulta_total)
        self.assertIn("d.id_persona IS NOT NULL", consulta_listado)
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


if __name__ == "__main__":
    unittest.main()
