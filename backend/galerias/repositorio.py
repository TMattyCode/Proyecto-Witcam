import hashlib
import shutil
import threading
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import quote

from backend.config import ConfiguracionGalerias, PROJECT_ROOT
from backend.exceptions import ErrorGaleria
from backend.utilidades.imagenes import calcular_calidad_muestra, leer_imagen


class RepositorioGalerias:
    """Centraliza acceso al sistema de archivos y evita carreras entre hilos."""

    def __init__(
        self,
        config: ConfiguracionGalerias,
        raiz_proyecto: Path = PROJECT_ROOT,
    ):
        self.config = config
        self.raiz_proyecto = raiz_proyecto
        self._bloqueo = threading.RLock()

    @contextmanager
    def transaccion(self):
        with self._bloqueo:
            yield

    def preparar(self) -> None:
        with self._bloqueo:
            self.config.carpeta_referencias.mkdir(parents=True, exist_ok=True)
            self.config.carpeta_pendientes.mkdir(parents=True, exist_ok=True)

    def carpeta_por_tipo(self, tipo: str) -> Path:
        return (
            self.config.carpeta_pendientes
            if tipo == "pendiente"
            else self.config.carpeta_referencias
        )

    def iterar_muestras(self, carpeta: Path) -> list[tuple[str, Path]]:
        with self._bloqueo:
            carpeta.mkdir(parents=True, exist_ok=True)
            muestras: list[tuple[str, Path]] = []
            for elemento in carpeta.iterdir():
                if elemento.is_dir():
                    for archivo in elemento.iterdir():
                        if (
                            archivo.is_file()
                            and archivo.suffix.lower() in self.config.extensiones
                        ):
                            muestras.append((elemento.name, archivo))
                elif (
                    elemento.is_file()
                    and elemento.suffix.lower() in self.config.extensiones
                ):
                    muestras.append((elemento.stem, elemento))
            return muestras

    def obtener_estado(self) -> list[tuple[str, float, int]]:
        with self._bloqueo:
            estado = []
            for carpeta in (
                self.config.carpeta_referencias,
                self.config.carpeta_pendientes,
            ):
                for _, imagen in self.iterar_muestras(carpeta):
                    datos = imagen.stat()
                    estado.append((str(imagen), datos.st_mtime, datos.st_size))
            return sorted(estado)

    def listar(self, carpeta: Path) -> list[dict]:
        with self._bloqueo:
            muestras = self.iterar_muestras(carpeta)
            nombres = sorted({nombre for nombre, _ in muestras})
            galerias = []
            for nombre in nombres:
                archivos = [
                    archivo
                    for nombre_muestra, archivo in muestras
                    if nombre_muestra == nombre
                ]
                if not archivos:
                    continue
                portada = max(
                    archivos,
                    key=lambda archivo: calcular_calidad_muestra(
                        leer_imagen(archivo)
                    ),
                )
                modificada = max(archivo.stat().st_mtime for archivo in archivos)
                relativa = quote(
                    portada.resolve()
                    .relative_to(self.raiz_proyecto.resolve())
                    .as_posix(),
                    safe="/",
                )
                galerias.append(
                    {
                        "name": nombre,
                        "url": f"/{relativa}?v={portada.stat().st_mtime_ns}",
                        "modified": modificada,
                        "sampleCount": len(archivos),
                    }
                )
            return sorted(
                galerias,
                key=lambda item: item["modified"],
                reverse=True,
            )

    def contar(self, carpeta: Path) -> int:
        with self._bloqueo:
            return len(
                {nombre for nombre, _ in self.iterar_muestras(carpeta)}
            )

    def firma(self) -> str:
        with self._bloqueo:
            digest = hashlib.sha256()
            for etiqueta, carpeta in (
                ("references", self.config.carpeta_referencias),
                ("pending", self.config.carpeta_pendientes),
            ):
                digest.update(etiqueta.encode("utf-8"))
                muestras = sorted(
                    self.iterar_muestras(carpeta),
                    key=lambda muestra: (
                        muestra[0].casefold(),
                        muestra[1].name.casefold(),
                    ),
                )
                for nombre, archivo in muestras:
                    datos = archivo.stat()
                    digest.update(nombre.encode("utf-8"))
                    digest.update(archivo.name.encode("utf-8"))
                    digest.update(str(datos.st_mtime_ns).encode("ascii"))
                    digest.update(str(datos.st_size).encode("ascii"))
            return digest.hexdigest()

    @staticmethod
    def nombre_seguro(nombre: str) -> str:
        base = Path(str(nombre)).name.strip()
        if not base:
            raise ErrorGaleria("El nombre no puede estar vacio")
        caracteres = []
        for caracter in base:
            if caracter.isalnum() or caracter in ("-", "_"):
                caracteres.append(caracter)
            elif caracter.isspace():
                caracteres.append("_")
        limpio = "".join(caracteres).strip("_")
        if not limpio:
            raise ErrorGaleria("El nombre debe tener letras o numeros")
        return limpio

    def ruta_galeria(self, carpeta: Path, nombre: str) -> Path:
        return carpeta / self.nombre_seguro(nombre)

    @staticmethod
    def ruta_directorio_unica(ruta: Path) -> Path:
        if not ruta.exists():
            return ruta
        contador = 1
        while True:
            candidata = ruta.with_name(f"{ruta.name}_{contador}")
            if not candidata.exists():
                return candidata
            contador += 1

    def migrar_imagenes_sueltas(self, carpeta: Path) -> None:
        with self._bloqueo:
            carpeta.mkdir(parents=True, exist_ok=True)
            for archivo in list(carpeta.iterdir()):
                if (
                    not archivo.is_file()
                    or archivo.suffix.lower() not in self.config.extensiones
                ):
                    continue
                galeria = self.ruta_directorio_unica(
                    self.ruta_galeria(carpeta, archivo.stem)
                )
                galeria.mkdir()
                shutil.move(str(archivo), str(galeria / archivo.name))

    def aprobar(self, nombre: str) -> None:
        with self._bloqueo:
            origen = self.ruta_galeria(
                self.config.carpeta_pendientes,
                nombre,
            )
            destino = self.ruta_directorio_unica(
                self.ruta_galeria(
                    self.config.carpeta_referencias,
                    nombre,
                )
            )
            if not origen.is_dir():
                raise FileNotFoundError("La persona pendiente no existe")
            shutil.move(str(origen), str(destino))

    def devolver_a_pendiente(self, nombre: str) -> None:
        with self._bloqueo:
            origen = self.ruta_galeria(
                self.config.carpeta_referencias,
                nombre,
            )
            destino = self.ruta_directorio_unica(
                self.ruta_galeria(
                    self.config.carpeta_pendientes,
                    nombre,
                )
            )
            if not origen.is_dir():
                raise FileNotFoundError("La persona de referencia no existe")
            shutil.move(str(origen), str(destino))

    def renombrar(self, tipo: str, nombre_actual: str, nombre_nuevo: str) -> None:
        with self._bloqueo:
            carpeta = self.carpeta_por_tipo(tipo)
            origen = self.ruta_galeria(carpeta, nombre_actual)
            if not origen.is_dir():
                raise FileNotFoundError("La persona no existe")
            destino = self.ruta_galeria(carpeta, nombre_nuevo)
            if origen.name == destino.name:
                return
            if origen.resolve() == destino.resolve():
                temporal = self.ruta_directorio_unica(
                    origen.with_name(f"__renombrando__{origen.name}")
                )
                origen.rename(temporal)
                temporal.rename(destino)
                return
            origen.rename(self.ruta_directorio_unica(destino))

    def rechazar(self, nombre: str) -> None:
        with self._bloqueo:
            ruta = self.ruta_galeria(
                self.config.carpeta_pendientes,
                nombre,
            )
            if not ruta.is_dir():
                raise FileNotFoundError("La persona pendiente no existe")
            shutil.rmtree(ruta)
