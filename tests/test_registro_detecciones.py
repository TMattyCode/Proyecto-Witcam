import tempfile
import unittest
from contextlib import contextmanager
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import cv2
import numpy as np

from backend.config import ConfiguracionApp, ConfiguracionGalerias
from backend.aplicacion.registro_detecciones import RegistradorDetecciones
from backend.database.registro_detecciones import (
    RepositorioRegistroDetecciones,
    ResultadoRegistroDeteccion,
)
from backend.dominio.modelos import EstadoSeguimiento, EventoIdentidadEstable
from backend.galerias.repositorio import RepositorioGalerias
from backend.galerias.almacenamiento import AlmacenamientoPorCuenta
from backend.video.motor import MotorReconocimiento


class ConexionRegistroFalsa:
    def __init__(self, persona_existente=False, deteccion_reciente=False):
        self.persona_existente = persona_existente
        self.deteccion_reciente = deteccion_reciente
        self.consulta = ""
        self.parametros = ()
        self.consultas = []
        self.commits = 0

    def cursor(self):
        return self

    def execute(self, consulta, *parametros):
        self.consulta = consulta
        self.parametros = parametros
        self.consultas.append((consulta, parametros))
        return self

    def fetchone(self):
        if "FROM Camara c" in self.consulta:
            return SimpleNamespace(id_cuenta=7, id_grupo_camara=3)
        if "FROM Persona WITH" in self.consulta:
            return (
                SimpleNamespace(id_persona=12)
                if self.persona_existente
                else None
            )
        if "FROM Deteccion d" in self.consulta:
            return (
                SimpleNamespace(id_deteccion=99)
                if self.deteccion_reciente
                else None
            )
        return None

    def fetchval(self):
        return 12

    def commit(self):
        self.commits += 1


class FabricaRegistroFalsa:
    def __init__(self, conexion):
        self.conexion = conexion

    @contextmanager
    def conectar(self):
        yield self.conexion


class FabricaPipelineFalsa:
    detector_personas = object()


class RepositorioGaleriasFalso:
    pass


class RepositorioRegistroControlado:
    def __init__(self, insertada):
        self.insertada = insertada

    def registrar(
        self,
        evento,
        personas_por_cuenta,
        ruta_imagen,
        cooldown_segundos,
    ):
        return ResultadoRegistroDeteccion(
            id_cuenta=evento.id_cuenta,
            id_persona=12,
            insertada=self.insertada,
        )


