from dataclasses import dataclass, field
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class ConfiguracionServidor:
    host: str = "localhost"
    puerto: int = 8000


@dataclass(frozen=True)
class ConfiguracionBaseDatos:
    controlador: str = "ODBC Driver 17 for SQL Server"
    servidor: str = "lpc:localhost"
    nombre_base: str = "WitcamBD"
    conexion_confiable: bool = True
    cifrar: bool = True
    confiar_certificado_servidor: bool = True

    def cadena_conexion(self) -> str:
        partes = [
            f"DRIVER={{{self.controlador}}}",
            f"SERVER={self.servidor}",
            f"DATABASE={self.nombre_base}",
            f"Encrypt={'yes' if self.cifrar else 'no'}",
            "TrustServerCertificate="
            f"{'yes' if self.confiar_certificado_servidor else 'no'}",
        ]
        if self.conexion_confiable:
            partes.append("Trusted_Connection=yes")
        return ";".join(partes) + ";"


@dataclass(frozen=True)
class ConfiguracionVideo:
    fuente: int | str = "MediaMTX/prueba2_10m.mp4"
    ancho_camara: int = 640
    alto_camara: int = 480
    ancho_analisis: int = 512
    alto_analisis: int = 384
    detectar_cada_n_frames: int = 1
    calidad_jpeg: int = 86
    fps_video_web: int = 12
    ancho_maximo_web: int = 1280
    alto_maximo_web: int = 720
    max_intentos_reconexion: int = 5
    intervalo_reconexion: float = 1.0


@dataclass(frozen=True)
class ConfiguracionRostro:
    reconocer_cada_n_detecciones: int = 6
    reconocer_cada_n_detecciones_sin_identidad: int = 3
    tamano_detector: int = 352
    ancho_minimo: int = 55
    alto_minimo: int = 55
    confianza_minima: float = 0.60
    simetria_minima: float = 0.25
    desviacion_maxima_nariz: float = 0.70
    proporcion_minima_ojos: float = 0.22
    descenso_minimo_nariz: float = 0.12
    descenso_maximo_nariz: float = 1.35
    descenso_minimo_boca: float = 0.15
    proporcion_minima_boca: float = 0.45
    balance_vertical_minimo: float = 0.18
    umbral_similitud: float = 0.45
    segunda_similitud_minima: float = 0.35
    umbral_galeria_una_muestra: float = 0.55


@dataclass(frozen=True)
class ConfiguracionYolo:
    habilitado: bool = True
    ruta_modelo: Path = PROJECT_ROOT / "yolo26n.pt"
    tamano_imagen: int = 416
    confianza: float = 0.35
    detectar_cada_n_ciclos: int = 3


@dataclass(frozen=True)
class ConfiguracionTracking:
    tolerancia_identidad_corporal: float = 3.0
    confirmaciones_identidad_inicial: int = 2
    similitud_identidad_inicial: float = 0.55
    confirmaciones_cambio_identidad: int = 3
    similitud_cambio_identidad: float = 0.60
    confirmaciones_contradiccion: int = 2
    similitud_maxima_incompatible: float = 0.20
    similitud_otra_identidad_fuerte: float = 0.60
    similitud_traspaso_identidad: float = 0.60
    margen_traspaso_identidad: float = 0.10
    limite_vertical_cabeza_cuerpo: float = 0.55
    proporcion_minima_rostro_en_cuerpo: float = 0.65
    margen_cambio_asociacion: float = 0.18
    iou_reasociacion_cuerpo: float = 0.30
    tolerancia_oclusion: float = 6.0
    similitud_posible_misma_persona: float = 0.30
    similitud_reidentificacion: float = 0.35
    iou_reidentificacion: float = 0.10


@dataclass(frozen=True)
class ConfiguracionDesconocidos:
    tiempo_confirmacion: float = 1.5
    muestras_minimas: int = 3
    tiempo_confirmacion_sin_cuerpo: float = 5.0
    muestras_minimas_sin_cuerpo: int = 5
    tolerancia_candidato_facial: float = 6.0
    iou_reasociacion_facial: float = 0.15
    iou_reasociacion_facial_fuerte: float = 0.45
    similitud_reasociacion_facial: float = 0.30
    cooldown_captura: float = 15.0


@dataclass(frozen=True)
class ConfiguracionGalerias:
    carpeta_referencias: Path = PROJECT_ROOT / "referencias_reconocimiento"
    carpeta_pendientes: Path = PROJECT_ROOT / "referencias_pendientes"
    intervalo_revision: float = 2.0
    similitud_evitar_duplicado: float = 0.40
    similitud_mapeo_renombrada: float = 0.95
    max_muestras_por_persona: int = 6
    similitud_muestra_redundante: float = 0.92
    similitud_muestra_semilla: float = 0.25
    intervalo_nueva_muestra: float = 1.0
    mejora_calidad_reemplazo: float = 0.05
    muestras_minimas_reconciliacion: int = 3
    similitud_principal_reconciliacion: float = 0.55
    similitud_secundaria_reconciliacion: float = 0.38
    promedio_reconciliacion: float = 0.46
    extensiones: frozenset[str] = frozenset(
        {".jpg", ".jpeg", ".png", ".webp"}
    )


@dataclass(frozen=True)
class ConfiguracionApp:
    servidor: ConfiguracionServidor = field(default_factory=ConfiguracionServidor)
    base_datos: ConfiguracionBaseDatos = field(
        default_factory=ConfiguracionBaseDatos
    )
    video: ConfiguracionVideo = field(default_factory=ConfiguracionVideo)
    rostro: ConfiguracionRostro = field(default_factory=ConfiguracionRostro)
    yolo: ConfiguracionYolo = field(default_factory=ConfiguracionYolo)
    tracking: ConfiguracionTracking = field(default_factory=ConfiguracionTracking)
    desconocidos: ConfiguracionDesconocidos = field(
        default_factory=ConfiguracionDesconocidos
    )
    galerias: ConfiguracionGalerias = field(default_factory=ConfiguracionGalerias)


def cargar_configuracion() -> ConfiguracionApp:
    return ConfiguracionApp()
