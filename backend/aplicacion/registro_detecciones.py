import logging
import queue
import threading

from backend.database.registro_detecciones import (
    RepositorioRegistroDetecciones,
)
from backend.dominio.modelos import EventoIdentidadEstable
from backend.galerias.almacenamiento import AlmacenamientoPorCuenta


LOGGER = logging.getLogger(__name__)


class RegistradorDetecciones:
    """Persiste eventos de IA sin bloquear el hilo que procesa video."""

    def __init__(
        self,
        repositorio_sql: RepositorioRegistroDetecciones,
        galerias: AlmacenamientoPorCuenta,
        cooldown_segundos: int,
        capacidad_cola: int,
    ):
        self.repositorio_sql = repositorio_sql
        self.galerias = galerias
        self.cooldown_segundos = cooldown_segundos
        self.cola: queue.Queue[EventoIdentidadEstable | None] = queue.Queue(
            maxsize=capacidad_cola
        )
        self.hilo = threading.Thread(target=self._procesar, daemon=True)
        self.hilo.start()

    def registrar(self, evento: EventoIdentidadEstable) -> None:
        try:
            self.cola.put_nowait(evento)
        except queue.Full:
            LOGGER.warning("Cola de detecciones llena; se descarta un evento")

    def cerrar(self) -> None:
        try:
            self.cola.put(None, timeout=5.0)
        except queue.Full:
            LOGGER.warning("No se pudo detener la cola de detecciones a tiempo")
            return
        self.hilo.join(timeout=5.0)

    def _procesar(self) -> None:
        while True:
            evento = self.cola.get()
            try:
                if evento is None:
                    return
                self._persistir(evento)
            except Exception:
                LOGGER.exception("No se pudo registrar la deteccion de IA")
            finally:
                self.cola.task_done()

    def _persistir(self, evento: EventoIdentidadEstable) -> None:
        repositorio = self.galerias.obtener(evento.id_cuenta)
        with repositorio.transaccion():
            asociaciones, muestra = repositorio.obtener_datos_persona(
                evento.tipo_galeria,
                evento.nombre,
            )
            if muestra is None:
                LOGGER.warning(
                    "Se omitio una deteccion porque su galeria no existe: %s",
                    evento.nombre,
                )
                return
            ruta, ruta_relativa = self.galerias.guardar_deteccion(
                evento.id_cuenta,
                evento.fecha_hora,
                evento.imagen,
            )
            try:
                resultado = self.repositorio_sql.registrar(
                    evento,
                    asociaciones,
                    ruta_relativa,
                    self.cooldown_segundos,
                )
            except Exception:
                self.galerias.eliminar_deteccion(ruta)
                raise
            if not resultado.insertada:
                self.galerias.eliminar_deteccion(ruta)
            if asociaciones.get(str(resultado.id_cuenta)) != resultado.id_persona:
                repositorio.guardar_id_persona(
                    evento.tipo_galeria,
                    evento.nombre,
                    resultado.id_cuenta,
                    resultado.id_persona,
                )
