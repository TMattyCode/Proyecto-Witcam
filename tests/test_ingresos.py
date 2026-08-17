import unittest
from contextlib import contextmanager
from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace

from backend.aplicacion.ingresos import ServicioIngresos
from backend.database.ingresos import (
    RepositorioIngresos,
    ResultadoEliminacionPersona,
)


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
        if "SELECT d.ruta_imagen_detectada" in self.consulta:
            return SimpleNamespace(
                ruta_imagen_detectada=(
                    "cuentas/cuenta_7/detecciones/2026/08/rostro.jpg"
                )
            )
        if "AND id_persona <> ?" in self.consulta:
            return None
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
                    nombre_usuario="admin_prueba",
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
        self.confirmada = False

    @contextmanager
    def conectar(self):
        yield SimpleNamespace(
            cursor=lambda: self.cursor,
            commit=lambda: setattr(self, "confirmada", True),
        )


class AutenticacionIngresosFalsa:
    def obtener_sesion(self, token):
        if token != "token-prueba":
            raise RuntimeError("Token inesperado")
        return {
            "ok": True,
            "user": {"id": 1, "idCuenta": 7},
        }

    def exigir_permiso(self, token, codigo_permiso):
        self.ultimo_permiso = codigo_permiso
        return self.obtener_sesion(token)["user"]


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

    def obtener_ruta_imagen_deteccion(self, id_cuenta, id_deteccion):
        self.argumentos = (id_cuenta, id_deteccion)
        return "cuentas/cuenta_7/detecciones/2026/08/rostro.jpg"

    def obtener_persona(self, id_cuenta, id_persona):
        self.argumentos = (id_cuenta, id_persona)
        return {"id": id_persona, "nombre": "Persona prueba"}

    def agregar_lista_observacion(
        self, id_cuenta, id_usuario, id_persona, motivo
    ):
        self.argumentos = (
            id_cuenta, id_usuario, id_persona, motivo
        )
        return True

    def listar_observacion(self, id_cuenta, pagina, limite):
        self.argumentos = (id_cuenta, pagina, limite)
        return {
            "total": 0,
            "pagina": pagina,
            "limite": limite,
            "registros": [],
        }

    def quitar_lista_observacion(self, id_cuenta, id_persona):
        self.argumentos = (id_cuenta, id_persona)
        return True

    def eliminar_persona(self, id_cuenta, id_persona):
        self.argumentos = (id_cuenta, id_persona)
        return ResultadoEliminacionPersona(
            id_persona=id_persona,
            nombre="Persona prueba",
            rutas_archivos=("cuentas/cuenta_7/detecciones/imagen.jpg",),
        )

    def renombrar_persona(self, id_cuenta, id_persona, nombre_nuevo):
        self.argumentos = (id_cuenta, id_persona, nombre_nuevo)
        return "Persona prueba"


class AlmacenamientoFalso:
    def __init__(self):
        self.argumentos = None

    def eliminar_archivos_persona(self, *argumentos):
        self.argumentos = argumentos

    def obtener_imagen_deteccion(self, *argumentos):
        self.argumentos = argumentos
        return "ruta/segura/rostro.jpg"

    def obtener(self, id_cuenta):
        return RepositorioGaleriaFalso()


class RepositorioGaleriaFalso:
    @contextmanager
    def transaccion(self):
        yield


class CursorEliminacionFalso:
    def __init__(self, observacion_activa=False, persona_existe=True):
        self.observacion_activa = observacion_activa
        self.persona_existe = persona_existe
        self.consulta = ""
        self.consultas = []

    def execute(self, consulta, *parametros):
        self.consulta = consulta
        self.consultas.append((consulta, parametros))
        return self

    def fetchone(self):
        if "FROM Persona WITH" in self.consulta:
            if not self.persona_existe:
                return None
            return SimpleNamespace(
                id_persona=12,
                nombre_persona="Persona prueba",
            )
        if "FROM ListaObservacion WITH" in self.consulta:
            return (
                SimpleNamespace(id_lista_observacion=8)
                if self.observacion_activa
                else None
            )
        return None

    def fetchall(self):
        if "FROM Deteccion" in self.consulta:
            return [
                SimpleNamespace(
                    ruta_archivo="cuentas/cuenta_7/detecciones/captura.jpg"
                )
            ]
        return []


class ConexionEliminacionFalsa:
    def __init__(self, cursor):
        self._cursor = cursor
        self.confirmada = False

    def cursor(self):
        return self._cursor

    def commit(self):
        self.confirmada = True