class PruebasRegistroDetecciones(unittest.TestCase):
    def setUp(self):
        self.evento = EventoIdentidadEstable(
            id_camara=4,
            id_cuenta=7,
            nombre="Matias",
            tipo_galeria="pendiente",
            similitud=0.82,
            fecha_hora=datetime(2026, 8, 14, 12, 0, 0),
        )

    def test_inserta_persona_y_deteccion_si_no_existe_cooldown(self):
        conexion = ConexionRegistroFalsa()
        repositorio = RepositorioRegistroDetecciones(
            FabricaRegistroFalsa(conexion)
        )

        resultado = repositorio.registrar(
            self.evento,
            {},
            "referencias_pendientes/Matias/muestra.jpg",
            1800,
        )

        consultas = "\n".join(consulta for consulta, _ in conexion.consultas)
        self.assertIn("INSERT INTO Persona", consultas)
        self.assertIn("INSERT INTO Deteccion", consultas)
        self.assertEqual(resultado.id_cuenta, 7)
        self.assertEqual(resultado.id_persona, 12)
        self.assertTrue(resultado.insertada)
        self.assertEqual(conexion.commits, 1)

    def test_cooldown_usa_persona_y_grupo_y_evitar_insert_repetido(self):
        conexion = ConexionRegistroFalsa(
            persona_existente=True,
            deteccion_reciente=True,
        )
        repositorio = RepositorioRegistroDetecciones(
            FabricaRegistroFalsa(conexion)
        )

        resultado = repositorio.registrar(
            self.evento,
            {"7": 12},
            None,
            1800,
        )

        consultas = "\n".join(consulta for consulta, _ in conexion.consultas)
        self.assertIn("c.id_grupo_camara = ?", consultas)
        self.assertNotIn("INSERT INTO Deteccion", consultas)
        self.assertFalse(resultado.insertada)

    def test_motor_notifica_una_vez_por_identidad_estable(self):
        eventos = []
        motor = MotorReconocimiento(
            ConfiguracionApp(),
            RepositorioGaleriasFalso(),
            FabricaPipelineFalsa(),
            eventos.append,
        )
        motor.estado.id_camara = 4
        motor.estado.id_cuenta = 7
        frame = np.zeros((240, 240, 3), dtype=np.uint8)
        seguimiento = EstadoSeguimiento(
            historial_personas={
                8: {
                    "nombre": "Matias",
                    "tipo": "pendiente",
                    "similitud": 0.82,
                }
            }
        )

        notificadas = motor._notificar_identidades_estables(
            frame,
            seguimiento,
            {},
        )
        motor._notificar_identidades_estables(
            frame,
            seguimiento,
            notificadas,
        )
        self.assertEqual(len(eventos), 1)

        motor._notificar_identidades_estables(frame, seguimiento, {})
        self.assertEqual(len(eventos), 2)

    def test_metadato_acompana_renombrado_y_aprobacion(self):
        with tempfile.TemporaryDirectory() as temporal:
            raiz = Path(temporal)
            config = replace(
                ConfiguracionGalerias(),
                carpeta_referencias=raiz / "referencias",
                carpeta_pendientes=raiz / "pendientes",
            )
            repositorio = RepositorioGalerias(config, raiz)
            repositorio.preparar()
            galeria = config.carpeta_pendientes / "Temporal"
            galeria.mkdir()
            cv2.imwrite(
                str(galeria / "muestra.jpg"),
                np.full((32, 32, 3), 128, dtype=np.uint8),
            )

            repositorio.guardar_id_persona(
                "pendiente", "Temporal", 7, 12
            )
            repositorio.renombrar("pendiente", "Temporal", "Matias")
            repositorio.aprobar("Matias")
            asociaciones, ruta = repositorio.obtener_datos_persona(
                "oficial", "Matias"
            )

            self.assertEqual(asociaciones, {"7": 12})
            self.assertTrue(ruta.endswith("muestra.jpg"))

    def test_almacenamiento_separa_galerias_y_detecciones_por_cuenta(self):
        with tempfile.TemporaryDirectory() as temporal:
            config = replace(
                ConfiguracionGalerias(),
                directorio_datos=Path(temporal),
            )
            almacenamiento = AlmacenamientoPorCuenta(config)
            cuenta_7 = almacenamiento.obtener(7)
            cuenta_8 = almacenamiento.obtener(8)

            self.assertNotEqual(
                cuenta_7.config.carpeta_pendientes,
                cuenta_8.config.carpeta_pendientes,
            )
            self.assertIn(
                "cuenta_7",
                cuenta_7.config.carpeta_pendientes.as_posix(),
            )
            ruta, relativa = almacenamiento.guardar_deteccion(
                7,
                self.evento.fecha_hora,
                np.zeros((32, 32, 3), dtype=np.uint8),
            )
            self.assertTrue(ruta.is_file())
            self.assertTrue(
                relativa.startswith("cuentas/cuenta_7/detecciones/2026/08/")
            )

    def test_captura_solo_permanece_si_sql_inserta_la_deteccion(self):
        with tempfile.TemporaryDirectory() as temporal:
            config = replace(
                ConfiguracionGalerias(),
                directorio_datos=Path(temporal),
            )
            almacenamiento = AlmacenamientoPorCuenta(config)
            repositorio = almacenamiento.obtener(7)
            galeria = repositorio.config.carpeta_pendientes / "Matias"
            galeria.mkdir()
            cv2.imwrite(
                str(galeria / "muestra.jpg"),
                np.full((32, 32, 3), 128, dtype=np.uint8),
            )
            evento = replace(
                self.evento,
                imagen=np.zeros((32, 32, 3), dtype=np.uint8),
            )
            registrador = RegistradorDetecciones(
                RepositorioRegistroControlado(False),
                almacenamiento,
                1800,
                2,
            )
            registrador._persistir(evento)
            archivos = list(
                (almacenamiento.raiz_cuenta(7) / "detecciones").rglob("*.jpg")
            )
            registrador.cerrar()
            self.assertEqual(archivos, [])


if __name__ == "__main__":
    unittest.main()
