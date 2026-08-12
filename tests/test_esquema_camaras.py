import unittest
from pathlib import Path


RUTA_ESQUEMA = Path(__file__).resolve().parents[1] / "database" / "Tablas.sql"


class PruebasEsquemaCamaras(unittest.TestCase):
    def test_nombres_solo_son_unicos_entre_registros_activos(self):
        esquema = RUTA_ESQUEMA.read_text(encoding="utf-8")

        self.assertIn(
            "CREATE UNIQUE INDEX UX_GrupoCamara_Cuenta_Nombre_Activo",
            esquema,
        )
        self.assertIn(
            "ON GrupoCamara(id_cuenta, nombre_grupo)\nWHERE activo = 1",
            esquema,
        )
        self.assertIn(
            "CREATE UNIQUE INDEX UX_Camara_Grupo_Nombre_Activa",
            esquema,
        )
        self.assertIn(
            "ON Camara(id_grupo_camara, nombre_camara)\nWHERE activa = 1",
            esquema,
        )
        self.assertNotIn("CONSTRAINT UQ_Camara_Grupo_Nombre", esquema)
        self.assertNotIn("CONSTRAINT UQ_GrupoCamara_Cuenta_Nombre", esquema)


if __name__ == "__main__":
    unittest.main()
