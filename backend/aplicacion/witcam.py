from backend.aplicacion.servicios import (
    ServicioGalerias,
    ServicioMonitoreo,
)
from backend.api.servidor import ServidorWitcam
from backend.config import ConfiguracionApp
from backend.galerias.repositorio import RepositorioGalerias
from backend.video.renderizado import crear_frame_mensaje


class AplicacionWitcam:
    def __init__(
        self,
        config: ConfiguracionApp,
        repositorio: RepositorioGalerias,
        monitoreo: ServicioMonitoreo,
        galerias: ServicioGalerias,
        servidor: ServidorWitcam,
    ):
        self.config = config
        self.repositorio = repositorio
        self.monitoreo = monitoreo
        self.galerias = galerias
        self.servidor = servidor

    def preparar(self) -> None:
        self.repositorio.preparar()
        config = self.config.galerias
        self.repositorio.migrar_imagenes_sueltas(
            config.carpeta_referencias
        )
        self.repositorio.migrar_imagenes_sueltas(
            config.carpeta_pendientes
        )
        motor = self.monitoreo.motor
        with motor.bloqueo:
            motor.estado.jpeg_actual = crear_frame_mensaje(
                "Presiona Iniciar en la interfaz",
                self.config.video,
            )

    def ejecutar(self) -> None:
        self.preparar()
        try:
            self.servidor.servir()
        finally:
            self.cerrar()

    def cerrar(self) -> None:
        self.monitoreo.detener()
        self.servidor.cerrar()