class FabricaEliminacionFalsa:
    def __init__(self, observacion_activa=False, persona_existe=True):
        self.cursor = CursorEliminacionFalso(
            observacion_activa,
            persona_existe,
        )
        self.conexion = ConexionEliminacionFalsa(self.cursor)

    @contextmanager
    def conectar(self):
        yield self.conexion


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
        self.assertFalse(resultado["ingresos"][0]["tieneRostro"])
        self.assertNotIn("rutaImagen", resultado["ingresos"][0])
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
        resultado = RepositorioIngresos(conexiones).listar_observacion(7, 2, 25)

        consulta_total, parametros_total = conexiones.cursor.consultas[0]
        consulta, parametros = conexiones.cursor.consultas[1]
        registros = resultado["registros"]
        self.assertIn("lo.activa = 1", consulta_total)
        self.assertEqual(parametros_total, (7, 7))
        self.assertIn("OFFSET ? ROWS", consulta)
        self.assertIn("FETCH NEXT ? ROWS ONLY", consulta)
        self.assertEqual(parametros, (7, 7, 25, 25))
        self.assertEqual(resultado["total"], 1)
        self.assertEqual(resultado["pagina"], 2)
        self.assertEqual(resultado["limite"], 25)
        self.assertEqual(registros[0]["motivo"], "En progreso")
        self.assertEqual(registros[0]["idPersona"], 12)
        self.assertIn("u.nombre_usuario", consulta)
        self.assertNotIn("u.apellido", consulta)
        self.assertEqual(registros[0]["registradoPor"], "admin_prueba")

    def test_reactivacion_reemplaza_el_motivo_anterior(self):
        conexiones = FabricaIngresosFalsa()

        agregado = RepositorioIngresos(
            conexiones
        ).agregar_lista_observacion(
            7,
            1,
            12,
            "Nuevo motivo",
        )

        consulta, parametros = conexiones.cursor.consultas[-1]
        self.assertTrue(agregado)
        self.assertIn("SET activa = 1", consulta)
        self.assertIn("motivo = ?", consulta)
        self.assertNotIn("AND activa = 0", consulta)
        self.assertEqual(parametros, ("Nuevo motivo", 1, 12))
        self.assertTrue(conexiones.confirmada)

    def test_repositorio_quita_observacion_solo_en_la_cuenta(self):
        conexiones = FabricaIngresosFalsa()
        resultado = RepositorioIngresos(
            conexiones
        ).quitar_lista_observacion(7, 12)

        consulta, parametros = conexiones.cursor.consultas[0]
        self.assertTrue(resultado)
        self.assertIn("SET activa = 0", consulta)
        self.assertIn("p.id_cuenta = ?", consulta)
        self.assertEqual(parametros, (12, 7))
        self.assertTrue(conexiones.confirmada)

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

        persona = RepositorioIngresos(conexiones).obtener_persona(7, 12)
        consulta_persona, parametros_persona = conexiones.cursor.consultas[-1]
        self.assertIn("id_persona = ? AND id_cuenta = ?", consulta_persona)
        self.assertEqual(parametros_persona, (12, 7))
        self.assertEqual(persona["nombre"], "Persona prueba")

        ruta = RepositorioIngresos(
            conexiones
        ).obtener_ruta_imagen_deteccion(7, 35)
        consulta_ruta, parametros_ruta = conexiones.cursor.consultas[-1]
        self.assertIn("d.id_deteccion = ?", consulta_ruta)
        self.assertIn("p.id_cuenta = ?", consulta_ruta)
        self.assertIn("gc.id_cuenta = ?", consulta_ruta)
        self.assertEqual(parametros_ruta, (35, 7, 7))
        self.assertTrue(ruta.endswith("rostro.jpg"))

    def test_repositorio_renombra_persona_solo_dentro_de_su_cuenta(self):
        conexiones = FabricaIngresosFalsa()

        anterior = RepositorioIngresos(conexiones).renombrar_persona(
            7,
            12,
            "Nombre nuevo",
        )

        consultas = conexiones.cursor.consultas
        self.assertEqual(anterior, "Persona prueba")
        self.assertIn("UPDLOCK, HOLDLOCK", consultas[0][0])
        self.assertEqual(consultas[0][1], (12, 7))
        self.assertIn("id_persona <> ?", consultas[1][0])
        self.assertEqual(consultas[1][1], (7, "Nombre nuevo", 12))
        self.assertIn("UPDATE Persona", consultas[2][0])
        self.assertEqual(consultas[2][1], ("Nombre nuevo", 12, 7))
        self.assertTrue(conexiones.confirmada)

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

        observacion = servicio.listar_observacion(
            "token-prueba",
            {"pagina": "2", "limite": "10"},
        )
        self.assertTrue(observacion["ok"])
        self.assertEqual(observacion["pagina"], 2)
        self.assertEqual(observacion["limite"], 10)
        self.assertEqual(repositorio.argumentos, (7, 2, 10))

        for parametros_invalidos in (
            {"pagina": "0"},
            {"pagina": "texto"},
            {"limite": "101"},
        ):
            with self.assertRaises(ValueError):
                servicio.listar_observacion(
                    "token-prueba",
                    parametros_invalidos,
                )

        agregado = servicio.agregar_lista_observacion(
            "token-prueba",
            {
                "idPersona": 12,
                "motivo": "  Acceso a zona restringida  ",
            },
        )
        self.assertTrue(agregado["enListaObservacion"])
        self.assertEqual(agregado["motivo"], "Acceso a zona restringida")
        self.assertEqual(
            repositorio.argumentos,
            (7, 1, 12, "Acceso a zona restringida"),
        )

        quitado = servicio.quitar_lista_observacion(
            "token-prueba",
            {"idPersona": 12},
        )
        self.assertFalse(quitado["enListaObservacion"])
        self.assertEqual(repositorio.argumentos, (7, 12))

        renombrada = servicio.renombrar_persona(
            "token-prueba",
            {"idPersona": 12, "nombre": "  Nombre nuevo  "},
        )
        self.assertEqual(renombrada["nombrePersona"], "Nombre nuevo")
        self.assertEqual(repositorio.argumentos, (7, 12, "Nombre nuevo"))

        for nombre_invalido in ("", " ", None, "x" * 151, "Nombre/invalido"):
            with self.assertRaises(ValueError):
                servicio.renombrar_persona(
                    "token-prueba",
                    {"idPersona": 12, "nombre": nombre_invalido},
                )

        almacenamiento = AlmacenamientoFalso()
        servicio_con_imagenes = ServicioIngresos(
            repositorio,
            AutenticacionIngresosFalsa(),
            almacenamiento,
        )
        rostro = servicio_con_imagenes.obtener_rostro_deteccion(
            "token-prueba",
            "35",
        )
        self.assertEqual(rostro, "ruta/segura/rostro.jpg")
        self.assertEqual(
            almacenamiento.argumentos,
            (7, "cuentas/cuenta_7/detecciones/2026/08/rostro.jpg"),
        )

        omitido = servicio.agregar_lista_observacion(
            "token-prueba",
            {"idPersona": 12},
        )
        self.assertEqual(omitido["motivo"], "")
        self.assertEqual(repositorio.argumentos, (7, 1, 12, ""))

        with self.assertRaisesRegex(ValueError, "500 caracteres"):
            servicio.agregar_lista_observacion(
                "token-prueba",
                {"idPersona": 12, "motivo": "x" * 501},
            )

    def test_eliminacion_anonimiza_detecciones_y_borra_identidad(self):
        conexiones = FabricaEliminacionFalsa()
        resultado = RepositorioIngresos(conexiones).eliminar_persona(7, 12)

        consultas = "\n".join(
            consulta for consulta, _ in conexiones.cursor.consultas
        )
        self.assertEqual(resultado.id_persona, 12)
        self.assertIn("SET id_persona = NULL", consultas)
        self.assertIn("ruta_imagen_detectada = NULL", consultas)
        self.assertIn("DELETE FROM Persona", consultas)
        self.assertTrue(conexiones.conexion.confirmada)

    def test_eliminacion_rechaza_persona_en_observacion(self):
        conexiones = FabricaEliminacionFalsa(observacion_activa=True)
        with self.assertRaisesRegex(ValueError, "lista de observacion"):
            RepositorioIngresos(conexiones).eliminar_persona(7, 12)
        self.assertFalse(conexiones.conexion.confirmada)

    def test_servicio_elimina_solo_en_cuenta_autenticada_y_limpia_archivos(self):
        repositorio = RepositorioIngresosFalso()
        almacenamiento = AlmacenamientoFalso()
        servicio = ServicioIngresos(
            repositorio,
            AutenticacionIngresosFalsa(),
            almacenamiento,
        )

        respuesta = servicio.eliminar_persona(
            "token-prueba",
            {"idPersona": 12},
        )

        self.assertTrue(respuesta["ok"])
        self.assertEqual(repositorio.argumentos, (7, 12))
        self.assertEqual(almacenamiento.argumentos[:3], (7, 12, "Persona prueba"))


if __name__ == "__main__":
    unittest.main()
