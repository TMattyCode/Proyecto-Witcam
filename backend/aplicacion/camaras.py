from collections.abc import Callable

from backend.aplicacion.autenticacion import ServicioAutenticacion
from backend.database.camaras import RepositorioCamaras
from backend.exceptions import ErrorCamara, PermisoDenegado


class ServicioCamaras:
    TIPOS = {"webcam", "onvif", "rtsp", "simulada"}
    ESCENAS = {"entrada", "pasillo", "caja", "bodega"}

    def __init__(
        self,
        repositorio: RepositorioCamaras,
        autenticacion: ServicioAutenticacion,
        camara_transmitiendo: Callable[[int], bool] | None = None,
    ):
        self.repositorio = repositorio
        self.autenticacion = autenticacion
        self.camara_transmitiendo = camara_transmitiendo or (
            lambda _id_camara: False
        )

    def listar(self, token: str) -> dict:
        usuario = self.autenticacion.exigir_permiso(token, "ver_camaras")
        datos = self._listar_disponibles(usuario)
        return {"ok": True, **datos}

    def guardar_grupos(self, token: str, datos: dict) -> dict:
        administrador = self._exigir_administrador(token)
        if not isinstance(datos, dict) or not isinstance(
            datos.get("grupos"), list
        ):
            raise ValueError("La lista de grupos no es valida")
        grupos = [
            self._validar_grupo(grupo, indice)
            for indice, grupo in enumerate(datos["grupos"])
        ]
        if not grupos:
            raise ValueError("Debe existir al menos un grupo de camaras")
        nombres = [grupo["nombre"].casefold() for grupo in grupos]
        if len(nombres) != len(set(nombres)):
            raise ValueError("No puede haber grupos con el mismo nombre")
        self.repositorio.guardar_grupos(
            administrador["idCuenta"],
            grupos,
        )
        return self.listar(token)

    def crear(self, token: str, datos: dict) -> dict:
        administrador = self._exigir_administrador(token)
        normalizados = self._validar_camara(datos, creando=True)
        self._exigir_grupo_disponible(
            administrador, normalizados["id_grupo"]
        )
        id_camara = self.repositorio.crear(
            administrador["idCuenta"],
            normalizados,
        )
        return {"ok": True, "id": id_camara, **self.listar(token)}

    def validar_transmision(
        self,
        token: str,
        id_camara: int,
        fuente: int | str | None,
    ) -> int:
        usuario = self.autenticacion.exigir_permiso(
            token, "controlar_camaras"
        )
        camaras = self._listar_disponibles(usuario)["camaras"]
        camara = next(
            (
                actual
                for actual in camaras
                if actual["id"] == id_camara
            ),
            None,
        )
        if camara is None:
            raise ErrorCamara(
                "La camara no existe o no esta asignada a este usuario"
            )
        if camara["tipo"] != "webcam":
            raise ErrorCamara(
                "Solo la webcam puede iniciar una transmision por ahora"
            )
        if camara.get("fuente") != fuente:
            raise ErrorCamara("La fuente no corresponde a la camara indicada")
        return usuario["idCuenta"]

    def validar_detencion(
        self,
        token: str,
        id_camara: int | None,
    ) -> None:
        usuario = self.autenticacion.exigir_permiso(
            token, "controlar_camaras"
        )
        if id_camara is None:
            return
        camaras = self._listar_disponibles(usuario)["camaras"]
        if not any(camara["id"] == id_camara for camara in camaras):
            raise ErrorCamara(
                "La camara no existe o no esta asignada a este usuario"
            )

    def editar(self, token: str, datos: dict) -> dict:
        administrador = self._exigir_administrador(token)
        id_camara = self._id_positivo(datos, "id")
        self._exigir_camara_detenida(id_camara)
        self._exigir_camara_disponible(administrador, id_camara)
        normalizados = self._validar_camara(datos, creando=False)
        self._exigir_grupo_disponible(
            administrador, normalizados["id_grupo"]
        )
        if not self.repositorio.editar(
            administrador["idCuenta"],
            id_camara,
            normalizados,
        ):
            raise ErrorCamara(
                "La camara no existe o no pertenece a esta cuenta"
            )
        return {"ok": True, **self.listar(token)}

    def eliminar(self, token: str, datos: dict) -> dict:
        administrador = self._exigir_administrador(token)
        id_camara = self._id_positivo(datos, "id")
        self._exigir_camara_detenida(id_camara)
        self._exigir_camara_disponible(administrador, id_camara)
        if not self.repositorio.eliminar(
            administrador["idCuenta"],
            id_camara,
        ):
            raise ErrorCamara(
                "La camara no existe o no pertenece a esta cuenta"
            )
        return {"ok": True, **self.listar(token)}

    def _exigir_camara_detenida(self, id_camara: int) -> None:
        if self.camara_transmitiendo(id_camara):
            raise ErrorCamara(
                "No se puede editar ni eliminar una camara mientras transmite"
            )

    def _listar_disponibles(self, usuario: dict) -> dict:
        acceso_total = usuario.get("rol") == "Administrador"
        return self.repositorio.listar(
            usuario["idCuenta"],
            usuario["id"],
            acceso_total,
        )

    def _exigir_administrador(self, token: str) -> dict:
        usuario = self.autenticacion.obtener_sesion(token)["user"]
        if usuario.get("rol") != "Administrador":
            raise PermisoDenegado(
                "Solo un administrador puede gestionar camaras y grupos"
            )
        return usuario

    def _exigir_grupo_disponible(
        self,
        usuario: dict,
        id_grupo: int,
    ) -> None:
        if not any(
            grupo["id"] == id_grupo
            for grupo in self._listar_disponibles(usuario)["grupos"]
        ):
            raise ErrorCamara(
                "El grupo no existe o no esta asignado a este usuario"
            )

    def _exigir_camara_disponible(
        self,
        usuario: dict,
        id_camara: int,
    ) -> None:
        if not any(
            camara["id"] == id_camara
            for camara in self._listar_disponibles(usuario)["camaras"]
        ):
            raise ErrorCamara(
                "La camara no existe o no esta asignada a este usuario"
            )

    @classmethod
    def _validar_grupo(cls, grupo, indice: int) -> dict:
        if not isinstance(grupo, dict):
            raise ValueError("Uno de los grupos no es valido")
        identificador = grupo.get("id", f"nuevo-{indice}")
        if not isinstance(identificador, (int, str)) or isinstance(
            identificador, bool
        ):
            raise ValueError("Uno de los grupos no es valido")
        if isinstance(identificador, int) and identificador <= 0:
            raise ValueError("Uno de los grupos no es valido")
        nombre = cls._texto(grupo, "nombre", 150, obligatorio=True)
        descripcion = cls._texto(grupo, "descripcion", 250) or None
        return {
            "id": identificador,
            "nombre": nombre,
            "descripcion": descripcion,
        }

    @classmethod
    def _validar_camara(cls, datos, *, creando: bool) -> dict:
        if not isinstance(datos, dict):
            raise ValueError("Los datos de la camara no son validos")
        tipo = cls._texto(datos, "tipo", 20, obligatorio=True).lower()
        if tipo not in cls.TIPOS:
            raise ValueError("El tipo de camara no es valido")
        normalizados = {
            "id_grupo": cls._id_positivo(datos, "grupoCamaraId"),
            "nombre": cls._texto(
                datos,
                "nombre",
                150,
                obligatorio=True,
            ),
            "tipo": tipo,
            "direccion_ip": None,
            "puerto_onvif": None,
            "usuario_conexion": None,
            "password": None,
            "fuente_video": None,
            "indice_dispositivo": None,
            "escena_simulada": None,
        }
        if tipo == "webcam":
            indice = datos.get("fuente", 0)
            if (
                isinstance(indice, bool)
                or not isinstance(indice, int)
                or indice < 0
            ):
                raise ValueError("El dispositivo de webcam no es valido")
            normalizados["indice_dispositivo"] = indice
        elif tipo == "simulada":
            escena = cls._texto(
                datos,
                "escena",
                30,
                obligatorio=True,
            ).lower()
            if escena not in cls.ESCENAS:
                raise ValueError("La escena simulada no es valida")
            normalizados["escena_simulada"] = escena
        elif tipo == "rtsp":
            fuente_video = cls._texto(
                datos,
                "fuenteVideo",
                1000,
                obligatorio=True,
            )
            if not fuente_video.lower().startswith(("rtsp://", "rtsps://")):
                raise ValueError("La URL RTSP no es valida")
            normalizados["fuente_video"] = fuente_video
        else:
            normalizados["direccion_ip"] = cls._texto(
                datos,
                "direccionIp",
                255,
                obligatorio=True,
            )
            normalizados["puerto_onvif"] = cls._id_positivo(
                datos,
                "puertoOnvif",
                maximo=65535,
            )
            normalizados["usuario_conexion"] = cls._texto(
                datos,
                "usuarioConexion",
                150,
                obligatorio=True,
            )
            password = cls._texto(
                datos,
                "passwordConexion",
                256,
                recortar=False,
            )
            if creando and not password:
                raise ValueError("La contrasena de la camara es obligatoria")
            normalizados["password"] = password or None
        return normalizados

    @staticmethod
    def _texto(
        datos: dict,
        clave: str,
        maximo: int,
        *,
        obligatorio: bool = False,
        recortar: bool = True,
    ) -> str:
        valor = datos.get(clave, "")
        if not isinstance(valor, str):
            raise ValueError(f"El campo {clave} no es valido")
        valor = valor.strip() if recortar else valor
        if len(valor) > maximo or (obligatorio and not valor):
            raise ValueError(f"El campo {clave} no es valido")
        return valor

    @staticmethod
    def _id_positivo(
        datos: dict,
        clave: str,
        maximo: int | None = None,
    ) -> int:
        valor = datos.get(clave)
        try:
            numero = int(valor)
        except (TypeError, ValueError) as error:
            raise ValueError(f"El campo {clave} no es valido") from error
        if isinstance(valor, bool) or numero <= 0 or (
            maximo is not None and numero > maximo
        ):
            raise ValueError(f"El campo {clave} no es valido")
        return numero
