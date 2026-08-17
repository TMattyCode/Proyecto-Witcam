import hashlib
import json
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
                tipo = (
                    "pending"
                    if carpeta.resolve()
                    == self.config.carpeta_pendientes.resolve()
                    else "reference"
                )
                galerias.append(
                    {
                        "name": nombre,
                        "url": (
                            "/api/galerias/imagen"
                            f"?type={tipo}&name={quote(nombre)}"
                            f"&v={portada.stat().st_mtime_ns}"
                        ),
                        "modified": modificada,
                        "sampleCount": len(archivos),
                    }
                )
            return sorted(
                galerias,
                key=lambda item: item["modified"],
                reverse=True,
            )

    def obtener_portada(self, tipo: str, nombre: str) -> Path:
        with self._bloqueo:
            carpeta = self.carpeta_por_tipo(tipo)
            galeria = self.ruta_galeria(carpeta, nombre)
            if not galeria.is_dir():
                raise FileNotFoundError("La persona no existe")
            muestras = [
                archivo
                for archivo in galeria.iterdir()
                if archivo.is_file()
                and archivo.suffix.lower() in self.config.extensiones
            ]
            if not muestras:
                raise FileNotFoundError("La persona no tiene muestras")
            return max(
                muestras,
                key=lambda archivo: calcular_calidad_muestra(
                    leer_imagen(archivo)
                ),
            )

    def obtener_portada_persona(
        self,
        id_cuenta: int,
        id_persona: int,
        nombre: str,
    ) -> Path:
        with self._bloqueo:
            nombre_seguro = self.nombre_seguro(nombre)
            for carpeta in (
                self.config.carpeta_referencias,
                self.config.carpeta_pendientes,
            ):
                if not carpeta.is_dir():
                    continue
                for galeria in carpeta.iterdir():
                    if not galeria.is_dir():
                        continue
                    asociaciones = self._leer_metadatos(galeria)
                    if (
                        asociaciones.get(str(id_cuenta)) != id_persona
                        and galeria.name != nombre_seguro
                    ):
                        continue
                    muestras = [
                        archivo
                        for archivo in galeria.iterdir()
                        if archivo.is_file()
                        and archivo.suffix.lower() in self.config.extensiones
                    ]
                    if muestras:
                        return max(
                            muestras,
                            key=lambda archivo: calcular_calidad_muestra(
                                leer_imagen(archivo)
                            ),
                        )
        raise FileNotFoundError("La persona no tiene una muestra facial")

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

    @staticmethod
    def nombre_persona_seguro(nombre: str) -> str:
        base = Path(str(nombre)).name.strip()
        if not base:
            raise ErrorGaleria("El nombre no puede estar vacio")
        caracteres = []
        for caracter in base:
            if caracter.isalnum() or caracter in ("-", "_"):
                caracteres.append(caracter)
            elif caracter.isspace():
                caracteres.append(" ")
        limpio = "".join(caracteres).strip(" _")
        if not limpio:
            raise ErrorGaleria("El nombre debe tener letras o numeros")
        return limpio

    def ruta_galeria(self, carpeta: Path, nombre: str) -> Path:
        return carpeta / self.nombre_seguro(nombre)

    def obtener_datos_persona(
        self,
        tipo: str,
        nombre: str,
    ) -> tuple[dict[str, int], str | None]:
        """Obtiene IDs persistentes y una muestra sin exponerlos en la UI."""
        with self._bloqueo:
            galeria = self.ruta_galeria(
                self.carpeta_por_tipo(tipo),
                nombre,
            )
            if not galeria.is_dir():
                return {}, None
            metadatos = self._leer_metadatos(galeria)
            muestras = [
                archivo
                for archivo in galeria.iterdir()
                if archivo.is_file()
                and archivo.suffix.lower() in self.config.extensiones
            ]
            if not muestras:
                return metadatos, None
            mejor = max(
                muestras,
                key=lambda archivo: calcular_calidad_muestra(
                    leer_imagen(archivo)
                ),
            )
            try:
                ruta = mejor.resolve().relative_to(
                    self.raiz_proyecto.resolve()
                )
                return metadatos, ruta.as_posix()
            except ValueError:
                return metadatos, str(mejor.resolve())

    def guardar_id_persona(
        self,
        tipo: str,
        nombre: str,
        id_cuenta: int,
        id_persona: int,
    ) -> None:
        with self._bloqueo:
            galeria = self.ruta_galeria(
                self.carpeta_por_tipo(tipo),
                nombre,
            )
            if not galeria.is_dir():
                return
            asociaciones = self._leer_metadatos(galeria)
            asociaciones[str(id_cuenta)] = id_persona
            temporal = galeria / ".witcam.json.tmp"
            destino = galeria / ".witcam.json"
            temporal.write_text(
                json.dumps(
                    {"personas_por_cuenta": asociaciones},
                    sort_keys=True,
                ),
                encoding="utf-8",
            )
            temporal.replace(destino)

    @staticmethod
    def _leer_metadatos(galeria: Path) -> dict[str, int]:
        ruta = galeria / ".witcam.json"
        if not ruta.is_file():
            return {}
        try:
            contenido = json.loads(ruta.read_text(encoding="utf-8"))
            asociaciones = contenido.get("personas_por_cuenta", {})
            return {
                str(cuenta): int(persona)
                for cuenta, persona in asociaciones.items()
                if int(persona) > 0
            }
        except (OSError, ValueError, TypeError, AttributeError):
            return {}

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

    def aprobar_persona(
        self,
        id_cuenta: int,
        id_persona: int,
        nombre: str,
    ) -> str | None:
        return self._mover_persona_entre_galerias(
            self.config.carpeta_pendientes,
            self.config.carpeta_referencias,
            id_cuenta,
            id_persona,
            nombre,
        )

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

    def devolver_persona_a_pendiente(
        self,
        id_cuenta: int,
        id_persona: int,
        nombre: str,
    ) -> str | None:
        return self._mover_persona_entre_galerias(
            self.config.carpeta_referencias,
            self.config.carpeta_pendientes,
            id_cuenta,
            id_persona,
            nombre,
        )

    def _mover_persona_entre_galerias(
        self,
        origen_base: Path,
        destino_base: Path,
        id_cuenta: int,
        id_persona: int,
        nombre: str,
    ) -> str | None:
        with self._bloqueo:
            if self._buscar_galeria_persona(
                destino_base,
                id_cuenta,
                id_persona,
                nombre,
            ) is not None:
                return None
            origen = self._buscar_galeria_persona(
                origen_base,
                id_cuenta,
                id_persona,
                nombre,
            )
            if origen is None:
                raise FileNotFoundError(
                    "La persona no tiene una galeria facial disponible"
                )
            destino = self.ruta_directorio_unica(
                destino_base / origen.name
            )
            shutil.move(str(origen), str(destino))
            return destino.name

    def _buscar_galeria_persona(
        self,
        carpeta: Path,
        id_cuenta: int,
        id_persona: int,
        nombre: str,
    ) -> Path | None:
        if not carpeta.is_dir():
            return None
        for galeria in carpeta.iterdir():
            if not galeria.is_dir():
                continue
            asociaciones = self._leer_metadatos(galeria)
            if asociaciones.get(str(id_cuenta)) == id_persona:
                return galeria
        candidata = self.ruta_galeria(carpeta, nombre)
        if not candidata.is_dir():
            return None
        asociaciones = self._leer_metadatos(candidata)
        asociada = asociaciones.get(str(id_cuenta))
        return candidata if asociada in (None, id_persona) else None

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

    def renombrar_persona(
        self,
        id_cuenta: int,
        id_persona: int,
        nombre_actual: str,
        nombre_nuevo: str,
    ) -> tuple[str, str, str] | None:
        """Renombra por metadata y devuelve datos suficientes para revertir."""
        with self._bloqueo:
            for tipo, carpeta in (
                ("referencia", self.config.carpeta_referencias),
                ("pendiente", self.config.carpeta_pendientes),
            ):
                origen = self._buscar_galeria_persona(
                    carpeta,
                    id_cuenta,
                    id_persona,
                    nombre_actual,
                )
                if origen is None:
                    continue
                destino = carpeta / self.nombre_persona_seguro(nombre_nuevo)
                if origen.name == destino.name:
                    return None
                if destino.exists() and origen.resolve() != destino.resolve():
                    raise ErrorGaleria(
                        "Ya existe una galeria con ese nombre"
                    )
                nombre_origen = origen.name
                if origen.resolve() == destino.resolve():
                    temporal = self.ruta_directorio_unica(
                        origen.with_name(f"__renombrando__{origen.name}")
                    )
                    origen.rename(temporal)
                    temporal.rename(destino)
                else:
                    origen.rename(destino)
                return tipo, nombre_origen, destino.name
        return None

    def rechazar(self, nombre: str) -> None:
        with self._bloqueo:
            ruta = self.ruta_galeria(
                self.config.carpeta_pendientes,
                nombre,
            )
            if not ruta.is_dir():
                raise FileNotFoundError("La persona pendiente no existe")
            shutil.rmtree(ruta)

    def eliminar_persona(
        self,
        id_cuenta: int,
        id_persona: int,
        nombre: str,
    ) -> int:
        """Elimina galerias asociadas por metadata o por su nombre actual."""
        eliminadas = 0
        with self._bloqueo:
            for carpeta in (
                self.config.carpeta_referencias,
                self.config.carpeta_pendientes,
            ):
                if not carpeta.is_dir():
                    continue
                for galeria in list(carpeta.iterdir()):
                    if not galeria.is_dir():
                        continue
                    asociaciones = self._leer_metadatos(galeria)
                    coincide_id = (
                        asociaciones.get(str(id_cuenta)) == id_persona
                    )
                    coincide_nombre = (
                        galeria.name == self.nombre_seguro(nombre)
                    )
                    if coincide_id or coincide_nombre:
                        shutil.rmtree(galeria)
                        eliminadas += 1
        return eliminadas
