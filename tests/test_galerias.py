import tempfile
import threading
import unittest
from dataclasses import replace
from pathlib import Path

import cv2
import numpy as np

from backend.config import ConfiguracionGalerias, ConfiguracionRostro
from backend.dominio.modelos import ReferenciaFacial
from backend.galerias.reconciliacion import evaluar_coincidencia
from backend.galerias.referencias import comparar_con_referencias
from backend.galerias.repositorio import RepositorioGalerias
from backend.utilidades.imagenes import escribir_jpg


class PruebasGalerias(unittest.TestCase):
    def setUp(self):
        self.temporal = tempfile.TemporaryDirectory()
        raiz = Path(self.temporal.name)
        self.config = replace(
            ConfiguracionGalerias(),
            carpeta_referencias=raiz / "referencias",
            carpeta_pendientes=raiz / "pendientes",
        )
        self.repositorio = RepositorioGalerias(self.config, raiz)
        self.repositorio.preparar()

    def tearDown(self):
        self.temporal.cleanup()

    @staticmethod
    def _crear_imagen(ruta: Path, valor: int = 100):
        ruta.parent.mkdir(parents=True, exist_ok=True)
        imagen = np.full((80, 80, 3), valor, dtype=np.uint8)
        cv2.circle(imagen, (40, 40), 20, (255 - valor,) * 3, 2)
        escribir_jpg(ruta, imagen)

    def test_operaciones_y_contrato_de_listado(self):
        ruta = self.config.carpeta_pendientes / "Persona" / "muestra.jpg"
        self._crear_imagen(ruta)
        listado = self.repositorio.listar(self.config.carpeta_pendientes)
        self.assertEqual(len(listado), 1)
        self.assertEqual(
            set(listado[0]),
            {"name", "url", "modified", "sampleCount"},
        )
        self.assertEqual(listado[0]["sampleCount"], 1)

        self.repositorio.renombrar("pendiente", "Persona", "Matías")
        self.assertTrue((self.config.carpeta_pendientes / "Matías").is_dir())
        self.repositorio.aprobar("Matías")
        self.assertTrue((self.config.carpeta_referencias / "Matías").is_dir())
        self.repositorio.devolver_a_pendiente("Matías")
        self.repositorio.rechazar("Matías")
        self.assertEqual(self.repositorio.contar(self.config.carpeta_pendientes), 0)

    def test_elimina_galeria_por_id_persistente_aunque_cambie_el_nombre(self):
        ruta = self.config.carpeta_pendientes / "Nombre_antiguo" / "muestra.jpg"
        self._crear_imagen(ruta)
        self.repositorio.guardar_id_persona(
            "pendiente",
            "Nombre_antiguo",
            7,
            12,
        )
        self.repositorio.renombrar(
            "pendiente",
            "Nombre_antiguo",
            "Nombre_nuevo",
        )

        eliminadas = self.repositorio.eliminar_persona(
            7,
            12,
            "Nombre base de datos",
        )

        self.assertEqual(eliminadas, 1)
        self.assertFalse(
            (self.config.carpeta_pendientes / "Nombre_nuevo").exists()
        )

    def test_mueve_persona_entre_pendientes_y_reconocimiento_por_id(self):
        ruta = self.config.carpeta_pendientes / "Nombre_antiguo" / "muestra.jpg"
        self._crear_imagen(ruta)
        self.repositorio.guardar_id_persona(
            "pendiente",
            "Nombre_antiguo",
            7,
            12,
        )
        self.repositorio.renombrar(
            "pendiente",
            "Nombre_antiguo",
            "Nombre_visible",
        )

        movida = self.repositorio.aprobar_persona(
            7,
            12,
            "Nombre de base de datos",
        )
        repetida = self.repositorio.aprobar_persona(
            7,
            12,
            "Nombre de base de datos",
        )

        self.assertEqual(movida, "Nombre_visible")
        self.assertIsNone(repetida)
        self.assertTrue(
            (self.config.carpeta_referencias / "Nombre_visible").is_dir()
        )

        devuelta = self.repositorio.devolver_persona_a_pendiente(
            7,
            12,
            "Nombre de base de datos",
        )

        self.assertEqual(devuelta, "Nombre_visible")
        self.assertTrue(
            (self.config.carpeta_pendientes / "Nombre_visible").is_dir()
        )

    def test_portada_persona_elige_la_muestra_de_mejor_calidad(self):
        galeria = self.config.carpeta_pendientes / "Persona"
        galeria.mkdir()
        imagen_plana = np.full((30, 30, 3), 100, dtype=np.uint8)
        escribir_jpg(galeria / "muestra_01.jpg", imagen_plana)
        self._crear_imagen(galeria / "muestra_nitida.jpg", 80)
        self.repositorio.guardar_id_persona("pendiente", "Persona", 7, 12)

        portada = self.repositorio.obtener_portada_persona(
            7,
            12,
            "Nombre distinto",
        )

        self.assertEqual(portada.name, "muestra_nitida.jpg")

    def test_bloqueo_permite_lecturas_y_renombrados_concurrentes(self):
        self._crear_imagen(
            self.config.carpeta_pendientes / "Persona" / "muestra.jpg"
        )
        errores = []

        def leer():
            try:
                for _ in range(50):
                    self.repositorio.firma()
                    self.repositorio.listar(
                        self.config.carpeta_pendientes
                    )
            except Exception as error:
                errores.append(error)

        def renombrar():
            try:
                for _ in range(25):
                    self.repositorio.renombrar(
                        "pendiente", "Persona", "Temporal"
                    )
                    self.repositorio.renombrar(
                        "pendiente", "Temporal", "Persona"
                    )
            except Exception as error:
                errores.append(error)

        hilos = [threading.Thread(target=leer), threading.Thread(target=renombrar)]
        for hilo in hilos:
            hilo.start()
        for hilo in hilos:
            hilo.join()
        self.assertEqual(errores, [])

    def test_comparacion_exige_consenso_de_dos_muestras(self):
        embedding = np.array([1.0, 0.0], dtype=np.float32)
        referencias = [
            ReferenciaFacial("A", embedding, "pendiente"),
            ReferenciaFacial(
                "A",
                np.array([0.8, 0.6], dtype=np.float32),
                "pendiente",
            ),
            ReferenciaFacial(
                "B",
                np.array([0.0, 1.0], dtype=np.float32),
                "pendiente",
            ),
        ]
        nombre, _, _, reconocido = comparar_con_referencias(
            embedding,
            referencias,
            ConfiguracionRostro(),
        )
        self.assertEqual(nombre, "A")
        self.assertTrue(reconocido)

    def test_reconciliacion_requiere_coincidencias_independientes(self):
        base = [
            np.array([1.0, 0.0, 0.0], dtype=np.float32),
            np.array([0.9, 0.1, 0.0], dtype=np.float32),
            np.array([0.8, 0.2, 0.0], dtype=np.float32),
        ]
        muestras_a = [
            ReferenciaFacial("A", vector, "pendiente") for vector in base
        ]
        muestras_b = [
            ReferenciaFacial("B", vector, "pendiente") for vector in base
        ]
        self.assertIsNotNone(
            evaluar_coincidencia(muestras_a, muestras_b, self.config)
        )
        self.assertIsNone(
            evaluar_coincidencia(muestras_a[:2], muestras_b, self.config)
        )


if __name__ == "__main__":
    unittest.main()
