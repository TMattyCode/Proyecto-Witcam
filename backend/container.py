from collections.abc import Callable

from backend.aplicacion.servicios import (
    ServicioGalerias,
    ServicioMonitoreo,
)
from backend.aplicacion.autenticacion import ServicioAutenticacion
from backend.aplicacion.ingresos import ServicioIngresos
from backend.aplicacion.witcam import AplicacionWitcam
from backend.api.handler import crear_handler
from backend.api.servidor import ServidorWitcam
from backend.config import ConfiguracionApp, PROJECT_ROOT, cargar_configuracion
from backend.galerias.muestras import GestorMuestras
from backend.galerias.referencias import CargadorReferencias
from backend.galerias.repositorio import RepositorioGalerias
from backend.database.conexion import FabricaConexionesSqlServer
from backend.database.usuarios import RepositorioUsuarios
from backend.database.ingresos import RepositorioIngresos
from backend.ia.adaptadores.bytetrack import RastreadorByteTrack
from backend.ia.adaptadores.insightface import (
    DetectorScrfd,
    ReconocedorInsightFace,
    SesionInsightFace,
)
from backend.ia.adaptadores.yolo import DetectorYoloPersonas
from backend.ia.desconocidos import GestorDesconocidos
from backend.ia.identidades import GestorIdentidades
from backend.ia.pipeline import PipelineReconocimiento
from backend.video.motor import MotorReconocimiento


class FabricaPipelineReal:
    def __init__(
        self,
        config: ConfiguracionApp,
        repositorio: RepositorioGalerias,
    ):
        self.config = config
        self.repositorio = repositorio
        self.detector_rostros = None
        self.reconocedor = None
        self.detector_personas = None
        self.cargador = None
        self.muestras = None

    def preparar_modelos(self) -> CargadorReferencias:
        sesion = SesionInsightFace(self.config.rostro)
        self.detector_rostros = DetectorScrfd(sesion)
        self.reconocedor = ReconocedorInsightFace(sesion)
        self.detector_personas = (
            DetectorYoloPersonas(self.config.yolo)
            if self.config.yolo.habilitado
            else None
        )
        self.cargador = CargadorReferencias(
            self.repositorio,
            self.reconocedor,
        )
        self.muestras = GestorMuestras(
            self.repositorio,
            self.reconocedor,
            self.config.rostro,
        )
        return self.cargador

    def __call__(
        self,
        fps: float,
        registrar_evento: Callable[[str], None],
    ) -> tuple[PipelineReconocimiento, CargadorReferencias]:
        if self.cargador is None:
            self.preparar_modelos()
        identidades = GestorIdentidades(self.config.tracking)
        desconocidos = GestorDesconocidos(
            self.config.desconocidos,
            self.config.galerias,
            self.config.rostro,
            self.config.tracking,
            self.muestras,
            identidades,
            registrar_evento,
        )
        rastreador_rostros = RastreadorByteTrack(0.25, fps)
        rastreador_personas = None
        if self.detector_personas is not None:
            rastreador_personas = RastreadorByteTrack(
                self.config.yolo.confianza,
                max(
                    1,
                    round(
                        fps / self.config.yolo.detectar_cada_n_ciclos
                    ),
                ),
            )
        pipeline = PipelineReconocimiento(
            self.config,
            self.detector_rostros,
            self.reconocedor,
            rastreador_rostros,
            identidades,
            desconocidos,
            self.muestras,
            self.detector_personas,
            rastreador_personas,
        )
        return pipeline, self.cargador


def construir_aplicacion(
    config: ConfiguracionApp | None = None,
) -> AplicacionWitcam:
    config = config or cargar_configuracion()
    repositorio = RepositorioGalerias(config.galerias)
    fabrica = FabricaPipelineReal(config, repositorio)
    motor = MotorReconocimiento(config, repositorio, fabrica)
    monitoreo = ServicioMonitoreo(motor)
    galerias = ServicioGalerias(repositorio)
    conexiones = FabricaConexionesSqlServer(config.base_datos)
    autenticacion = ServicioAutenticacion(
        RepositorioUsuarios(conexiones)
    )
    ingresos = ServicioIngresos(
        RepositorioIngresos(conexiones),
        autenticacion,
    )
    handler = crear_handler(
        PROJECT_ROOT,
        monitoreo,
        galerias,
        config.video,
        autenticacion,
        ingresos,
    )
    servidor = ServidorWitcam(config.servidor, handler)
    return AplicacionWitcam(
        config,
        repositorio,
        monitoreo,
        galerias,
        servidor,
    )


build_application = construir_aplicacion
