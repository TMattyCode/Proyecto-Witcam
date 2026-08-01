import base64
import hashlib
import hmac
import secrets
import threading

from backend.database.usuarios import RepositorioUsuarios
from backend.exceptions import CredencialesInvalidas, ErrorAutenticacion


ITERACIONES_PBKDF2 = 310_000


def crear_hash_password(password: str) -> str:
    sal = secrets.token_bytes(16)
    derivada = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        sal,
        ITERACIONES_PBKDF2,
    )
    return "$".join(
        (
            "pbkdf2_sha256",
            str(ITERACIONES_PBKDF2),
            base64.b64encode(sal).decode("ascii"),
            base64.b64encode(derivada).decode("ascii"),
        )
    )


def verificar_password(password: str, password_hash: str) -> bool:
    try:
        algoritmo, iteraciones, sal_b64, derivada_b64 = password_hash.split("$")
        if algoritmo != "pbkdf2_sha256":
            return False
        sal = base64.b64decode(sal_b64)
        esperada = base64.b64decode(derivada_b64)
        obtenida = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            sal,
            int(iteraciones),
        )
        return hmac.compare_digest(obtenida, esperada)
    except (ValueError, TypeError):
        return False


class ServicioAutenticacion:
    def __init__(self, usuarios: RepositorioUsuarios):
        self.usuarios = usuarios
        self._sesiones: dict[str, dict] = {}
        self._bloqueo = threading.Lock()

    def registrar(self, datos: dict) -> dict:
        normalizados = self._validar_registro(datos)
        usuario = self.usuarios.registrar_administrador(
            normalizados,
            crear_hash_password(normalizados["contrasena"]),
        )
        return {"ok": True, "user": usuario}

    def iniciar_sesion(self, datos: dict) -> dict:
        nombre_usuario = str(datos.get("nombreUsuario", "")).strip()
        password = str(datos.get("contrasena", ""))
        if not nombre_usuario or not password:
            raise CredencialesInvalidas("Ingresa usuario y contrasena")
        fila = self.usuarios.buscar_para_login(nombre_usuario)
        if (
            fila is None
            or fila.nombre_estado != "Activo"
            or not verificar_password(password, fila.password_hash)
        ):
            raise CredencialesInvalidas("Usuario o contrasena incorrectos")
        usuario = {
            "id": fila.id_usuario,
            "idCuenta": fila.id_cuenta,
            "nombreCuenta": fila.nombre_cuenta,
            "nombreUsuario": fila.nombre_usuario,
            "nombre": fila.nombre,
            "apellido": fila.apellido,
            "correo": fila.correo,
            "rol": fila.nombre_rol,
        }
        token = secrets.token_urlsafe(32)
        with self._bloqueo:
            self._sesiones[token] = usuario
        self.usuarios.registrar_acceso(fila.id_usuario)
        return {"ok": True, "token": token, "user": usuario}

    def obtener_sesion(self, token: str) -> dict:
        with self._bloqueo:
            usuario = self._sesiones.get(token)
        if usuario is None:
            raise CredencialesInvalidas("La sesion no es valida")
        return {"ok": True, "user": usuario}

    def cerrar_sesion(self, token: str) -> None:
        with self._bloqueo:
            self._sesiones.pop(token, None)

    @staticmethod
    def _validar_registro(datos: dict) -> dict:
        campos = {
            "nombre_cuenta": str(datos.get("nombreCuenta", "")).strip(),
            "nombre_usuario": str(datos.get("nombreUsuario", "")).strip(),
            "contrasena": str(datos.get("contrasena", "")),
            "correo": str(datos.get("correo", "")).strip().lower(),
            "telefono": str(datos.get("telefono", "")).strip() or None,
            "nombre": str(datos.get("nombre", "")).strip(),
            "apellido": str(datos.get("apellido", "")).strip(),
        }
        obligatorios = (
            "nombre_cuenta",
            "nombre_usuario",
            "contrasena",
            "correo",
            "nombre",
            "apellido",
        )
        if any(not campos[campo] for campo in obligatorios):
            raise ErrorAutenticacion("Completa todos los campos obligatorios")
        if len(campos["contrasena"]) < 8:
            raise ErrorAutenticacion(
                "La contrasena debe tener al menos 8 caracteres"
            )
        if "@" not in campos["correo"]:
            raise ErrorAutenticacion("El correo electronico no es valido")
        return campos
