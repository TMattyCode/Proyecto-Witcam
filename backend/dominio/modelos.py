from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import numpy as np


Caja = tuple[int, int, int, int]
Color = tuple[int, int, int]


@dataclass
class ReferenciaFacial:
    nombre: str
    embedding: np.ndarray
    tipo: str
    firma_archivo: tuple[int, int] | None = None
    ruta: Path | None = None
    calidad: float = 0.0


@dataclass
class DeteccionRostro:
    bbox: Caja
    confianza: float
    puntos_clave: np.ndarray | None = None


@dataclass
class RostroModelo:
    bbox: Caja
    confianza: float
    puntos_clave: np.ndarray | None
    embedding: np.ndarray


@dataclass
class AnalisisRostro:
    bbox: Caja
    embedding: np.ndarray | None = None
    nombre: str = "Desconocido"
    similitud: float = -1.0
    tipo: str | None = None
    reconocido: bool = False
    evaluable: bool = False
    motivo_no_evaluable: str = ""
    reconocimiento_ejecutado: bool = False


@dataclass
class DeteccionPersona:
    bbox: Caja
    tracker_id: int


@dataclass
class HistorialRostro:
    nombre: str
    similitud: float
    tipo: str
    ultimo_visto: float
    embedding: np.ndarray
    bbox: Caja


@dataclass
class AsociacionRostroPersona:
    persona_id: int
    ultimo_visto: float


@dataclass
class PersonaSeguida:
    tracker_id: int
    bbox: Caja
    ultimo_visto: float
    nombre: str | None = None
    similitud: float = -1.0
    tipo: str | None = None
    embedding: np.ndarray | None = None
    rostro_origen: int | None = None
    rostros_asociados: set[int] = field(default_factory=set)
    identidad_candidata: dict | None = None
    confirmaciones_identidad: int = 0
    cambio_candidato: str | None = None
    datos_cambio: dict | None = None
    confirmaciones_cambio: int = 0
    confirmaciones_contradiccion: int = 0


@dataclass
class CandidatoDesconocido:
    inicio: float
    ultimo_visto: float
    muestras: int
    rostro_tracker_id: int
    persona_id: int | None
    bbox: Caja
    mejor_frame: np.ndarray
    mejor_bbox: Caja
    mejor_area: int
    mejor_calidad: float
    mejor_embedding: np.ndarray
    embedding_semilla: np.ndarray
    confirmaciones_incompatibles: int = 0
    guardado: bool = False
    ultima_captura: float = 0.0


@dataclass(frozen=True)
class ResultadoVisual:
    bbox: Caja
    texto: str
    color: Color


@dataclass(frozen=True)
class EventoIdentidadEstable:
    id_camara: int
    id_cuenta: int
    nombre: str
    tipo_galeria: str
    similitud: float
    fecha_hora: datetime
    imagen: np.ndarray | None = None


@dataclass
class EstadoMotor:
    ejecutando: bool = False
    transmitiendo: bool = False
    id_camara: int | None = None
    id_cuenta: int | None = None
    ultimo_error: str | None = None
    ultimo_evento: str = "Detenido"
    detecciones: list[dict] = field(default_factory=list)
    cantidad_referencias: int = 0
    jpeg_actual: bytes | None = None


@dataclass
class EstadoSeguimiento:
    candidatos_desconocidos: dict[
        tuple[str, int], CandidatoDesconocido
    ] = field(default_factory=dict)
    historial_rostros: dict[int, dict] = field(default_factory=dict)
    historial_personas: dict[int, dict] = field(default_factory=dict)
    asociaciones_rostro_persona: dict[int, AsociacionRostroPersona] = field(
        default_factory=dict
    )
