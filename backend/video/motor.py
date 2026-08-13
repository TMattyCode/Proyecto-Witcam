import logging
import threading
import time
from collections.abc import Callable
from typing import Protocol

from backend.config import ConfiguracionApp
from backend.dominio.modelos import (
    EstadoMotor,
    EstadoSeguimiento,
    ResultadoVisual,
)
from backend.galerias.reconciliacion import reconciliar
from backend.galerias.referencias import (
    CargadorReferencias,
    crear_mapa_referencias,
)
from backend.galerias.repositorio import RepositorioGalerias
from backend.ia.pipeline import PipelineReconocimiento
from backend.utilidades.tiempo import limpiar_historial
from backend.video.captura import CapturadorFrames
from backend.video.renderizado import (
    ajustar_para_web,
    codificar_jpeg,
    crear_frame_mensaje,
    dibujar_resultados,
)


LOGGER = logging.getLogger(__name__)


class FabricaPipeline(Protocol):
    def preparar_modelos(self) -> CargadorReferencias:
        """Carga proveedores pesados y devuelve el cargador compartido."""

    def __call__(
        self,
        fps: float,
        registrar_evento: Callable[[str], None],
    ) -> tuple[PipelineReconocimiento, CargadorReferencias]:
        """Crea trackers dependientes de los FPS y ensambla el pipeline."""


