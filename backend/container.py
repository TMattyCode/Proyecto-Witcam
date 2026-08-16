from collections.abc import Callable

from backend.aplicacion.servicios import (
    ServicioGalerias,
    ServicioMonitoreo,
)
from backend.aplicacion.autenticacion import ServicioAutenticacion
from backend.aplicacion.ingresos import ServicioIngresos
from backend.aplicacion.registro_detecciones import RegistradorDetecciones
from backend.aplicacion.camaras import ServicioCamaras
from backend.aplicacion.witcam import AplicacionWitcam
from backend.api.handler import crear_handler
from backend.api.servidor import ServidorWitcam
from backend.config import ConfiguracionApp, PROJECT_ROOT, cargar_configuracion
from backend.galerias.muestras import GestorMuestras
from backend.galerias.almacenamiento import AlmacenamientoPorCuenta
from backend.galerias.referencias import CargadorReferencias
from backend.galerias.repositorio import RepositorioGalerias
from backend.database.conexion import FabricaConexionesSqlServer
from backend.database.usuarios import RepositorioUsuarios
from backend.database.ingresos import RepositorioIngresos
from backend.database.registro_detecciones import (
    RepositorioRegistroDetecciones,
)
from backend.database.camaras import RepositorioCamaras
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
        repositorio: RepositorioGalerias | None,
    ):
        self.config = config
        self.repositorio = repositorio
        self.detector_rostros = None
        self.reconocedor = None
        self.detector_personas = None
        self.cargador = None
        self.muestras = None

    def usar_repositorio(self, repositorio: RepositorioGalerias) -> None:
        if repositorio is self.repositorio:
            return
        self.repositorio = repositorio
        self.cargador = None
        self.muestras = None

    def preparar_modelos(self) -> CargadorReferencias:
        if self.repositorio is None:
            raise RuntimeError("No se ha seleccionado una cuenta para la IA")
        if self.reconocedor is None:
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
    almacenamiento = AlmacenamientoPorCuenta(config.galerias)
    fabrica = FabricaPipelineReal(config, None)
    conexiones = FabricaConexionesSqlServer(config.base_datos)
    registrador_detecciones = RegistradorDetecciones(
        RepositorioRegistroDetecciones(conexiones),
        almacenamiento,
        config.detecciones.cooldown_segundos,
        config.detecciones.capacidad_cola,
    )
    motor = MotorReconocimiento(
        config,
        None,
        fabrica,
        registrador_detecciones.registrar,
    )
    monitoreo = ServicioMonitoreo(motor, almacenamiento)
    autenticacion = ServicioAutenticacion(
        RepositorioUsuarios(conexiones)
    )
    galerias = ServicioGalerias(almacenamiento, autenticacion)
    ingresos = ServicioIngresos(
        RepositorioIngresos(conexiones),
        autenticacion,
        almacenamiento,
    )
    camaras = ServicioCamaras(
        RepositorioCamaras(
            conexiones,
            config.base_datos.secreto_camaras,
        ),
        autenticacion,
        monitoreo.camara_transmitiendo,
    )
    handler = crear_handler(
        PROJECT_ROOT,
        monitoreo,
        galerias,
        config.video,
        autenticacion,
        ingresos,
        camaras,
    )
    servidor = ServidorWitcam(config.servidor, handler)
    return AplicacionWitcam(
        config,
        None,
        monitoreo,
        galerias,
        servidor,
        registrador_detecciones,
    )


build_application = construir_aplicacion
