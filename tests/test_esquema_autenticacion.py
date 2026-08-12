import unittest
from pathlib import Path


class PruebasEsquemaAutenticacion(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ruta = Path(__file__).resolve().parents[1] / "database" / "Tablas.sql"
        cls.sql = ruta.read_text(encoding="utf-8")

    def test_usuario_y_correo_son_unicos_solo_si_estan_activos(self):
        self.assertIn("CREATE UNIQUE INDEX UX_Usuario_Nombre_Activo", self.sql)
        self.assertIn("ON Usuario(nombre_usuario)\nWHERE id_estado_usuario = 1", self.sql)
        self.assertIn("CREATE UNIQUE INDEX UX_Usuario_Correo_Activo", self.sql)
        self.assertIn("ON Usuario(correo)\nWHERE id_estado_usuario = 1", self.sql)
        self.assertNotIn("nombre_usuario VARCHAR(100) NOT NULL UNIQUE", self.sql)
        self.assertNotIn("correo VARCHAR(250) NOT NULL UNIQUE", self.sql)

    def test_password_se_guarda_como_hash(self):
        self.assertIn("password_hash VARCHAR(255) NOT NULL", self.sql)


if __name__ == "__main__":
    unittest.main()
