from backend.galerias.repositorio import RepositorioGalerias
from backend.video.motor import MotorReconocimiento


class ServicioMonitoreo:
    def __init__(self, motor: MotorReconocimiento):
        self.motor = motor

    def iniciar(
        self,
        fuente: int | str | None = None,
        analizar: bool = True,
        id_camara: int | None = None,
    ) -> None:
        self.motor.iniciar(fuente, analizar, id_camara)

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
    def __init__(self, repositorio: RepositorioGalerias):
        self.repositorio = repositorio

    def listar(self) -> dict:
        config = self.repositorio.config
        return {
            "references": self.repositorio.listar(
                config.carpeta_referencias
            ),
            "pending": self.repositorio.listar(
                config.carpeta_pendientes
            ),
            "gallery_signature": self.repositorio.firma(),
        }

    def aprobar(self, nombre: str) -> None:
        self.repositorio.aprobar(nombre)

    def devolver_a_pendiente(self, nombre: str) -> None:
        self.repositorio.devolver_a_pendiente(nombre)

    def renombrar(
        self,
        tipo_externo: str,
        nombre: str,
        nuevo_nombre: str,
    ) -> None:
        tipo = "pendiente" if tipo_externo == "pending" else "oficial"
        self.repositorio.renombrar(tipo, nombre, nuevo_nombre)

    def rechazar(self, nombre: str) -> None:
        self.repositorio.rechazar(nombre)