class MotorReconocimiento:
    """Coordina captura, reconocimiento y publicacion sin logica de IA."""

    def __init__(
        self,
        config: ConfiguracionApp,
        repositorio: RepositorioGalerias,
        fabrica_pipeline: FabricaPipeline,
    ):
        self.config = config
        self.repositorio = repositorio
        self.fabrica_pipeline = fabrica_pipeline
        self.bloqueo = threading.Lock()
        self.evento_detencion = threading.Event()
        self.hilo: threading.Thread | None = None
        self.estado = EstadoMotor()
        self.resultados_dibujo: list[ResultadoVisual] = []
        self.fuente_actual: int | str = self.config.video.fuente
        self.analisis_habilitado = True

    def iniciar(
        self,
        fuente: int | str | None = None,
        analizar: bool = True,
        id_camara: int | None = None,
    ) -> None:
        if self.hilo and self.hilo.is_alive():
            return
        self.evento_detencion.clear()
        with self.bloqueo:
            self.fuente_actual = (
                self.config.video.fuente if fuente is None else fuente
            )
            self.analisis_habilitado = analizar
            self.estado.ejecutando = True
            self.estado.transmitiendo = False
            self.estado.id_camara = id_camara
            self.estado.ultimo_error = None
            self.estado.ultimo_evento = "Iniciando camara"
            self.estado.jpeg_actual = crear_frame_mensaje(
                "Iniciando camara...",
                self.config.video,
            )
            self.estado.detecciones = []
            self.resultados_dibujo = []
        self.hilo = threading.Thread(target=self._ejecutar, daemon=True)
        self.hilo.start()

    def detener(self) -> None:
        self.evento_detencion.set()
        with self.bloqueo:
            self._restablecer_estado()
        if (
            self.hilo
            and self.hilo.is_alive()
            and threading.current_thread() != self.hilo
        ):
            self.hilo.join(timeout=2.0)

    def registrar_evento(self, evento: str) -> None:
        with self.bloqueo:
            self.estado.ultimo_evento = evento

    def obtener_estado(self) -> dict:
        with self.bloqueo:
            base = {
                "running": self.estado.ejecutando,
                "streaming": self.estado.transmitiendo,
                "camera_id": self.estado.id_camara,
                "last_error": self.estado.ultimo_error,
                "last_event": self.estado.ultimo_evento,
                "detections": list(self.estado.detecciones),
                "references_count": self.estado.cantidad_referencias,
                "has_frame": self.estado.jpeg_actual is not None,
            }
        galerias = self.config.galerias
        base.update(
            {
                "references_files": self.repositorio.contar(
                    galerias.carpeta_referencias
                ),
                "pending_files": self.repositorio.contar(
                    galerias.carpeta_pendientes
                ),
                "gallery_signature": self.repositorio.firma(),
                "similarity_threshold": self.config.rostro.umbral_similitud,
            }
        )
        return base

    def obtener_frame(self) -> bytes | None:
        with self.bloqueo:
            return self.estado.jpeg_actual

    def _publicar_frame(self, frame) -> None:
        if self.evento_detencion.is_set():
            return
        jpeg = codificar_jpeg(frame, self.config.video)
        if jpeg is None:
            return
        with self.bloqueo:
            if self.evento_detencion.is_set():
                return
            self.estado.jpeg_actual = jpeg
            self.estado.transmitiendo = True

    def _ejecutar(self) -> None:
        capturador = None
        hilo_video = None
        pipeline = None
        cargador = None
        try:
            self.registrar_evento("Abriendo fuente de video")
            es_archivo = CapturadorFrames._es_archivo_local(
                self.fuente_actual
            )
            if self.analisis_habilitado and es_archivo:
                self.registrar_evento("Cargando modelos antes del video")
                cargador = self.fabrica_pipeline.preparar_modelos()
                referencias = cargador.cargar()
                reconciliar(self.repositorio, referencias)

            capturador = CapturadorFrames(
                self.fuente_actual,
                self.evento_detencion,
                self.config.video,
            )
            capturador.iniciar()
            hilo_video = threading.Thread(
                target=self._publicar_video,
                args=(capturador,),
                daemon=True,
            )
            hilo_video.start()
            self._esperar_primer_frame(capturador)

            if not self.analisis_habilitado:
                self._mantener_transmision(capturador)
                return

            if pipeline is None:
                if cargador is None:
                    self.registrar_evento("Cargando modelo")
                pipeline, cargador = self.fabrica_pipeline(
                    capturador.fps,
                    self.registrar_evento,
                )
                if not es_archivo:
                    referencias = cargador.cargar()
                    reconciliar(self.repositorio, referencias)

            self._procesar(
                capturador,
                pipeline,
                cargador,
                referencias,
            )
        except Exception as error:
            with self.bloqueo:
                self.estado.ultimo_error = (
                    "No se pudo iniciar o mantener la transmision de video."
                )
                self.estado.ultimo_evento = "Error"
            LOGGER.exception("Error en el motor de reconocimiento")
        finally:
            self.evento_detencion.set()
            if capturador is not None:
                capturador.detener()
            if hilo_video and hilo_video.is_alive():
                hilo_video.join(timeout=1.0)
            with self.bloqueo:
                self._restablecer_estado()

    def _mantener_transmision(
        self,
        capturador: CapturadorFrames,
    ) -> None:
        with self.bloqueo:
            self.estado.ultimo_evento = "Transmision activa sin analisis"
        while not self.evento_detencion.is_set():
            _, _, error = capturador.obtener()
            if error:
                raise RuntimeError(error)
            self.evento_detencion.wait(0.1)

    def _esperar_primer_frame(self, capturador: CapturadorFrames) -> None:
        limite = time.time() + 30.0
        while not self.evento_detencion.is_set():
            _, frame, error = capturador.obtener()
            if error:
                raise RuntimeError(error)
            if frame is not None:
                return
            if time.time() >= limite:
                raise RuntimeError(
                    "La fuente de video no entrego ningun frame."
                )
            self.evento_detencion.wait(0.05)

    def _procesar(
        self,
        capturador: CapturadorFrames,
        pipeline: PipelineReconocimiento,
        cargador: CargadorReferencias,
        referencias,
    ) -> None:
        estado_galerias = self.repositorio.obtener_estado()
        ultima_revision = time.time()
        seguimiento = EstadoSeguimiento()
        ultima_secuencia = capturador.secuencia_actual()
        contador_rostros = (
            self.config.rostro.reconocer_cada_n_detecciones - 1
        )
        contador_personas = self.config.yolo.detectar_cada_n_ciclos - 1
        personas = []
        with self.bloqueo:
            self.estado.ultimo_evento = "Fuente de video activa"
            self.estado.cantidad_referencias = len(referencias)

        while not self.evento_detencion.is_set():
            secuencia, frame, error = capturador.obtener()
            if error:
                raise RuntimeError(error)
            if frame is None:
                self.evento_detencion.wait(0.01)
                continue

            ahora = time.time()
            if (
                ahora - ultima_revision
                >= self.config.galerias.intervalo_revision
            ):
                nuevo_estado = self.repositorio.obtener_estado()
                if nuevo_estado != estado_galerias:
                    anteriores = referencias
                    referencias = cargador.cargar(anteriores)
                    reconciliar(self.repositorio, referencias)
                    mapa = crear_mapa_referencias(
                        anteriores,
                        referencias,
                        self.config.rostro,
                        self.config.galerias,
                    )
                    pipeline.identidades.reconciliar_referencias_activas(
                        mapa,
                        seguimiento.historial_rostros,
                        seguimiento.historial_personas,
                        seguimiento.candidatos_desconocidos,
                    )
                    estado_galerias = self.repositorio.obtener_estado()
                    contador_rostros = max(
                        contador_rostros,
                        self.config.rostro
                        .reconocer_cada_n_detecciones_sin_identidad
                        - 1,
                    )
                    with self.bloqueo:
                        self.estado.cantidad_referencias = len(referencias)
                        self.estado.ultimo_evento = (
                            "Referencias actualizadas"
                        )
                ultima_revision = ahora

            if (
                secuencia - ultima_secuencia
                < self.config.video.detectar_cada_n_frames
            ):
                self.evento_detencion.wait(0.01)
                continue
            contador_rostros += 1
            if pipeline.detector_personas is not None:
                contador_personas += 1
                if (
                    contador_personas
                    >= self.config.yolo.detectar_cada_n_ciclos
                ):
                    personas = pipeline.detectar_personas(frame)
                    contador_personas = 0
                pipeline.identidades.actualizar_personas_visibles(
                    personas,
                    seguimiento.historial_personas,
                    seguimiento.asociaciones_rostro_persona,
                    seguimiento.candidatos_desconocidos,
                )
            sin_identidad = any(
                "nombre"
                not in seguimiento.historial_personas.get(
                    persona.tracker_id,
                    {},
                )
                for persona in personas
            )
            intervalo = (
                self.config.rostro
                .reconocer_cada_n_detecciones_sin_identidad
                if sin_identidad
                else self.config.rostro.reconocer_cada_n_detecciones
            )
            reconocer = contador_rostros >= intervalo
            resultados_rostros = pipeline.analizar_frame(
                frame,
                referencias,
                reconocer,
                personas,
                seguimiento,
            )
            resultados = resultados_rostros
            if pipeline.detector_personas is not None:
                resultados = (
                    pipeline.identidades.crear_resultados_personas(
                        personas,
                        resultados_rostros,
                        seguimiento.historial_personas,
                    )
                    + resultados_rostros
                )
            if reconocer:
                contador_rostros = 0
            pipeline.desconocidos.limpiar(
                seguimiento.candidatos_desconocidos
            )
            limpiar_historial(
                seguimiento.historial_rostros,
                self.config.tracking.tolerancia_oclusion,
            )
            limpiar_historial(
                seguimiento.historial_personas,
                self.config.tracking.tolerancia_identidad_corporal,
            )
            limpiar_historial(
                seguimiento.asociaciones_rostro_persona,
                self.config.tracking.tolerancia_identidad_corporal,
            )
            with self.bloqueo:
                self.resultados_dibujo = resultados
                self.estado.detecciones = [
                    {
                        "texto": resultado.texto,
                        "color": resultado.color,
                    }
                    for resultado in resultados
                ]
            ultima_secuencia = capturador.secuencia_actual()

    def _publicar_video(self, capturador: CapturadorFrames) -> None:
        intervalo = 1.0 / self.config.video.fps_video_web
        while not self.evento_detencion.is_set():
            inicio = time.perf_counter()
            _, frame, error = capturador.obtener()
            if error:
                return
            if frame is not None:
                with self.bloqueo:
                    resultados = list(self.resultados_dibujo)
                dibujar_resultados(frame, resultados)
                self._publicar_frame(
                    ajustar_para_web(frame, self.config.video)
                )
            restante = intervalo - (time.perf_counter() - inicio)
            if restante > 0:
                self.evento_detencion.wait(restante)

    def _restablecer_estado(self) -> None:
        self.estado.ejecutando = False
        self.estado.transmitiendo = False
        self.estado.id_camara = None
        self.estado.jpeg_actual = crear_frame_mensaje(
            "Presiona Iniciar en la interfaz",
            self.config.video,
        )
        self.estado.ultimo_evento = "Detenido"
        self.estado.detecciones = []
        self.resultados_dibujo = []
