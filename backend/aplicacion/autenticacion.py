import base64
import hashlib
import hmac
import re
import secrets
import threading
from datetime import datetime

from backend.database.usuarios import RepositorioUsuarios
from backend.exceptions import CredencialesInvalidas, ErrorAutenticacion


ITERACIONES_PBKDF2 = 310_000
PATRON_CORREO = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
PATRON_USUARIO = re.compile(r"^[\w.-]+$", re.UNICODE)
PATRON_TELEFONO = re.compile(r"^[+\d\s().-]+$")


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
        nombre_usuario = self._leer_texto(datos, "nombreUsuario", 100)
        password = self._leer_texto(
            datos,
            "contrasena",
            128,
            recortar=False,
        )
        if not nombre_usuario or not password or len(password) < 8:
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
        self.usuarios.registrar_acceso(fila.id_usuario)
        token = secrets.token_urlsafe(32)
        with self._bloqueo:
            self._sesiones[token] = usuario
        return {"ok": True, "token": token, "user": usuario}

    def obtener_sesion(self, token: str) -> dict:
        usuario = self._obtener_usuario_sesion(token)
        return {"ok": True, "user": usuario}

    def exigir_permiso(self, token: str, codigo_permiso: str) -> dict:
        usuario = self._obtener_usuario_sesion(token)
        if not self.usuarios.tiene_permiso(usuario["id"], codigo_permiso):
            raise ErrorAutenticacion(
                "No tienes permiso para realizar esta operacion"
            )
        return usuario

    def obtener_resumen_cuenta(self, token: str) -> dict:
        usuario = self._obtener_usuario_sesion(token)
        resumen = self.usuarios.obtener_resumen_cuenta(usuario["idCuenta"])
        if resumen is None:
            raise ErrorAutenticacion("La cuenta asociada ya no existe")
        return {"ok": True, **resumen}

    def listar_subusuarios(self, token: str, filtros: dict | str | None = None) -> dict:
        administrador = self._obtener_administrador(token)
        if isinstance(filtros, str):
            filtros = {"estado": filtros}
        elif filtros is None:
            filtros = {}
        elif not isinstance(filtros, dict):
            raise ValueError("Los filtros no son validos")
        estado = filtros.get("estado", "activo")
        estado_normalizado = estado.strip().lower() if isinstance(estado, str) else ""
        if estado_normalizado != "activo":
            raise ValueError("Solo se pueden consultar subusuarios activos")
        usuario = self._validar_filtro_texto(filtros.get("usuario", ""), 100)
        permiso = self._validar_filtro_texto(filtros.get("permiso", ""), 50)
        registro_desde = self._validar_fecha_filtro(
            filtros.get("registroDesde", ""), "registroDesde"
        )
        registro_hasta = self._validar_fecha_filtro(
            filtros.get("registroHasta", ""), "registroHasta"
        )
        acceso_desde = self._validar_fecha_filtro(
            filtros.get("accesoDesde", ""), "accesoDesde"
        )
        acceso_hasta = self._validar_fecha_filtro(
            filtros.get("accesoHasta", ""), "accesoHasta"
        )
        sin_acceso = filtros.get("sinAcceso", "false")
        if isinstance(sin_acceso, str):
            if sin_acceso.lower() not in {"true", "false"}:
                raise ValueError("El filtro sinAcceso no es valido")
            sin_acceso = sin_acceso.lower() == "true"
        if not isinstance(sin_acceso, bool):
            raise ValueError("El filtro sinAcceso no es valido")
        if sin_acceso and (acceso_desde or acceso_hasta):
            raise ValueError(
                "No se puede combinar Nunca se ha conectado con un rango de acceso"
            )
        pagina = self._validar_entero_filtro(filtros.get("pagina", 1), "pagina", 1, None)
        limite = self._validar_entero_filtro(
            filtros.get("limite", 25), "limite", 1, 100
        )
        if registro_desde and registro_hasta and registro_desde > registro_hasta:
            raise ValueError("El rango de fecha de registro no es valido")
        if acceso_desde and acceso_hasta and acceso_desde > acceso_hasta:
            raise ValueError("El rango de ultimo acceso no es valido")

        filtros_normalizados = {
            "estado": "Activo",
            "usuario": usuario,
            "permiso": permiso,
            "registro_desde": registro_desde,
            "registro_hasta": registro_hasta,
            "acceso_desde": acceso_desde,
            "acceso_hasta": acceso_hasta,
            "sin_acceso": sin_acceso,
            "pagina": pagina,
            "limite": limite,
        }
        resultado = self.usuarios.listar_subusuarios(
            administrador["idCuenta"],
            filtros_normalizados,
        )
        return {"ok": True, "filtroEstado": estado_normalizado, **resultado}

    @staticmethod
    def _validar_filtro_texto(valor, maximo: int) -> str:
        if not isinstance(valor, str):
            raise ValueError("Uno de los filtros de texto no es valido")
        valor = valor.strip()
        if len(valor) > maximo:
            raise ValueError("Uno de los filtros supera el largo permitido")
        return valor

    @staticmethod
    def _validar_fecha_filtro(valor, nombre: str) -> str:
        if valor in (None, ""):
            return ""
        if not isinstance(valor, str):
            raise ValueError(f"El filtro {nombre} no es valido")
        try:
            return datetime.strptime(valor, "%Y-%m-%d").date().isoformat()
        except ValueError as error:
            raise ValueError(f"El filtro {nombre} no es valido") from error

    @staticmethod
    def _validar_entero_filtro(valor, nombre: str, minimo: int, maximo: int | None) -> int:
        try:
            numero = int(valor)
        except (TypeError, ValueError) as error:
            raise ValueError(f"El filtro {nombre} no es valido") from error
        if isinstance(valor, bool) or numero < minimo or (
            maximo is not None and numero > maximo
        ):
            raise ValueError(f"El filtro {nombre} no es valido")
        return numero

    def registrar_subusuario(self, token: str, datos: dict) -> dict:
        administrador = self._obtener_administrador(token)
        normalizados, permisos = self._validar_subusuario(datos)
        subusuario = self.usuarios.registrar_subusuario(
            administrador["idCuenta"],
            normalizados,
            crear_hash_password(normalizados["contrasena"]),
            permisos,
        )
        return {"ok": True, "subusuario": subusuario}

    def actualizar_estado_subusuario(self, token: str, datos: dict) -> dict:
        administrador = self._obtener_administrador(token)
        if not isinstance(datos, dict):
            raise ErrorAutenticacion("Los datos del subusuario no son validos")
        id_usuario = datos.get("id")
        if (
            isinstance(id_usuario, bool)
            or not isinstance(id_usuario, int)
            or id_usuario <= 0
        ):
            raise ErrorAutenticacion("El subusuario no es valido")
        estado_recibido = datos.get("estado")
        estado_normalizado = (
            estado_recibido.strip().lower()
            if isinstance(estado_recibido, str)
            else ""
        )
        if estado_normalizado != "inactivo":
            raise ErrorAutenticacion("Los subusuarios solo se pueden desactivar")

        actualizado = self.usuarios.actualizar_estado_subusuario(
            administrador["idCuenta"],
            id_usuario,
            "Inactivo",
        )
        if not actualizado:
            raise ErrorAutenticacion(
                "El subusuario no existe o no pertenece a esta cuenta"
            )
        if estado_normalizado == "inactivo":
            self._cerrar_sesiones_usuario(id_usuario)
        return {
            "ok": True,
            "id": id_usuario,
            "estado": "Inactivo",
        }

    def editar_subusuario(self, token: str, datos: dict) -> dict:
        administrador = self._obtener_administrador(token)
        if not isinstance(datos, dict):
            raise ErrorAutenticacion("Los datos del subusuario no son validos")
        if set(datos) - {"id", "permisos"}:
            raise ErrorAutenticacion(
                "El administrador solo puede modificar los permisos"
            )
        id_usuario = datos.get("id")
        if (
            isinstance(id_usuario, bool)
            or not isinstance(id_usuario, int)
            or id_usuario <= 0
        ):
            raise ErrorAutenticacion("El subusuario no es valido")
        permisos = self._validar_permisos(datos)
        actualizado = self.usuarios.actualizar_permisos_subusuario(
            administrador["idCuenta"],
            id_usuario,
            permisos,
        )
        if not actualizado:
            raise ErrorAutenticacion(
                "El subusuario activo no existe o no pertenece a esta cuenta"
            )
        self._cerrar_sesiones_usuario(id_usuario)
        return {
            "ok": True,
            "subusuario": {
                "id": id_usuario,
                "estado": "Activo",
                "permisos": permisos,
            },
        }

    def _cerrar_sesiones_usuario(self, id_usuario: int) -> None:
        with self._bloqueo:
            tokens = [
                token_sesion
                for token_sesion, usuario in self._sesiones.items()
                if usuario.get("id") == id_usuario
            ]
            for token_sesion in tokens:
                self._sesiones.pop(token_sesion, None)

    def _obtener_administrador(self, token: str) -> dict:
        usuario = self._obtener_usuario_sesion(token)
        if usuario.get("rol") != "Administrador":
            raise ErrorAutenticacion(
                "Solo un administrador puede gestionar subusuarios"
            )
        return usuario

    def _obtener_usuario_sesion(self, token: str) -> dict:
        with self._bloqueo:
            usuario = self._sesiones.get(token)
        if usuario is None:
            raise CredencialesInvalidas("La sesion no es valida")
        return usuario

    def cerrar_sesion(self, token: str) -> None:
        with self._bloqueo:
            self._sesiones.pop(token, None)

    @staticmethod
    def _validar_registro(datos: dict) -> dict:
        if not isinstance(datos, dict):
            raise ErrorAutenticacion("Los datos de registro no son validos")
        campos = {
            "nombre_cuenta": ServicioAutenticacion._leer_texto(
                datos, "nombreCuenta", 150
            ),
            "nombre_usuario": ServicioAutenticacion._leer_texto(
                datos, "nombreUsuario", 100
            ),
            "contrasena": ServicioAutenticacion._leer_texto(
                datos, "contrasena", 128, recortar=False
            ),
            "correo": ServicioAutenticacion._leer_texto(
                datos, "correo", 250
            ).lower(),
            "telefono": ServicioAutenticacion._leer_texto(
                datos, "telefono", 20
            ) or None,
            "nombre": ServicioAutenticacion._leer_texto(datos, "nombre", 100),
            "apellido": ServicioAutenticacion._leer_texto(
                datos, "apellido", 100
            ),
        }
        confirmacion = ServicioAutenticacion._leer_texto(
            datos,
            "confirmarContrasena",
            128,
            recortar=False,
        )
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
        if not confirmacion or confirmacion != campos["contrasena"]:
            raise ErrorAutenticacion("Las contrasenas no coinciden")
        if not PATRON_USUARIO.fullmatch(campos["nombre_usuario"]):
            raise ErrorAutenticacion(
                "El usuario solo puede contener letras, numeros, punto, guion y guion bajo"
            )
        if not PATRON_CORREO.fullmatch(campos["correo"]):
            raise ErrorAutenticacion("El correo electronico no es valido")
        if campos["telefono"] and not PATRON_TELEFONO.fullmatch(
            campos["telefono"]
        ):
            raise ErrorAutenticacion("El telefono no es valido")
        return campos

    @staticmethod
    def _validar_subusuario(
        datos: dict,
        contrasena_opcional: bool = False,
    ) -> tuple[dict, list[str]]:
        if not isinstance(datos, dict):
            raise ErrorAutenticacion("Los datos del subusuario no son validos")
        campos = {
            "nombre_usuario": ServicioAutenticacion._leer_texto(
                datos, "nombreUsuario", 100
            ),
            "contrasena": ServicioAutenticacion._leer_texto(
                datos, "contrasena", 128, recortar=False
            ),
            "correo": ServicioAutenticacion._leer_texto(
                datos, "correo", 250
            ).lower(),
            "telefono": ServicioAutenticacion._leer_texto(
                datos, "telefono", 20
            ) or None,
            "nombre": ServicioAutenticacion._leer_texto(datos, "nombre", 100),
            "apellido": ServicioAutenticacion._leer_texto(
                datos, "apellido", 100
            ),
        }
        confirmacion = ServicioAutenticacion._leer_texto(
            datos,
            "confirmarContrasena",
            128,
            recortar=False,
        )
        if any(
            not campos[campo]
            for campo in (
                "nombre_usuario",
                "correo",
                "nombre",
                "apellido",
            )
        ):
            raise ErrorAutenticacion("Completa todos los campos obligatorios")
        if not contrasena_opcional and not campos["contrasena"]:
            raise ErrorAutenticacion("Completa todos los campos obligatorios")
        if campos["contrasena"] and len(campos["contrasena"]) < 8:
            raise ErrorAutenticacion(
                "La contrasena debe tener al menos 8 caracteres"
            )
        if campos["contrasena"] != confirmacion:
            raise ErrorAutenticacion("Las contrasenas no coinciden")
        if not PATRON_USUARIO.fullmatch(campos["nombre_usuario"]):
            raise ErrorAutenticacion(
                "El usuario solo puede contener letras, numeros, punto, guion y guion bajo"
            )
        if not PATRON_CORREO.fullmatch(campos["correo"]):
            raise ErrorAutenticacion("El correo electronico no es valido")
        if campos["telefono"] and not PATRON_TELEFONO.fullmatch(
            campos["telefono"]
        ):
            raise ErrorAutenticacion("El telefono no es valido")

        permisos = ServicioAutenticacion._validar_permisos(datos)
        return campos, permisos

    @staticmethod
    def _validar_permisos(datos: dict) -> list[str]:
        permisos_recibidos = datos.get("permisos", [])
        if not isinstance(permisos_recibidos, list) or any(
            not isinstance(codigo, str) for codigo in permisos_recibidos
        ):
            raise ErrorAutenticacion("La lista de permisos no es valida")
        permisos = list(
            dict.fromkeys(
                codigo.strip()
                for codigo in permisos_recibidos
                if codigo.strip()
            )
        )
        if any(len(codigo) > 50 for codigo in permisos):
            raise ErrorAutenticacion("Uno o mas permisos no son validos")
        return permisos

    @staticmethod
    def _leer_texto(
        datos: dict,
        clave: str,
        largo_maximo: int,
        *,
        recortar: bool = True,
    ) -> str:
        if not isinstance(datos, dict):
            return ""
        valor = datos.get(clave, "")
        if not isinstance(valor, str):
            return ""
        texto = valor.strip() if recortar else valor
        if len(texto) > largo_maximo:
            raise ErrorAutenticacion(
                f"El campo {clave} supera el largo permitido"
            )
        return texto
