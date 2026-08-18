from pathlib import Path

from backend.aplicacion.autenticacion import ServicioAutenticacion
from backend.galerias.almacenamiento import AlmacenamientoPorCuenta
from backend.galerias.repositorio import RepositorioGalerias
from backend.video.motor import MotorReconocimiento


class ServicioMonitoreo:
    def __init__(
        self,
        motor: MotorReconocimiento,
        almacenamiento: AlmacenamientoPorCuenta | None = None,
    ):
        self.motor = motor
        self.almacenamiento = almacenamiento

    def iniciar(
        self,
        fuente: int | str | None = None,
        analizar: bool = True,
        id_camara: int | None = None,
        id_cuenta: int | None = None,
    ) -> None:
        repositorio = None
        if self.almacenamiento is not None and id_cuenta is not None:
            repositorio = self.almacenamiento.obtener(id_cuenta)
        self.motor.iniciar(
            fuente,
            analizar,
            id_camara,
            id_cuenta,
            repositorio,
        )

    def detener(self) -> None:
        self.motor.detener()

    def estado(self) -> dict:
        return self.motor.obtener_estado()

    def frame(self) -> bytes | None:
        return self.motor.obtener_frame()

    def camara_transmitiendo(self, id_camara: int) -> bool:
        estado = self.motor.obtener_estado()
        return estado["running"] and estado["camera_id"] == id_camara


class ServicioGalerias:
    def __init__(
        self,
        repositorio: RepositorioGalerias | AlmacenamientoPorCuenta,
        autenticacion: ServicioAutenticacion | None = None,
    ):
        self.repositorio = repositorio
        self.autenticacion = autenticacion

    def _obtener_repositorio(
        self,
        token: str | None = None,
        permiso: str = "ver",
    ) -> RepositorioGalerias:
        if isinstance(self.repositorio, RepositorioGalerias):
            return self.repositorio
        if self.autenticacion is None or token is None:
            raise ValueError("La sesion es necesaria para acceder a galerias")
        usuario = self.autenticacion.exigir_permiso(token, permiso)
        return self.repositorio.obtener(usuario["idCuenta"])

    def listar(self, token: str | None = None) -> dict:
        repositorio = self._obtener_repositorio(token)
        config = repositorio.config
        return {
            "references": repositorio.listar(
                config.carpeta_referencias
            ),
            "pending": repositorio.listar(
                config.carpeta_pendientes
            ),
            "gallery_signature": repositorio.firma(),
        }

    def aprobar(self, nombre: str, token: str | None = None) -> None:
        self._obtener_repositorio(token, "anadir").aprobar(nombre)

    def devolver_a_pendiente(
        self,
        nombre: str,
        token: str | None = None,
    ) -> None:
        self._obtener_repositorio(token, "editar").devolver_a_pendiente(nombre)

    def renombrar(
        self,
        tipo_externo: str,
        nombre: str,
        nuevo_nombre: str,
        token: str | None = None,
    ) -> None:
        tipo = "pendiente" if tipo_externo == "pending" else "oficial"
        self._obtener_repositorio(token, "editar").renombrar(
            tipo,
            nombre,
            nuevo_nombre,
        )

    def rechazar(self, nombre: str, token: str | None = None) -> None:
        self._obtener_repositorio(token, "eliminar").rechazar(nombre)

    def obtener_imagen(
        self,
        token: str,
        tipo_externo: str,
        nombre: str,
    ) -> Path:
        tipo = "pendiente" if tipo_externo == "pending" else "oficial"
        return self._obtener_repositorio(token).obtener_portada(tipo, nombre)
