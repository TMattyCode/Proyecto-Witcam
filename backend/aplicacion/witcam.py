from backend.aplicacion.servicios import (
    ServicioGalerias,
    ServicioMonitoreo,
)
from backend.aplicacion.registro_detecciones import RegistradorDetecciones
from backend.api.servidor import ServidorWitcam
from backend.config import ConfiguracionApp
from backend.galerias.repositorio import RepositorioGalerias
from backend.video.renderizado import crear_frame_mensaje


class AplicacionWitcam:
    def __init__(
        self,
        config: ConfiguracionApp,
        repositorio: RepositorioGalerias | None,
        monitoreo: ServicioMonitoreo,
        galerias: ServicioGalerias,
        servidor: ServidorWitcam,
        registrador_detecciones: RegistradorDetecciones | None = None,
    ):
        self.config = config
        self.repositorio = repositorio
        self.monitoreo = monitoreo
        self.galerias = galerias
        self.servidor = servidor
        self.registrador_detecciones = registrador_detecciones

    def preparar(self) -> None:
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
        if self.registrador_detecciones is not None:
            self.registrador_detecciones.cerrar()
        self.servidor.cerrar()
