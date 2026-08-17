import threading
import uuid
import logging
from dataclasses import replace
from datetime import datetime
from pathlib import Path

import numpy as np

from backend.config import ConfiguracionGalerias
from backend.galerias.repositorio import RepositorioGalerias
from backend.utilidades.imagenes import escribir_jpg


LOGGER = logging.getLogger(__name__)


class AlmacenamientoPorCuenta:
    """Crea repositorios aislados y capturas dentro de cada cuenta."""

    def __init__(self, config: ConfiguracionGalerias):
        self.config = config
        self._repositorios: dict[int, RepositorioGalerias] = {}
        self._bloqueo = threading.RLock()

    def obtener(self, id_cuenta: int) -> RepositorioGalerias:
        if isinstance(id_cuenta, bool) or id_cuenta <= 0:
            raise ValueError("La cuenta no es valida")
        with self._bloqueo:
            existente = self._repositorios.get(id_cuenta)
            if existente is not None:
                return existente
            raiz_cuenta = self.raiz_cuenta(id_cuenta)
            config = replace(
                self.config,
                carpeta_referencias=(
                    raiz_cuenta / "galerias" / "reconocimiento"
                ),
                carpeta_pendientes=(
                    raiz_cuenta / "galerias" / "pendientes"
                ),
            )
            repositorio = RepositorioGalerias(
                config,
                self.config.directorio_datos,
            )
            repositorio.preparar()
            self._repositorios[id_cuenta] = repositorio
            return repositorio

    def raiz_cuenta(self, id_cuenta: int) -> Path:
        return (
            self.config.directorio_datos
            / "cuentas"
            / f"cuenta_{id_cuenta}"
        )

    def guardar_deteccion(
        self,
        id_cuenta: int,
        fecha: datetime,
        imagen: np.ndarray | None,
    ) -> tuple[Path | None, str | None]:
        if imagen is None or imagen.size == 0:
            return None, None
        carpeta = (
            self.raiz_cuenta(id_cuenta)
            / "detecciones"
            / f"{fecha.year:04d}"
            / f"{fecha.month:02d}"
        )
        with self._bloqueo:
            carpeta.mkdir(parents=True, exist_ok=True)
            ruta = carpeta / f"deteccion_{uuid.uuid4().hex}.jpg"
            escribir_jpg(ruta, imagen)
        relativa = ruta.relative_to(self.config.directorio_datos).as_posix()
        return ruta, relativa

    def eliminar_deteccion(self, ruta: Path | None) -> None:
        if ruta is None:
            return
        with self._bloqueo:
            ruta.unlink(missing_ok=True)

    def obtener_imagen_deteccion(
        self,
        id_cuenta: int,
        valor_ruta: str,
    ) -> Path:
        if not valor_ruta:
            raise FileNotFoundError("La deteccion no tiene un rostro disponible")
        ruta = Path(valor_ruta)
        if not ruta.is_absolute():
            ruta = self.config.directorio_datos / ruta
        raiz_detecciones = (
            self.raiz_cuenta(id_cuenta) / "detecciones"
        ).resolve()
        try:
            resuelta = ruta.resolve()
        except OSError as error:
            raise FileNotFoundError(
                "No se pudo localizar la imagen de la deteccion"
            ) from error
        if not resuelta.is_relative_to(raiz_detecciones):
            raise FileNotFoundError(
                "La imagen de la deteccion no pertenece a esta cuenta"
            )
        if not resuelta.is_file():
            raise FileNotFoundError(
                "La deteccion no tiene un rostro disponible"
            )
        return resuelta

    def eliminar_archivos_persona(
        self,
        id_cuenta: int,
        id_persona: int,
        nombre: str,
        rutas_archivos: tuple[str, ...],
    ) -> None:
        raiz_cuenta = self.raiz_cuenta(id_cuenta).resolve()
        repositorio = self.obtener(id_cuenta)
        repositorio.eliminar_persona(id_cuenta, id_persona, nombre)
        with self._bloqueo:
            for valor in rutas_archivos:
                ruta = Path(valor)
                if not ruta.is_absolute():
                    ruta = self.config.directorio_datos / ruta
                try:
                    resuelta = ruta.resolve()
                    if not resuelta.is_relative_to(raiz_cuenta):
                        LOGGER.warning(
                            "Se omitio una ruta fuera de la cuenta: %s",
                            valor,
                        )
                        continue
                    resuelta.unlink(missing_ok=True)
                except OSError:
                    LOGGER.exception(
                        "No se pudo eliminar un archivo de la persona %s",
                        id_persona,
                    )
