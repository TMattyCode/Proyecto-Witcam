import re
import unittest
from pathlib import Path


class PruebasEsquemaAutenticacion(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ruta = Path(__file__).resolve().parents[1] / "database" / "Tablas.sql"
        cls.sql = ruta.read_text(encoding="utf-8")

    def test_usuario_y_correo_son_unicos(self):
        self.assertRegex(
            self.sql,
            re.compile(r"nombre_usuario\s+VARCHAR\(100\)\s+NOT NULL UNIQUE", re.I),
        )
        self.assertRegex(
            self.sql,
            re.compile(r"correo\s+VARCHAR\(250\)\s+NOT NULL UNIQUE", re.I),
        )

    def test_password_se_guarda_como_hash(self):
        self.assertIn("password_hash VARCHAR(255) NOT NULL", self.sql)


if __name__ == "__main__":
    unittest.main()
