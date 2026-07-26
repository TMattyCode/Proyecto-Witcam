import json
import hashlib
import mimetypes
import os
import shutil
import threading
import time
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, unquote, urlparse

import cv2
import numpy as np
import supervision as sv
from insightface.app import FaceAnalysis
from insightface.utils import face_align
from ultralytics import YOLO

# =========================
# CONFIGURACION
# =========================

# Puede ser 0, una URL RTSP o una ruta como r"C:\Videos\prueba.mp4".
CAMARA = "MediaMTX/prueba10m.mp4"
HOST = "localhost"
PUERTO_WEB = 8000

BASE_DIR = Path(__file__).resolve().parent
CARPETA_REFERENCIAS = BASE_DIR / "referencias_reconocimiento"
CARPETA_PENDIENTES = BASE_DIR / "referencias_pendientes"
INTERVALO_REVISION_CARPETAS = 2.0

CARPETAS_REFERENCIAS = [
    {"ruta": CARPETA_REFERENCIAS, "tipo": "oficial"},
    {"ruta": CARPETA_PENDIENTES, "tipo": "pendiente"},
]

TIEMPO_CONFIRMACION_DESCONOCIDO = 1.5
MIN_MUESTRAS_DESCONOCIDO = 3
TIEMPO_CONFIRMACION_DESCONOCIDO_SIN_CUERPO = 5.0
MIN_MUESTRAS_DESCONOCIDO_SIN_CUERPO = 5
TOLERANCIA_CANDIDATO_FACIAL_SEGUNDOS = 6.0
MIN_IOU_REASOCIACION_CANDIDATO_FACIAL = 0.15
MIN_IOU_REASOCIACION_CANDIDATO_FACIAL_FUERTE = 0.45
MIN_SIMILITUD_REASOCIACION_CANDIDATO_FACIAL = 0.30
MIN_ANCHO_ROSTRO = 55
MIN_ALTO_ROSTRO = 55
MIN_CONFIANZA_ROSTRO_ANALIZABLE = 0.60
MIN_SIMETRIA_ROSTRO_ANALIZABLE = 0.25
MAX_DESVIACION_NARIZ_ANALIZABLE = 0.70
MIN_PROPORCION_OJOS_EN_ROSTRO = 0.22
MIN_DESCENSO_NARIZ_RESPECTO_OJOS = 0.12
MAX_DESCENSO_NARIZ_RESPECTO_OJOS = 1.35
MIN_DESCENSO_BOCA_RESPECTO_NARIZ = 0.15
MIN_PROPORCION_BOCA_RESPECTO_OJOS = 0.45
MIN_BALANCE_VERTICAL_ROSTRO = 0.18
COOLDOWN_CAPTURA = 15
TOLERANCIA_OCLUSION_SEGUNDOS = 6.0
MIN_SIMILITUD_POSIBLE_MISMA_PERSONA = 0.30
MIN_SIMILITUD_REIDENTIFICACION = 0.35
MIN_IOU_REIDENTIFICACION = 0.10

UMBRAL_SIMILITUD = 0.45
MIN_SEGUNDA_SIMILITUD_GALERIA = 0.35
UMBRAL_GALERIA_UNA_MUESTRA = 0.55
MIN_SIMILITUD_EVITAR_GALERIA_DUPLICADA = 0.40

ANCHO_CAMARA = 640
ALTO_CAMARA = 480
ANCHO_ANALISIS = 512
ALTO_ANALISIS = 384
DETECTAR_CADA_N_FRAMES = 1
RECONOCER_CADA_N_DETECCIONES = 6
RECONOCER_CADA_N_DETECCIONES_SIN_IDENTIDAD = 3
DET_SIZE = 352
USAR_YOLO_PERSONAS = True
MODELO_YOLO = str(BASE_DIR / "yolo26n.pt")
YOLO_IMGSZ = 416
YOLO_CONFIANZA = 0.35
DETECTAR_PERSONAS_CADA_N_CICLOS = 3
TOLERANCIA_IDENTIDAD_CORPORAL_SEGUNDOS = 3.0
MIN_CONFIRMACIONES_IDENTIDAD_INICIAL = 2
MIN_SIMILITUD_IDENTIDAD_INICIAL = 0.55
MIN_CONFIRMACIONES_CAMBIO_IDENTIDAD = 3
MIN_SIMILITUD_CAMBIO_IDENTIDAD = 0.60
MIN_CONFIRMACIONES_CONTRADICCION_IDENTIDAD = 2
MAX_SIMILITUD_IDENTIDAD_INCOMPATIBLE = 0.20
MIN_SIMILITUD_OTRA_IDENTIDAD_FUERTE = 0.60
MIN_SIMILITUD_TRASPASO_IDENTIDAD = 0.60
MARGEN_SIMILITUD_TRASPASO_IDENTIDAD = 0.10
LIMITE_VERTICAL_CABEZA_EN_CUERPO = 0.55
MIN_PROPORCION_ROSTRO_DENTRO_CUERPO = 0.65
MARGEN_CAMBIO_ASOCIACION_ROSTRO_CUERPO = 0.18
MIN_SIMILITUD_MAPEO_REFERENCIA_RENOMBRADA = 0.95
MIN_IOU_REASOCIACION_CUERPO = 0.30
MAX_MUESTRAS_POR_PERSONA = 6
MAX_SIMILITUD_MUESTRA_REDUNDANTE = 0.92
MIN_SIMILITUD_MUESTRA_CON_SEMILLA = 0.25
INTERVALO_NUEVA_MUESTRA_SEGUNDOS = 1.0
MIN_MEJORA_CALIDAD_REEMPLAZO = 0.05
MIN_MUESTRAS_RECONCILIACION_GALERIA = 3
MIN_SIMILITUD_PRINCIPAL_RECONCILIACION = 0.55
MIN_SIMILITUD_SECUNDARIA_RECONCILIACION = 0.38
MIN_PROMEDIO_RECONCILIACION = 0.46
JPEG_QUALITY = 86
FPS_VIDEO_WEB = 12
ANCHO_MAX_VIDEO_WEB = 1280
ALTO_MAX_VIDEO_WEB = 720
MAX_INTENTOS_RECONEXION = 5
INTERVALO_RECONEXION = 1.0

EXTENSIONES_IMAGEN = {".jpg", ".jpeg", ".png", ".webp"}


# =========================
# FUNCIONES IA
# =========================


def normalizar_vector(vector):
    norma = np.linalg.norm(vector)
    if norma == 0:
        return vector
    return vector / norma


def leer_imagen(ruta_imagen):
    datos = np.fromfile(str(ruta_imagen), dtype=np.uint8)

    if datos.size == 0:
        return None

    return cv2.imdecode(datos, cv2.IMREAD_COLOR)


def crear_modelo():
    print("Cargando modelo de reconocimiento facial...")

    modelo = FaceAnalysis(
        name="buffalo_l",
        allowed_modules=["detection", "recognition"],
        providers=["CPUExecutionProvider"]
    )

    modelo.prepare(
        ctx_id=-1,
        det_size=(DET_SIZE, DET_SIZE)
    )

    return modelo


def crear_modelo_personas():
    print("Cargando modelo YOLO de deteccion de personas...")
    return YOLO(MODELO_YOLO)


def obtener_rostro_principal(rostros):
    return max(
        rostros,
        key=lambda rostro: (rostro.bbox[2] - rostro.bbox[0]) * (rostro.bbox[3] - rostro.bbox[1])
    )


def iterar_muestras(carpeta):
    raiz = Path(carpeta)
    raiz.mkdir(exist_ok=True)

    for elemento in raiz.iterdir():
        if elemento.is_dir():
            for archivo in elemento.iterdir():
                if archivo.is_file() and archivo.suffix.lower() in EXTENSIONES_IMAGEN:
                    yield elemento.name, archivo
        elif elemento.is_file() and elemento.suffix.lower() in EXTENSIONES_IMAGEN:
            yield elemento.stem, elemento


def calcular_calidad_muestra(imagen):
    if imagen is None or imagen.size == 0:
        return 0.0

    alto, ancho = imagen.shape[:2]
    proporcion_tamano = min(1.0, (ancho * alto) / float(160 * 160))
    gris = cv2.cvtColor(imagen, cv2.COLOR_BGR2GRAY)
    nitidez = float(cv2.Laplacian(gris, cv2.CV_64F).var())
    proporcion_nitidez = min(1.0, nitidez / 300.0)
    return proporcion_tamano * 0.45 + proporcion_nitidez * 0.55


def cargar_referencias(modelo, referencias_anteriores=None):
    referencias = []
    cache_referencias = {
        referencia["firma_archivo"]: referencia
        for referencia in referencias_anteriores or []
        if referencia.get("firma_archivo") is not None
    }

    print("Cargando rostros de referencia...")

    for carpeta_info in CARPETAS_REFERENCIAS:
        carpeta = Path(carpeta_info["ruta"])
        tipo = carpeta_info["tipo"]
        carpeta.mkdir(exist_ok=True)

        for nombre_persona, ruta_imagen in iterar_muestras(carpeta):
            datos_archivo = ruta_imagen.stat()
            firma_archivo = (
                datos_archivo.st_mtime_ns,
                datos_archivo.st_size
            )
            referencia_cacheada = cache_referencias.get(firma_archivo)
            if referencia_cacheada is not None:
                referencias.append({
                    "nombre": nombre_persona,
                    "embedding": referencia_cacheada["embedding"].copy(),
                    "tipo": tipo,
                    "firma_archivo": firma_archivo,
                    "ruta": str(ruta_imagen),
                    "calidad": referencia_cacheada.get("calidad", 0.0)
                })
                print(
                    f"Referencia reutilizada: {nombre_persona} | tipo: {tipo}"
                )
                continue

            imagen = leer_imagen(ruta_imagen)

            if imagen is None:
                print(f"No se pudo leer: {ruta_imagen.name}")
                continue

            rostros = modelo.get(imagen)

            if len(rostros) == 0:
                print(f"No se detecto rostro en: {ruta_imagen.name}")
                continue

            rostro = obtener_rostro_principal(rostros)
            embedding = normalizar_vector(rostro.embedding)

            referencias.append({
                "nombre": nombre_persona,
                "embedding": embedding,
                "tipo": tipo,
                "firma_archivo": firma_archivo,
                "ruta": str(ruta_imagen),
                "calidad": calcular_calidad_muestra(imagen)
            })

            print(f"Referencia cargada: {nombre_persona} | tipo: {tipo}")

    if not referencias:
        print("No hay rostros de referencia validos todavia.")
        print(f"Puedes agregar imagenes manualmente en: {CARPETA_REFERENCIAS}")
        print(f"Las capturas de desconocidos se guardaran en: {CARPETA_PENDIENTES}")

    return referencias


def crear_mapa_referencias(anteriores, nuevas):
    mapa = {}

    for anterior in anteriores:
        misma_identidad = [
            nueva
            for nueva in nuevas
            if nueva["nombre"] == anterior["nombre"]
        ]
        if misma_identidad:
            mejor = max(
                misma_identidad,
                key=lambda nueva: float(
                    np.dot(anterior["embedding"], nueva["embedding"])
                )
            )
            similitud = float(
                np.dot(anterior["embedding"], mejor["embedding"])
            )
            if similitud >= UMBRAL_SIMILITUD:
                mapa[(anterior["nombre"], anterior["tipo"])] = (
                    mejor["nombre"],
                    mejor["tipo"]
                )
                continue

        if not nuevas:
            continue

        mejor = max(
            nuevas,
            key=lambda nueva: float(
                np.dot(anterior["embedding"], nueva["embedding"])
            )
        )
        similitud = float(
            np.dot(anterior["embedding"], mejor["embedding"])
        )
        if similitud >= MIN_SIMILITUD_MAPEO_REFERENCIA_RENOMBRADA:
            mapa[(anterior["nombre"], anterior["tipo"])] = (
                mejor["nombre"],
                mejor["tipo"]
            )

    return mapa


def comparar_con_referencias(embedding_actual, referencias):
    mejor_nombre = "Desconocido"
    mejor_similitud = -1
    mejor_tipo = None
    mejor_criterio = (-1, -1.0)
    mejor_reconocido = False
    similitudes_por_identidad = {}

    for referencia in referencias:
        similitud = float(np.dot(embedding_actual, referencia["embedding"]))
        clave = (referencia["nombre"], referencia["tipo"])
        similitudes_por_identidad.setdefault(clave, []).append(similitud)

    for (nombre, tipo), similitudes in similitudes_por_identidad.items():
        ordenadas = sorted(similitudes, reverse=True)
        mejor = ordenadas[0]
        if len(ordenadas) >= 2:
            segunda = ordenadas[1]
            puntuacion = (mejor + segunda) / 2.0
            reconocido = (
                mejor >= UMBRAL_SIMILITUD
                and segunda >= MIN_SEGUNDA_SIMILITUD_GALERIA
            )
        else:
            puntuacion = mejor
            reconocido = mejor >= UMBRAL_GALERIA_UNA_MUESTRA

        criterio = (1 if reconocido else 0, puntuacion)
        if criterio > mejor_criterio:
            mejor_criterio = criterio
            mejor_similitud = mejor
            mejor_nombre = nombre
            mejor_tipo = tipo
            mejor_reconocido = reconocido

    return mejor_nombre, mejor_similitud, mejor_tipo, mejor_reconocido


def evaluar_coincidencia_entre_galerias(muestras_a, muestras_b):
    if (
        len(muestras_a) < MIN_MUESTRAS_RECONCILIACION_GALERIA
        or len(muestras_b) < MIN_MUESTRAS_RECONCILIACION_GALERIA
    ):
        return None

    coincidencias = sorted(
        (
            (
                float(np.dot(muestra_a["embedding"], muestra_b["embedding"])),
                indice_a,
                indice_b
            )
            for indice_a, muestra_a in enumerate(muestras_a)
            for indice_b, muestra_b in enumerate(muestras_b)
        ),
        reverse=True
    )
    if not coincidencias:
        return None

    principal = coincidencias[0]
    secundaria = next(
        (
            coincidencia
            for coincidencia in coincidencias[1:]
            if coincidencia[1] != principal[1]
            and coincidencia[2] != principal[2]
        ),
        None
    )
    if secundaria is None:
        return None

    similitud_principal = principal[0]
    similitud_secundaria = secundaria[0]
    promedio = (similitud_principal + similitud_secundaria) / 2.0
    if (
        similitud_principal < MIN_SIMILITUD_PRINCIPAL_RECONCILIACION
        or similitud_secundaria < MIN_SIMILITUD_SECUNDARIA_RECONCILIACION
        or promedio < MIN_PROMEDIO_RECONCILIACION
    ):
        return None

    return {
        "principal": similitud_principal,
        "secundaria": similitud_secundaria,
        "promedio": promedio
    }


def obtener_antiguedad_galeria(muestras):
    fechas = []
    for muestra in muestras:
        ruta = Path(muestra.get("ruta", ""))
        if ruta.is_file():
            fechas.append(ruta.stat().st_mtime_ns)
    return min(fechas, default=time.time_ns())


def seleccionar_muestras_para_fusion(muestras_destino, muestras_origen):
    seleccionadas = sorted(
        muestras_destino,
        key=lambda muestra: obtener_antiguedad_galeria([muestra])
    )[:MAX_MUESTRAS_POR_PERSONA]

    for candidata in sorted(
        muestras_origen,
        key=lambda muestra: muestra.get("calidad", 0.0),
        reverse=True
    ):
        if len(seleccionadas) < MAX_MUESTRAS_POR_PERSONA:
            seleccionadas.append(candidata)
            continue

        peor = min(
            seleccionadas,
            key=lambda muestra: muestra.get("calidad", 0.0)
        )
        if (
            candidata.get("calidad", 0.0)
            >= peor.get("calidad", 0.0) + MIN_MEJORA_CALIDAD_REEMPLAZO
        ):
            seleccionadas.remove(peor)
            seleccionadas.append(candidata)

    return seleccionadas


def fusionar_galerias_pendientes(
    nombre_destino,
    nombre_origen,
    referencias
):
    ruta_destino = ruta_galeria_segura(CARPETA_PENDIENTES, nombre_destino)
    ruta_origen = ruta_galeria_segura(CARPETA_PENDIENTES, nombre_origen)
    if not ruta_destino.is_dir() or not ruta_origen.is_dir():
        return False

    muestras_destino = [
        referencia
        for referencia in referencias
        if referencia["tipo"] == "pendiente"
        and referencia["nombre"] == nombre_destino
    ]
    muestras_origen = [
        referencia
        for referencia in referencias
        if referencia["tipo"] == "pendiente"
        and referencia["nombre"] == nombre_origen
    ]
    seleccionadas = seleccionar_muestras_para_fusion(
        muestras_destino,
        muestras_origen
    )
    ids_seleccionadas = {id(muestra) for muestra in seleccionadas}

    for muestra in muestras_destino + muestras_origen:
        ruta_actual = Path(muestra.get("ruta", ""))
        if id(muestra) not in ids_seleccionadas:
            if ruta_actual.is_file():
                ruta_actual.unlink()
            continue

        if ruta_actual.parent == ruta_origen:
            destino_muestra = ruta_destino / ruta_actual.name
            if destino_muestra.exists():
                destino_muestra = (
                    ruta_destino
                    / f"muestra_fusion_{time.time_ns()}{ruta_actual.suffix.lower()}"
                )
            shutil.move(str(ruta_actual), str(destino_muestra))
            ruta_actual = destino_muestra

        datos = ruta_actual.stat()
        muestra["nombre"] = nombre_destino
        muestra["ruta"] = str(ruta_actual)
        muestra["firma_archivo"] = (
            datos.st_mtime_ns,
            datos.st_size
        )

    if ruta_origen.is_dir():
        shutil.rmtree(ruta_origen)

    referencias[:] = [
        referencia
        for referencia in referencias
        if not (
            referencia["tipo"] == "pendiente"
            and referencia["nombre"] in {nombre_destino, nombre_origen}
        )
    ] + seleccionadas
    return True


def reconciliar_galerias_pendientes(referencias):
    mapa_fusiones = {}

    while True:
        galerias = {}
        for referencia in referencias:
            if referencia["tipo"] == "pendiente":
                galerias.setdefault(referencia["nombre"], []).append(referencia)

        mejor_fusion = None
        nombres = sorted(galerias)
        for indice, nombre_a in enumerate(nombres):
            for nombre_b in nombres[indice + 1:]:
                resultado = evaluar_coincidencia_entre_galerias(
                    galerias[nombre_a],
                    galerias[nombre_b]
                )
                if resultado is None:
                    continue
                if (
                    mejor_fusion is None
                    or resultado["promedio"] > mejor_fusion[0]
                ):
                    mejor_fusion = (
                        resultado["promedio"],
                        nombre_a,
                        nombre_b,
                        resultado
                    )

        if mejor_fusion is None:
            break

        _, nombre_a, nombre_b, resultado = mejor_fusion
        muestras_a = galerias[nombre_a]
        muestras_b = galerias[nombre_b]
        if obtener_antiguedad_galeria(muestras_a) <= obtener_antiguedad_galeria(
            muestras_b
        ):
            nombre_destino, nombre_origen = nombre_a, nombre_b
        else:
            nombre_destino, nombre_origen = nombre_b, nombre_a

        if not fusionar_galerias_pendientes(
            nombre_destino,
            nombre_origen,
            referencias
        ):
            break

        mapa_fusiones[(nombre_origen, "pendiente")] = (
            nombre_destino,
            "pendiente"
        )
        print(
            f"Galerias duplicadas fusionadas: {nombre_origen} -> "
            f"{nombre_destino} | similitudes "
            f"{resultado['principal']:.2f}/{resultado['secundaria']:.2f}"
        )

    return mapa_fusiones


def obtener_estado_carpetas():
    estado = []

    for carpeta_info in CARPETAS_REFERENCIAS:
        carpeta = Path(carpeta_info["ruta"])
        carpeta.mkdir(exist_ok=True)

        for _, imagen in iterar_muestras(carpeta):
            datos = imagen.stat()
            estado.append((str(imagen), datos.st_mtime, datos.st_size))

    return sorted(estado)


def calcular_iou(caja_a, caja_b):
    x_a = max(caja_a[0], caja_b[0])
    y_a = max(caja_a[1], caja_b[1])
    x_b = min(caja_a[2], caja_b[2])
    y_b = min(caja_a[3], caja_b[3])

    inter_ancho = max(0, x_b - x_a)
    inter_alto = max(0, y_b - y_a)
    inter_area = inter_ancho * inter_alto

    area_a = max(0, caja_a[2] - caja_a[0]) * max(0, caja_a[3] - caja_a[1])
    area_b = max(0, caja_b[2] - caja_b[0]) * max(0, caja_b[3] - caja_b[1])

    union = area_a + area_b - inter_area

    if union == 0:
        return 0.0

    return inter_area / union


def evaluar_calidad_rostro(
    caja,
    puntos_clave,
    confianza,
    validar_tamano_confianza=True
):
    x1, y1, x2, y2 = caja
    ancho = x2 - x1
    alto = y2 - y1

    if validar_tamano_confianza:
        if ancho < MIN_ANCHO_ROSTRO or alto < MIN_ALTO_ROSTRO:
            return False, "rostro muy pequeno"

        if confianza < MIN_CONFIANZA_ROSTRO_ANALIZABLE:
            return False, "baja confianza"

    if puntos_clave is None or len(puntos_clave) < 5:
        return False, "puntos faciales insuficientes"

    ojo_izquierdo = np.asarray(puntos_clave[0], dtype=np.float32)
    ojo_derecho = np.asarray(puntos_clave[1], dtype=np.float32)
    nariz = np.asarray(puntos_clave[2], dtype=np.float32)
    boca_izquierda = np.asarray(puntos_clave[3], dtype=np.float32)
    boca_derecha = np.asarray(puntos_clave[4], dtype=np.float32)
    eje_ojos = ojo_derecho - ojo_izquierdo
    distancia_ojos = float(np.linalg.norm(eje_ojos))

    if distancia_ojos <= 1.0:
        return False, "ojos no visibles"

    punto_medio_ojos = (ojo_izquierdo + ojo_derecho) / 2.0
    punto_medio_boca = (boca_izquierda + boca_derecha) / 2.0
    distancia_nariz_izquierda = float(np.linalg.norm(nariz - ojo_izquierdo))
    distancia_nariz_derecha = float(np.linalg.norm(nariz - ojo_derecho))
    distancia_mayor = max(distancia_nariz_izquierda, distancia_nariz_derecha)
    simetria = (
        min(distancia_nariz_izquierda, distancia_nariz_derecha) / distancia_mayor
        if distancia_mayor > 0
        else 0.0
    )

    eje_ojos_normalizado = eje_ojos / distancia_ojos
    eje_vertical = np.array(
        [-eje_ojos_normalizado[1], eje_ojos_normalizado[0]],
        dtype=np.float32
    )
    if eje_vertical[1] < 0:
        eje_vertical *= -1

    descenso_nariz = float(np.dot(nariz - punto_medio_ojos, eje_vertical))
    descenso_boca = float(np.dot(punto_medio_boca - nariz, eje_vertical))
    proporcion_boca = (
        float(np.linalg.norm(boca_derecha - boca_izquierda)) / distancia_ojos
    )
    balance_vertical = (
        min(descenso_nariz, descenso_boca)
        / max(descenso_nariz, descenso_boca)
        if descenso_nariz > 0 and descenso_boca > 0
        else 0.0
    )
    desviacion_nariz = abs(
        float(np.dot(nariz - punto_medio_ojos, eje_ojos_normalizado))
    ) / distancia_ojos

    if (
        descenso_nariz / distancia_ojos
        > MAX_DESCENSO_NARIZ_RESPECTO_OJOS
    ):
        return False, "mirada demasiado baja"

    if distancia_ojos / max(ancho, 1.0) < MIN_PROPORCION_OJOS_EN_ROSTRO:
        return False, "puntos faciales poco fiables"

    if (
        descenso_nariz / distancia_ojos < MIN_DESCENSO_NARIZ_RESPECTO_OJOS
        or descenso_boca / distancia_ojos < MIN_DESCENSO_BOCA_RESPECTO_NARIZ
        or proporcion_boca < MIN_PROPORCION_BOCA_RESPECTO_OJOS
        or balance_vertical < MIN_BALANCE_VERTICAL_ROSTRO
    ):
        return False, "componentes faciales incompletos"

    if (
        simetria < MIN_SIMETRIA_ROSTRO_ANALIZABLE
        or desviacion_nariz > MAX_DESVIACION_NARIZ_ANALIZABLE
    ):
        return False, "angulo insuficiente"

    return True, None


def limpiar_tracks_antiguos(tracks, tiempo_maximo_sin_ver=2.0):
    ahora = time.time()
    ids_a_eliminar = []

    for track_id, candidato in tracks.items():
        if ahora - candidato["ultimo_visto"] > tiempo_maximo_sin_ver:
            ids_a_eliminar.append(track_id)

    for track_id in ids_a_eliminar:
        del tracks[track_id]


def limpiar_candidatos_desconocidos(candidatos):
    ahora = time.time()
    for clave, candidato in list(candidatos.items()):
        es_candidato_facial = (
            isinstance(clave, tuple)
            and len(clave) == 2
            and clave[0] == "rostro"
        )
        tolerancia = (
            TOLERANCIA_CANDIDATO_FACIAL_SEGUNDOS
            if es_candidato_facial
            else 2.0
        )
        if ahora - candidato["ultimo_visto"] > tolerancia:
            candidatos.pop(clave, None)


def clave_candidato_desconocido(tracker_id, persona_id=None):
    if persona_id is not None:
        return ("persona", int(persona_id))
    return ("rostro", int(tracker_id))


def eliminar_candidato_desconocido(
    candidatos,
    tracker_id=None,
    persona_id=None
):
    if tracker_id is not None:
        candidatos.pop(("rostro", int(tracker_id)), None)
        candidatos.pop(int(tracker_id), None)
    if persona_id is not None:
        candidatos.pop(("persona", int(persona_id)), None)


def limpiar_historial_reconocidos(historial, tiempo_maximo_sin_ver=10.0):
    ahora = time.time()
    ids_a_eliminar = []

    for track_id, datos in historial.items():
        if ahora - datos["ultimo_visto"] > tiempo_maximo_sin_ver:
            ids_a_eliminar.append(track_id)

    for track_id in ids_a_eliminar:
        del historial[track_id]


# =========================
# MOTOR DE RECONOCIMIENTO
# =========================


class CapturadorFrames:
    def __init__(self, fuente, stop_event):
        self.fuente = fuente
        self.es_archivo_local = self._es_archivo_local(fuente)
        self.stop_event = stop_event
        self.local_stop_event = threading.Event()
        self.lock = threading.Lock()
        self.camara = None
        self.thread = None
        self.latest_frame = None
        self.sequence = 0
        self.error = None
        self.fps = 15.0

    @staticmethod
    def _es_archivo_local(fuente):
        if not isinstance(fuente, (str, Path)):
            return False

        fuente_normalizada = str(fuente).lower()
        return not fuente_normalizada.startswith(
            ("rtsp://", "rtmp://", "http://", "https://")
        )

    def start(self):
        self._abrir_camara()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def _abrir_camara(self):
        if self.es_archivo_local:
            ruta_video = Path(self.fuente).expanduser()
            if not ruta_video.is_absolute():
                ruta_video = Path(__file__).resolve().parent / ruta_video
            if not ruta_video.is_file():
                raise RuntimeError(
                    f"No existe el archivo de video: {ruta_video}"
                )
            self.camara = cv2.VideoCapture(str(ruta_video), cv2.CAP_FFMPEG)
        elif isinstance(self.fuente, str):
            os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"
            self.camara = cv2.VideoCapture(
                self.fuente,
                cv2.CAP_FFMPEG,
                [
                    cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 5000,
                    cv2.CAP_PROP_READ_TIMEOUT_MSEC, 2000,
                ]
            )
        else:
            self.camara = cv2.VideoCapture(self.fuente, cv2.CAP_DSHOW)
            self.camara.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
            self.camara.set(cv2.CAP_PROP_FPS, 15)
            self.camara.set(cv2.CAP_PROP_FRAME_WIDTH, ANCHO_CAMARA)
            self.camara.set(cv2.CAP_PROP_FRAME_HEIGHT, ALTO_CAMARA)

        self.camara.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        if not self.camara.isOpened():
            raise RuntimeError(f"No se pudo abrir la fuente de video: {self.fuente}")

        fps_camara = self.camara.get(cv2.CAP_PROP_FPS)
        if fps_camara > 0:
            self.fps = fps_camara

    def _run(self):
        intentos_reconexion = 0
        siguiente_frame = time.perf_counter()

        while not self.stop_event.is_set() and not self.local_stop_event.is_set():
            correcto, frame = self.camara.read()

            if not correcto:
                if self.es_archivo_local:
                    with self.lock:
                        self.error = "El video de prueba finalizo."
                    return

                intentos_reconexion += 1

                if self.camara is not None:
                    self.camara.release()

                if intentos_reconexion > MAX_INTENTOS_RECONEXION:
                    with self.lock:
                        self.error = "No se pudo leer la transmision de video."
                    return

                if self.stop_event.wait(INTERVALO_RECONEXION):
                    return

                try:
                    self._abrir_camara()
                except RuntimeError:
                    continue

                continue

            intentos_reconexion = 0

            with self.lock:
                self.latest_frame = frame
                self.sequence += 1

            if self.es_archivo_local:
                siguiente_frame += 1.0 / max(self.fps, 1.0)
                espera = siguiente_frame - time.perf_counter()
                if espera > 0:
                    self.stop_event.wait(espera)
                else:
                    siguiente_frame = time.perf_counter()

    def snapshot(self):
        with self.lock:
            frame = None if self.latest_frame is None else self.latest_frame.copy()
            return self.sequence, frame, self.error

    def current_sequence(self):
        with self.lock:
            return self.sequence

    def stop(self):
        self.local_stop_event.set()

        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2.5)

        if self.camara is not None:
            self.camara.release()

        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.0)


class MotorReconocimiento:
    def __init__(self):
        self.lock = threading.Lock()
        self.stop_event = threading.Event()
        self.thread = None
        self.running = False
        self.streaming = False
        self.latest_jpeg = None
        self.last_error = None
        self.last_event = "Detenido"
        self.detections = []
        self.references_count = 0
        self.resultados_dibujo = []

    def start(self):
        if self.thread and self.thread.is_alive():
            return

        self.stop_event.clear()
        with self.lock:
            self.running = True
            self.streaming = False
            self.last_error = None
            self.last_event = "Iniciando camara"
            self.latest_jpeg = crear_frame_mensaje("Iniciando camara...")
            self.detections = []
            self.resultados_dibujo = []

        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        with self.lock:
            self.running = False
            self.streaming = False
            self.latest_jpeg = crear_frame_mensaje("Presiona Iniciar en la interfaz")
            self.last_event = "Detenido"
            self.detections = []
            self.resultados_dibujo = []

        if self.thread and self.thread.is_alive() and threading.current_thread() != self.thread:
            self.thread.join(timeout=2.0)

    def snapshot(self):
        with self.lock:
            return {
                "running": self.running,
                "streaming": self.streaming,
                "last_error": self.last_error,
                "last_event": self.last_event,
                "detections": list(self.detections),
                "references_count": self.references_count,
                "has_frame": self.latest_jpeg is not None,
                "references_files": contar_galerias(CARPETA_REFERENCIAS),
                "pending_files": contar_galerias(CARPETA_PENDIENTES),
                "gallery_signature": firma_galerias(),
                "similarity_threshold": UMBRAL_SIMILITUD,
            }

    def get_frame(self):
        with self.lock:
            return self.latest_jpeg

    def _set_frame(self, frame):
        if self.stop_event.is_set():
            return

        correcto, buffer = cv2.imencode(
            ".jpg",
            frame,
            [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY]
        )

        if not correcto:
            return

        with self.lock:
            if self.stop_event.is_set():
                return
            self.latest_jpeg = buffer.tobytes()
            self.streaming = True

    def _run(self):
        modelo = None
        modelo_personas = None
        capturador = None
        thread_video = None

        try:
            with self.lock:
                self.running = True
                self.streaming = False
                self.last_error = None
                self.last_event = "Abriendo fuente de video"

            fuente_es_archivo = CapturadorFrames._es_archivo_local(CAMARA)
            if fuente_es_archivo:
                with self.lock:
                    self.last_event = "Cargando modelos antes del video"
                modelo = crear_modelo()
                if USAR_YOLO_PERSONAS:
                    modelo_personas = crear_modelo_personas()
                referencias = cargar_referencias(modelo)
                reconciliar_galerias_pendientes(referencias)

            capturador = CapturadorFrames(CAMARA, self.stop_event)
            capturador.start()
            thread_video = threading.Thread(
                target=self._publicar_video,
                args=(capturador,),
                daemon=True
            )
            thread_video.start()

            limite_espera = time.time() + 30.0
            while not self.stop_event.is_set():
                _, primer_frame, error_captura = capturador.snapshot()
                if error_captura:
                    raise RuntimeError(error_captura)
                if primer_frame is not None:
                    break
                if time.time() >= limite_espera:
                    raise RuntimeError("La fuente de video no entrego ningun frame.")
                self.stop_event.wait(0.05)

            if modelo is None:
                with self.lock:
                    self.last_event = "Cargando modelo"

                modelo = crear_modelo()
                if USAR_YOLO_PERSONAS:
                    modelo_personas = crear_modelo_personas()
                referencias = cargar_referencias(modelo)
                reconciliar_galerias_pendientes(referencias)

            estado_carpetas = obtener_estado_carpetas()
            ultima_revision_carpetas = time.time()

            Path(CARPETA_PENDIENTES).mkdir(exist_ok=True)

            candidatos_desconocidos = {}
            historial_reconocidos = {}
            historial_personas = {}
            asociaciones_rostro_persona = {}

            tracker = sv.ByteTrack(
                track_activation_threshold=0.25,
                lost_track_buffer=30,
                minimum_matching_threshold=0.8,
                frame_rate=capturador.fps,
                minimum_consecutive_frames=1
            )
            tracker_personas = sv.ByteTrack(
                track_activation_threshold=YOLO_CONFIANZA,
                lost_track_buffer=30,
                minimum_matching_threshold=0.8,
                frame_rate=max(
                    1,
                    round(capturador.fps / DETECTAR_PERSONAS_CADA_N_CICLOS)
                ),
                minimum_consecutive_frames=1
            )

            ultima_secuencia_detectada = capturador.current_sequence()
            contador_detecciones = RECONOCER_CADA_N_DETECCIONES - 1
            contador_personas = DETECTAR_PERSONAS_CADA_N_CICLOS - 1
            personas_seguidas = []

            with self.lock:
                self.last_event = "Fuente de video activa"
                self.references_count = len(referencias)

            while not self.stop_event.is_set():
                secuencia, frame, error_captura = capturador.snapshot()

                if error_captura:
                    raise RuntimeError(error_captura)

                if frame is None:
                    self.stop_event.wait(0.01)
                    continue

                ahora_revision = time.time()

                if ahora_revision - ultima_revision_carpetas >= INTERVALO_REVISION_CARPETAS:
                    nuevo_estado_carpetas = obtener_estado_carpetas()

                    if nuevo_estado_carpetas != estado_carpetas:
                        nuevas_referencias = cargar_referencias(
                            modelo,
                            referencias
                        )
                        reconciliar_galerias_pendientes(nuevas_referencias)
                        mapa_referencias = crear_mapa_referencias(
                            referencias,
                            nuevas_referencias
                        )
                        self._reconciliar_referencias_activas(
                            mapa_referencias,
                            historial_reconocidos,
                            historial_personas,
                            candidatos_desconocidos
                        )
                        referencias = nuevas_referencias
                        estado_carpetas = obtener_estado_carpetas()
                        contador_detecciones = max(
                            contador_detecciones,
                            RECONOCER_CADA_N_DETECCIONES_SIN_IDENTIDAD - 1
                        )

                        with self.lock:
                            self.references_count = len(referencias)
                            self.last_event = "Referencias actualizadas"

                    ultima_revision_carpetas = ahora_revision

                if secuencia - ultima_secuencia_detectada < DETECTAR_CADA_N_FRAMES:
                    self.stop_event.wait(0.01)
                    continue

                contador_detecciones += 1

                if modelo_personas is not None:
                    contador_personas += 1
                    if contador_personas >= DETECTAR_PERSONAS_CADA_N_CICLOS:
                        personas_seguidas = self._detectar_personas(
                            frame,
                            modelo_personas,
                            tracker_personas
                        )
                        contador_personas = 0

                    self._actualizar_personas_visibles(
                        personas_seguidas,
                        historial_personas,
                        asociaciones_rostro_persona,
                        candidatos_desconocidos
                    )

                hay_persona_sin_identidad = any(
                    "nombre" not in historial_personas.get(
                        persona["tracker_id"],
                        {}
                    )
                    for persona in personas_seguidas
                )
                intervalo_reconocimiento = (
                    RECONOCER_CADA_N_DETECCIONES_SIN_IDENTIDAD
                    if hay_persona_sin_identidad
                    else RECONOCER_CADA_N_DETECCIONES
                )
                realizar_reconocimiento = (
                    contador_detecciones >= intervalo_reconocimiento
                )

                resultados = self._analizar_frame(
                    frame,
                    modelo,
                    referencias,
                    tracker,
                    candidatos_desconocidos,
                    historial_reconocidos,
                    realizar_reconocimiento,
                    personas_seguidas,
                    historial_personas,
                    asociaciones_rostro_persona
                )

                if modelo_personas is not None:
                    resultados = (
                        self._crear_resultados_personas(
                            personas_seguidas,
                            resultados,
                            historial_personas
                        )
                        + resultados
                    )

                if realizar_reconocimiento:
                    contador_detecciones = 0

                limpiar_candidatos_desconocidos(candidatos_desconocidos)
                limpiar_historial_reconocidos(historial_reconocidos)
                limpiar_tracks_antiguos(
                    historial_personas,
                    TOLERANCIA_IDENTIDAD_CORPORAL_SEGUNDOS
                )
                limpiar_tracks_antiguos(
                    asociaciones_rostro_persona,
                    TOLERANCIA_IDENTIDAD_CORPORAL_SEGUNDOS
                )

                with self.lock:
                    self.resultados_dibujo = resultados
                    self.detections = [
                        {"texto": texto, "color": color}
                        for _, _, _, _, texto, color in resultados
                    ]

                # Descarta los frames recibidos mientras el detector estaba ocupado.
                ultima_secuencia_detectada = capturador.current_sequence()

        except Exception as error:
            with self.lock:
                self.last_error = str(error)
                self.last_event = "Error"
            print(f"Error en motor de reconocimiento: {error}")
        finally:
            self.stop_event.set()

            if capturador is not None:
                capturador.stop()

            if thread_video and thread_video.is_alive():
                thread_video.join(timeout=1.0)

            with self.lock:
                self.running = False
                self.streaming = False
                self.latest_jpeg = crear_frame_mensaje("Presiona Iniciar en la interfaz")
                self.last_event = "Detenido"
                self.detections = []
                self.resultados_dibujo = []

    def _publicar_video(self, capturador):
        intervalo = 1.0 / FPS_VIDEO_WEB

        while not self.stop_event.is_set():
            inicio = time.perf_counter()
            _, frame, error_captura = capturador.snapshot()

            if error_captura:
                return

            if frame is not None:
                with self.lock:
                    resultados = list(self.resultados_dibujo)

                self._dibujar_resultados(frame, resultados)
                frame = self._ajustar_frame_video_web(frame)
                self._set_frame(frame)

            restante = intervalo - (time.perf_counter() - inicio)
            if restante > 0:
                self.stop_event.wait(restante)

    @staticmethod
    def _ajustar_frame_video_web(frame):
        alto, ancho = frame.shape[:2]
        factor = min(
            1.0,
            ANCHO_MAX_VIDEO_WEB / ancho,
            ALTO_MAX_VIDEO_WEB / alto
        )

        if factor >= 1.0:
            return frame

        nuevo_ancho = max(1, round(ancho * factor))
        nuevo_alto = max(1, round(alto * factor))
        return cv2.resize(
            frame,
            (nuevo_ancho, nuevo_alto),
            interpolation=cv2.INTER_AREA
        )

    def _analizar_frame(
        self,
        frame,
        modelo,
        referencias,
        tracker,
        candidatos_desconocidos,
        historial_reconocidos,
        realizar_reconocimiento,
        personas_seguidas,
        historial_personas,
        asociaciones_rostro_persona
    ):
        alto_original, ancho_original = frame.shape[:2]
        factor_escala = min(
            ANCHO_ANALISIS / ancho_original,
            ALTO_ANALISIS / alto_original
        )
        ancho_ia = max(1, round(ancho_original * factor_escala))
        alto_ia = max(1, round(alto_original * factor_escala))
        frame_ia = cv2.resize(frame, (ancho_ia, alto_ia))
        resultados_actuales = []

        cajas_originales = []
        confianzas_originales = []
        analisis_rostros = []

        escala_x = ancho_original / ancho_ia
        escala_y = alto_original / alto_ia

        bboxes, puntos_clave = modelo.det_model.detect(
            frame_ia,
            max_num=0,
            metric="default"
        )

        recortes = []
        indices_analizables = []

        for indice, bbox_detectado in enumerate(bboxes):
            x1, y1, x2, y2 = bbox_detectado[:4].astype(int)

            x1 = int(x1 * escala_x)
            x2 = int(x2 * escala_x)
            y1 = int(y1 * escala_y)
            y2 = int(y2 * escala_y)

            bbox_actual = [x1, y1, x2, y2]
            puntos = (
                puntos_clave[indice]
                if puntos_clave is not None and indice < len(puntos_clave)
                else None
            )
            puntos_originales = None
            if puntos is not None:
                puntos_originales = np.asarray(puntos, dtype=np.float32).copy()
                puntos_originales[:, 0] *= escala_x
                puntos_originales[:, 1] *= escala_y

            evaluable, motivo_no_evaluable = evaluar_calidad_rostro(
                bbox_actual,
                puntos_originales,
                float(bbox_detectado[4])
            )

            cajas_originales.append(bbox_actual)
            confianzas_originales.append(float(bbox_detectado[4]))
            analisis_rostros.append({
                "bbox": bbox_actual,
                "embedding": None,
                "nombre": "Desconocido",
                "similitud": -1.0,
                "tipo": None,
                "reconocido": False,
                "evaluable": evaluable,
                "motivo_no_evaluable": motivo_no_evaluable,
                "reconocimiento_ejecutado": realizar_reconocimiento
            })

            if (
                realizar_reconocimiento
                and evaluable
                and puntos_originales is not None
            ):
                recortes.append(
                    face_align.norm_crop(
                        frame,
                        landmark=puntos_originales,
                        image_size=112
                    )
                )
                indices_analizables.append(indice)

        if recortes:
            embeddings = modelo.models["recognition"].get_feat(recortes)

            for indice, embedding_detectado in zip(
                indices_analizables,
                embeddings
            ):
                embedding_actual = normalizar_vector(embedding_detectado)
                nombre, similitud, tipo, reconocido = comparar_con_referencias(
                    embedding_actual,
                    referencias
                )
                analisis_rostros[indice].update({
                    "embedding": embedding_actual,
                    "nombre": nombre,
                    "similitud": similitud,
                    "tipo": tipo,
                    "reconocido": reconocido
                })

        if cajas_originales:
            detections = sv.Detections(
                xyxy=np.array(cajas_originales, dtype=np.float32),
                confidence=np.array(confianzas_originales, dtype=np.float32),
                class_id=np.zeros(len(cajas_originales), dtype=int)
            )
        else:
            detections = sv.Detections.empty()

        detections = tracker.update_with_detections(detections)

        if detections.tracker_id is None:
            return resultados_actuales

        detecciones_rostros = [
            (box, int(tracker_id))
            for box, tracker_id in zip(
                detections.xyxy,
                detections.tracker_id
            )
        ]
        rostros_visibles = {
            tracker_id
            for _, tracker_id in detecciones_rostros
        }
        detecciones_rostros.sort(
            key=lambda deteccion: (
                deteccion[1] not in asociaciones_rostro_persona,
                deteccion[1]
            )
        )
        personas_asignadas = set()

        for box, tracker_id in detecciones_rostros:
            x1, y1, x2, y2 = box.astype(int)

            mejor_dato = None
            mejor_iou = 0.0

            for dato_rostro in analisis_rostros:
                iou_actual = calcular_iou(box, dato_rostro["bbox"])

                if iou_actual > mejor_iou:
                    mejor_iou = iou_actual
                    mejor_dato = dato_rostro

            persona = self._buscar_persona_para_rostro(
                box,
                personas_seguidas,
                asociaciones_rostro_persona.get(tracker_id, {}).get("persona_id"),
                personas_asignadas
            )
            persona_id = persona["tracker_id"] if persona is not None else None
            clave_candidato = clave_candidato_desconocido(
                tracker_id,
                persona_id
            )

            if persona_id is not None:
                personas_asignadas.add(persona_id)
                asociaciones_rostro_persona[tracker_id] = {
                    "persona_id": persona_id,
                    "ultimo_visto": time.time()
                }
                if mejor_dato is not None and mejor_dato["reconocido"]:
                    rostros_revocados = self._registrar_identidad_persona(
                        persona_id,
                        mejor_dato,
                        historial_personas,
                        tracker_id
                    )
                    for rostro_id in rostros_revocados:
                        historial_reconocidos.pop(rostro_id, None)
                        eliminar_candidato_desconocido(
                            candidatos_desconocidos,
                            tracker_id=rostro_id
                        )

                identidad_corporal = historial_personas.get(persona_id)
                if identidad_corporal is not None and "nombre" in identidad_corporal:
                    identidad_suspendida = self._actualizar_contradiccion_identidad(
                        identidad_corporal,
                        mejor_dato,
                        referencias
                    )
                    if identidad_suspendida:
                        rostros_liberados = self._revocar_identidad_persona(
                            identidad_corporal
                        )
                        rostros_liberados.add(tracker_id)
                        for rostro_id in rostros_liberados:
                            historial_reconocidos.pop(rostro_id, None)
                            eliminar_candidato_desconocido(
                                candidatos_desconocidos,
                                tracker_id=rostro_id
                            )
                        eliminar_candidato_desconocido(
                            candidatos_desconocidos,
                            persona_id=persona_id
                        )
                    else:
                        if (
                            identidad_corporal["tipo"] == "pendiente"
                            and mejor_dato is not None
                            and mejor_dato.get("embedding") is not None
                        ):
                            agregar_muestra_a_galeria(
                                frame,
                                tuple(box.astype(int)),
                                identidad_corporal["nombre"],
                                mejor_dato["embedding"],
                                referencias
                            )

                        identidad_corporal.setdefault(
                            "rostros_asociados",
                            set()
                        ).add(tracker_id)
                        bbox_actual = tuple(box.astype(int))
                        historial_reconocidos[tracker_id] = {
                            "nombre": identidad_corporal["nombre"],
                            "similitud": identidad_corporal["similitud"],
                            "tipo": identidad_corporal["tipo"],
                            "ultimo_visto": time.time(),
                            "embedding": identidad_corporal["embedding"].copy(),
                            "bbox": bbox_actual
                        }
                        eliminar_candidato_desconocido(
                            candidatos_desconocidos,
                            tracker_id,
                            persona_id
                        )
                        color = (
                            (0, 255, 0)
                            if identidad_corporal["tipo"] == "oficial"
                            else (0, 255, 255)
                        )
                        texto = (
                            f"ID {tracker_id} | {identidad_corporal['nombre']} "
                            f"| identidad corporal"
                        )
                        resultados_actuales.append(
                            (x1, y1, x2, y2, texto, color)
                        )
                        continue

                if mejor_dato is not None and mejor_dato["reconocido"]:
                    nombre_candidato = mejor_dato["nombre"]
                    pertenece_a_otra = any(
                        otro_id != persona_id
                        and datos.get("nombre") == nombre_candidato
                        for otro_id, datos in historial_personas.items()
                    )
                    estado = (
                        "coincidencia ambigua"
                        if pertenece_a_otra
                        else "identidad por confirmar"
                    )
                    texto = f"ID {tracker_id} | {nombre_candidato} | {estado}"
                    resultados_actuales.append(
                        (x1, y1, x2, y2, texto, (160, 160, 160))
                    )
                    continue

            if mejor_dato is None or mejor_iou <= 0.3:
                if tracker_id in historial_reconocidos:
                    historial = historial_reconocidos[tracker_id]
                    color = (0, 255, 0) if historial["tipo"] == "oficial" else (0, 255, 255)
                    texto = f"ID {tracker_id} | {historial['nombre']} | {historial['similitud']:.2f}"
                else:
                    color = (0, 0, 255)
                    texto = f"ID {tracker_id} | Sin match"

                resultados_actuales.append((x1, y1, x2, y2, texto, color))
                continue

            if not mejor_dato["evaluable"]:
                bbox_actual = tuple(mejor_dato["bbox"])
                historial = historial_reconocidos.get(tracker_id)

                if historial is None:
                    historial = self._buscar_identidad_por_posicion(
                        tracker_id,
                        bbox_actual,
                        historial_reconocidos
                    )

                    if historial is not None:
                        historial_reconocidos[tracker_id] = {
                            **historial,
                            "ultimo_visto": time.time(),
                            "bbox": bbox_actual
                        }

                if historial is not None:
                    eliminar_candidato_desconocido(
                        candidatos_desconocidos,
                        tracker_id,
                        persona_id
                    )
                    historial["ultimo_visto"] = time.time()
                    historial["bbox"] = bbox_actual
                    color = (0, 180, 255)
                    texto = (
                        f"ID {tracker_id} | {historial['nombre']} | "
                        f"{mejor_dato['motivo_no_evaluable']}"
                    )
                else:
                    candidato = candidatos_desconocidos.get(clave_candidato)
                    if candidato is not None:
                        candidato["ultimo_visto"] = time.time()
                        candidato["bbox"] = bbox_actual
                    color = (160, 160, 160)
                    texto = (
                        f"ID {tracker_id} | No evaluable | "
                        f"{mejor_dato['motivo_no_evaluable']}"
                    )

                resultados_actuales.append((x1, y1, x2, y2, texto, color))
                continue

            if not mejor_dato["reconocimiento_ejecutado"]:
                bbox_actual = tuple(mejor_dato["bbox"])
                historial = historial_reconocidos.get(tracker_id)

                if historial is None:
                    historial = self._buscar_identidad_por_posicion(
                        tracker_id,
                        bbox_actual,
                        historial_reconocidos
                    )

                    if historial is not None:
                        historial_reconocidos[tracker_id] = {
                            **historial,
                            "ultimo_visto": time.time(),
                            "bbox": bbox_actual
                        }

                if historial is not None:
                    historial["ultimo_visto"] = time.time()
                    historial["bbox"] = bbox_actual
                    eliminar_candidato_desconocido(
                        candidatos_desconocidos,
                        tracker_id,
                        persona_id
                    )
                    color = (
                        (0, 255, 0)
                        if historial["tipo"] == "oficial"
                        else (0, 255, 255)
                    )
                    texto = f"ID {tracker_id} | {historial['nombre']} | seguimiento"
                else:
                    candidato = candidatos_desconocidos.get(clave_candidato)
                    if candidato is not None:
                        ahora = time.time()
                        area_rostro = max(0, x2 - x1) * max(0, y2 - y1)
                        candidato["ultimo_visto"] = ahora
                        candidato["bbox"] = bbox_actual

                        tiempo_visible = ahora - candidato["inicio"]
                        texto = (
                            f"ID {tracker_id} | Desconocido en seguimiento... "
                            f"{tiempo_visible:.1f}s"
                        )
                    else:
                        texto = f"ID {tracker_id} | Rostro detectado"
                    color = (160, 160, 160)

                resultados_actuales.append((x1, y1, x2, y2, texto, color))
                continue

            nombre = mejor_dato["nombre"]
            similitud = mejor_dato["similitud"]
            tipo = mejor_dato["tipo"]
            reconocido = mejor_dato["reconocido"]
            embedding_actual = mejor_dato["embedding"]
            bbox_actual = tuple(mejor_dato["bbox"])

            historial_actual = historial_reconocidos.get(tracker_id)
            if (
                reconocido
                and historial_actual is not None
                and nombre != historial_actual["nombre"]
                and time.time() - historial_actual["ultimo_visto"]
                <= TOLERANCIA_OCLUSION_SEGUNDOS
            ):
                historial_actual["ultimo_visto"] = time.time()
                historial_actual["bbox"] = bbox_actual
                eliminar_candidato_desconocido(
                    candidatos_desconocidos,
                    tracker_id,
                    persona_id
                )
                color = (
                    (0, 255, 0)
                    if historial_actual["tipo"] == "oficial"
                    else (0, 255, 255)
                )
                texto = (
                    f"ID {tracker_id} | {historial_actual['nombre']} "
                    f"| identidad estable"
                )
                resultados_actuales.append((x1, y1, x2, y2, texto, color))
                continue

            if reconocido:
                identidad_ya_asignada = any(
                    datos.get("nombre") == nombre
                    and time.time() - datos.get("ultimo_visto", 0)
                    <= TOLERANCIA_IDENTIDAD_CORPORAL_SEGUNDOS
                    for datos in historial_personas.values()
                )
                if persona_id is None and identidad_ya_asignada:
                    resultados_actuales.append((
                        x1,
                        y1,
                        x2,
                        y2,
                        f"ID {tracker_id} | {nombre} | coincidencia ambigua",
                        (160, 160, 160)
                    ))
                    eliminar_candidato_desconocido(
                        candidatos_desconocidos,
                        tracker_id,
                        persona_id
                    )
                    continue

                if tipo == "pendiente":
                    agregar_muestra_a_galeria(
                        frame,
                        bbox_actual,
                        nombre,
                        embedding_actual,
                        referencias
                    )

                historial_reconocidos[tracker_id] = {
                    "nombre": nombre,
                    "similitud": similitud,
                    "tipo": tipo,
                    "ultimo_visto": time.time(),
                    "embedding": embedding_actual.copy(),
                    "bbox": bbox_actual
                }
                eliminar_candidato_desconocido(
                    candidatos_desconocidos,
                    tracker_id,
                    persona_id
                )

                if tipo == "oficial":
                    color = (0, 255, 0)
                    texto = f"ID {tracker_id} | {nombre} | {similitud:.2f}"
                else:
                    color = (0, 255, 255)
                    texto = f"ID {tracker_id} | Pendiente: {nombre} | {similitud:.2f}"
            else:
                resultado = self._manejar_desconocido(
                    frame,
                    modelo,
                    tracker_id,
                    box,
                    nombre,
                    similitud,
                    embedding_actual,
                    bbox_actual,
                    referencias,
                    candidatos_desconocidos,
                    historial_reconocidos,
                    persona_id,
                    historial_personas,
                    rostros_visibles
                )
                color, texto = resultado

            resultados_actuales.append((x1, y1, x2, y2, texto, color))

        return resultados_actuales

    @staticmethod
    def _detectar_personas(frame, modelo_personas, tracker_personas):
        resultado_yolo = modelo_personas.predict(
            frame,
            classes=[0],
            conf=YOLO_CONFIANZA,
            imgsz=YOLO_IMGSZ,
            device="cpu",
            verbose=False
        )[0]

        if resultado_yolo.boxes is None or len(resultado_yolo.boxes) == 0:
            detecciones = sv.Detections.empty()
        else:
            detecciones = sv.Detections(
                xyxy=resultado_yolo.boxes.xyxy.cpu().numpy().astype(np.float32),
                confidence=(
                    resultado_yolo.boxes.conf.cpu().numpy().astype(np.float32)
                ),
                class_id=np.zeros(len(resultado_yolo.boxes), dtype=int)
            )

        detecciones = tracker_personas.update_with_detections(detecciones)
        if detecciones.tracker_id is None:
            return []

        return [
            {
                "bbox": tuple(caja.astype(int)),
                "tracker_id": int(tracker_id)
            }
            for caja, tracker_id in zip(
                detecciones.xyxy,
                detecciones.tracker_id
            )
        ]

    @staticmethod
    def _actualizar_personas_visibles(
        personas,
        historial_personas,
        asociaciones_rostro_persona,
        candidatos_desconocidos
    ):
        ahora = time.time()
        ids_visibles = {persona["tracker_id"] for persona in personas}

        for persona in personas:
            persona_id = persona["tracker_id"]
            datos = historial_personas.get(persona_id)

            if datos is None or "nombre" not in datos:
                candidatas = []
                for id_anterior, datos_anteriores in historial_personas.items():
                    tiene_continuidad = (
                        "nombre" in datos_anteriores
                        or (
                            ("persona", int(id_anterior))
                            in candidatos_desconocidos
                        )
                    )
                    if (
                        id_anterior == persona_id
                        or id_anterior in ids_visibles
                        or not tiene_continuidad
                        or ahora - datos_anteriores.get("ultimo_visto", 0)
                        > TOLERANCIA_IDENTIDAD_CORPORAL_SEGUNDOS
                    ):
                        continue

                    iou = calcular_iou(
                        persona["bbox"],
                        datos_anteriores.get("bbox", (0, 0, 0, 0))
                    )
                    if iou >= MIN_IOU_REASOCIACION_CUERPO:
                        candidatas.append(
                            (iou, id_anterior, datos_anteriores)
                        )

                if candidatas:
                    _, id_anterior, datos_anteriores = max(
                        candidatas,
                        key=lambda candidata: candidata[0]
                    )
                    historial_personas[persona_id] = datos_anteriores
                    historial_personas.pop(id_anterior, None)
                    for asociacion in asociaciones_rostro_persona.values():
                        if asociacion.get("persona_id") == id_anterior:
                            asociacion["persona_id"] = persona_id
                    clave_anterior = ("persona", int(id_anterior))
                    clave_nueva = ("persona", int(persona_id))
                    if (
                        clave_anterior in candidatos_desconocidos
                        and clave_nueva not in candidatos_desconocidos
                    ):
                        candidatos_desconocidos[clave_nueva] = (
                            candidatos_desconocidos.pop(clave_anterior)
                        )
                    datos = datos_anteriores

            if datos is None:
                datos = historial_personas.setdefault(persona_id, {})

            datos["ultimo_visto"] = ahora
            datos["bbox"] = persona["bbox"]
            candidato = candidatos_desconocidos.get(
                ("persona", int(persona_id))
            )
            if candidato is not None:
                candidato["ultimo_visto"] = ahora

    @staticmethod
    def _reconciliar_referencias_activas(
        mapa_referencias,
        historial_reconocidos,
        historial_personas,
        candidatos_desconocidos
    ):
        rostros_revocados = set()

        for persona in historial_personas.values():
            nombre = persona.get("nombre")
            tipo = persona.get("tipo")
            if nombre is not None and tipo is not None:
                nueva_identidad = mapa_referencias.get((nombre, tipo))
                if nueva_identidad is None:
                    rostros_revocados.update(
                        MotorReconocimiento._revocar_identidad_persona(persona)
                    )
                else:
                    persona["nombre"], persona["tipo"] = nueva_identidad

            for campo in ("identidad_candidata", "datos_cambio"):
                candidata = persona.get(campo)
                if candidata is None:
                    continue
                nueva_identidad = mapa_referencias.get(
                    (candidata.get("nombre"), candidata.get("tipo"))
                )
                if nueva_identidad is None:
                    persona.pop(campo, None)
                    if campo == "datos_cambio":
                        persona["cambio_candidato"] = None
                        persona["confirmaciones_cambio"] = 0
                else:
                    candidata["nombre"], candidata["tipo"] = nueva_identidad
                    if campo == "datos_cambio":
                        persona["cambio_candidato"] = candidata["nombre"]

        for rostro_id, historial in list(historial_reconocidos.items()):
            nueva_identidad = mapa_referencias.get(
                (historial.get("nombre"), historial.get("tipo"))
            )
            if nueva_identidad is None or rostro_id in rostros_revocados:
                historial_reconocidos.pop(rostro_id, None)
                eliminar_candidato_desconocido(
                    candidatos_desconocidos,
                    tracker_id=rostro_id
                )
                continue
            historial["nombre"], historial["tipo"] = nueva_identidad

    @staticmethod
    def _buscar_persona_para_rostro(
        caja_rostro,
        personas,
        persona_preferida_id=None,
        personas_excluidas=None
    ):
        rx1, ry1, rx2, ry2 = caja_rostro
        centro_x = (rx1 + rx2) / 2.0
        centro_y = (ry1 + ry2) / 2.0
        area_rostro = max(1.0, (rx2 - rx1) * (ry2 - ry1))
        candidatas = []
        personas_excluidas = personas_excluidas or set()

        for persona in personas:
            if persona["tracker_id"] in personas_excluidas:
                continue

            px1, py1, px2, py2 = persona["bbox"]
            ancho = max(1, px2 - px1)
            alto = max(1, py2 - py1)
            limite_cabeza_y = py1 + alto * LIMITE_VERTICAL_CABEZA_EN_CUERPO
            if not (
                px1 <= centro_x <= px2
                and py1 <= centro_y <= limite_cabeza_y
            ):
                continue

            inter_x1 = max(rx1, px1)
            inter_y1 = max(ry1, py1)
            inter_x2 = min(rx2, px2)
            inter_y2 = min(ry2, py2)
            area_interseccion = (
                max(0.0, inter_x2 - inter_x1)
                * max(0.0, inter_y2 - inter_y1)
            )
            proporcion_dentro = area_interseccion / area_rostro
            if proporcion_dentro < MIN_PROPORCION_ROSTRO_DENTRO_CUERPO:
                continue

            centro_cabeza_x = px1 + ancho / 2.0
            centro_cabeza_y = py1 + alto * 0.20
            distancia = (
                abs(centro_x - centro_cabeza_x) / ancho
                + abs(centro_y - centro_cabeza_y) / alto
                + (1.0 - proporcion_dentro) * 0.5
            )
            candidatas.append((distancia, persona))

        if not candidatas:
            return None

        mejor_distancia, mejor_persona = min(
            candidatas,
            key=lambda candidata: candidata[0]
        )
        preferida = next(
            (
                candidata
                for candidata in candidatas
                if candidata[1]["tracker_id"] == persona_preferida_id
            ),
            None
        )
        if (
            preferida is not None
            and mejor_persona["tracker_id"] != persona_preferida_id
            and mejor_distancia + MARGEN_CAMBIO_ASOCIACION_ROSTRO_CUERPO
            >= preferida[0]
        ):
            return preferida[1]

        return mejor_persona

    @staticmethod
    def _registrar_identidad_persona(
        persona_id,
        identidad_rostro,
        historial_personas,
        rostro_tracker_id
    ):
        if not identidad_rostro.get("reconocido", True):
            return set()

        nombre = identidad_rostro.get("nombre")
        embedding = identidad_rostro.get("embedding")
        tipo = identidad_rostro.get("tipo")
        similitud = float(identidad_rostro.get("similitud", -1.0))
        if not nombre or embedding is None or tipo is None:
            return set()

        persona = historial_personas.setdefault(persona_id, {})
        if "nombre" not in persona:
            if similitud < MIN_SIMILITUD_IDENTIDAD_INICIAL:
                persona.pop("identidad_candidata", None)
                return set()

            candidata = persona.get("identidad_candidata")
            if candidata is not None and candidata["nombre"] == nombre:
                candidata["confirmaciones"] += 1
                if similitud >= candidata["similitud"]:
                    candidata.update({
                        "similitud": similitud,
                        "tipo": tipo,
                        "embedding": embedding.copy()
                    })
            else:
                candidata = {
                    "nombre": nombre,
                    "similitud": similitud,
                    "tipo": tipo,
                    "embedding": embedding.copy(),
                    "confirmaciones": 1
                }
                persona["identidad_candidata"] = candidata

            if candidata["confirmaciones"] < MIN_CONFIRMACIONES_IDENTIDAD_INICIAL:
                return set()

            rostros_revocados = MotorReconocimiento._resolver_propietarios_identidad(
                persona_id,
                candidata,
                historial_personas
            )
            if rostros_revocados is None:
                return set()

            MotorReconocimiento._asignar_identidad_persona(
                persona,
                candidata,
                rostro_tracker_id
            )
            return rostros_revocados

        if nombre == persona["nombre"]:
            if similitud >= persona["similitud"]:
                persona["similitud"] = similitud
                persona["embedding"] = embedding.copy()
                persona["tipo"] = tipo
            persona["ultima_evidencia_facial"] = time.time()
            persona.setdefault("rostros_asociados", set()).add(rostro_tracker_id)
            persona["cambio_candidato"] = None
            persona["confirmaciones_cambio"] = 0
            return set()

        if similitud < MIN_SIMILITUD_CAMBIO_IDENTIDAD:
            persona["cambio_candidato"] = None
            persona["confirmaciones_cambio"] = 0
            return set()

        if persona.get("cambio_candidato") == nombre:
            persona["confirmaciones_cambio"] += 1
            if similitud >= persona["datos_cambio"]["similitud"]:
                persona["datos_cambio"].update({
                    "similitud": similitud,
                    "tipo": tipo,
                    "embedding": embedding.copy()
                })
        else:
            persona["cambio_candidato"] = nombre
            persona["confirmaciones_cambio"] = 1
            persona["datos_cambio"] = {
                "nombre": nombre,
                "similitud": similitud,
                "tipo": tipo,
                "embedding": embedding.copy()
            }

        if persona["confirmaciones_cambio"] < MIN_CONFIRMACIONES_CAMBIO_IDENTIDAD:
            return set()

        nueva_identidad = persona["datos_cambio"]
        rostros_revocados = MotorReconocimiento._resolver_propietarios_identidad(
            persona_id,
            nueva_identidad,
            historial_personas
        )
        if rostros_revocados is None:
            return set()

        rostros_revocados.update(
            MotorReconocimiento._revocar_identidad_persona(persona)
        )
        MotorReconocimiento._asignar_identidad_persona(
            persona,
            nueva_identidad,
            rostro_tracker_id
        )
        return rostros_revocados

    @staticmethod
    def _actualizar_contradiccion_identidad(
        persona,
        dato_rostro,
        referencias
    ):
        if (
            "nombre" not in persona
            or dato_rostro is None
            or not dato_rostro.get("reconocimiento_ejecutado")
            or not dato_rostro.get("evaluable")
            or dato_rostro.get("embedding") is None
        ):
            return persona.get("identidad_suspendida", False)

        similitudes_propias = [
            float(np.dot(dato_rostro["embedding"], referencia["embedding"]))
            for referencia in referencias
            if referencia["nombre"] == persona["nombre"]
            and referencia["tipo"] == persona["tipo"]
        ]
        mejor_similitud_propia = (
            max(similitudes_propias)
            if similitudes_propias
            else -1.0
        )
        otra_identidad_fuerte = (
            dato_rostro.get("reconocido", False)
            and dato_rostro.get("nombre") != persona["nombre"]
            and float(dato_rostro.get("similitud", -1.0))
            >= MIN_SIMILITUD_OTRA_IDENTIDAD_FUERTE
        )
        identidad_incompatible = (
            mejor_similitud_propia < MAX_SIMILITUD_IDENTIDAD_INCOMPATIBLE
            or otra_identidad_fuerte
        )
        confirma_identidad_actual = (
            dato_rostro.get("reconocido", False)
            and dato_rostro.get("nombre") == persona["nombre"]
        )

        if confirma_identidad_actual:
            persona["identidad_suspendida"] = False
            persona["confirmaciones_contradiccion"] = 0
            return False

        if not identidad_incompatible:
            persona["confirmaciones_contradiccion"] = 0
            return persona.get("identidad_suspendida", False)

        persona["confirmaciones_contradiccion"] = (
            persona.get("confirmaciones_contradiccion", 0) + 1
        )
        if (
            persona["confirmaciones_contradiccion"]
            >= MIN_CONFIRMACIONES_CONTRADICCION_IDENTIDAD
        ):
            persona["identidad_suspendida"] = True

        return persona.get("identidad_suspendida", False)

    @staticmethod
    def _resolver_propietarios_identidad(
        persona_id,
        nueva_identidad,
        historial_personas
    ):
        ahora = time.time()
        propietarios = [
            datos
            for otro_id, datos in historial_personas.items()
            if otro_id != persona_id
            and datos.get("nombre") == nueva_identidad["nombre"]
        ]
        rostros_revocados = set()

        for propietario in propietarios:
            propietario_activo = (
                ahora - propietario.get("ultimo_visto", 0)
                <= TOLERANCIA_IDENTIDAD_CORPORAL_SEGUNDOS
            )
            evidencia_mas_fuerte = (
                nueva_identidad["similitud"]
                >= propietario.get("similitud", -1.0)
                + MARGEN_SIMILITUD_TRASPASO_IDENTIDAD
            )
            evidencia_suficiente = (
                nueva_identidad["similitud"]
                >= MIN_SIMILITUD_TRASPASO_IDENTIDAD
            )
            if not evidencia_suficiente:
                return None

            if propietario_activo and not evidencia_mas_fuerte:
                return None

        for propietario in propietarios:
            rostros_revocados.update(
                MotorReconocimiento._revocar_identidad_persona(propietario)
            )

        return rostros_revocados

    @staticmethod
    def _revocar_identidad_persona(persona):
        rostros_asociados = set(persona.get("rostros_asociados", set()))
        for campo in (
            "nombre",
            "similitud",
            "tipo",
            "embedding",
            "ultima_evidencia_facial",
            "rostros_asociados",
            "identidad_candidata",
            "cambio_candidato",
            "confirmaciones_cambio",
            "datos_cambio",
            "identidad_suspendida",
            "confirmaciones_contradiccion"
        ):
            persona.pop(campo, None)
        return rostros_asociados

    @staticmethod
    def _asignar_identidad_persona(persona, identidad, rostro_tracker_id):
        persona.update({
            "nombre": identidad["nombre"],
            "similitud": identidad["similitud"],
            "tipo": identidad["tipo"],
            "embedding": identidad["embedding"].copy(),
            "ultima_evidencia_facial": time.time(),
            "rostros_asociados": {rostro_tracker_id},
            "cambio_candidato": None,
            "confirmaciones_cambio": 0,
            "identidad_suspendida": False,
            "confirmaciones_contradiccion": 0
        })
        persona.pop("identidad_candidata", None)
        persona.pop("datos_cambio", None)

    @staticmethod
    def _crear_resultados_personas(
        personas,
        resultados_rostros,
        historial_personas
    ):
        resultados = []

        for persona in personas:
            x1, y1, x2, y2 = persona["bbox"]
            tiene_rostro = False

            for rx1, ry1, rx2, ry2, _, _ in resultados_rostros:
                centro_x = (rx1 + rx2) / 2.0
                centro_y = (ry1 + ry2) / 2.0
                if x1 <= centro_x <= x2 and y1 <= centro_y <= y2:
                    tiene_rostro = True
                    break

            identidad = historial_personas.get(persona["tracker_id"], {})
            if identidad.get("identidad_suspendida"):
                estado = "identidad en verificacion"
                color = (160, 160, 160)
            elif "nombre" in identidad:
                estado = identidad["nombre"]
                color = (
                    (0, 255, 0)
                    if identidad["tipo"] == "oficial"
                    else (0, 255, 255)
                )
            else:
                estado = (
                    "rostro detectado"
                    if tiene_rostro
                    else "sin rostro visible"
                )
                color = (255, 140, 0)

            texto = f"Persona {persona['tracker_id']} | {estado}"
            resultados.append((x1, y1, x2, y2, texto, color))

        return resultados

    @staticmethod
    def _buscar_candidato_facial_reciente(
        tracker_id,
        bbox_actual,
        embedding_actual,
        candidatos_desconocidos,
        rostros_visibles
    ):
        ahora = time.time()
        mejor = None

        for clave, candidato in candidatos_desconocidos.items():
            if (
                not isinstance(clave, tuple)
                or len(clave) != 2
                or clave[0] != "rostro"
                or clave[1] == tracker_id
                or candidato.get("rostro_tracker_id") in rostros_visibles
                or ahora - candidato.get("ultimo_visto", 0)
                > TOLERANCIA_CANDIDATO_FACIAL_SEGUNDOS
            ):
                continue

            iou = calcular_iou(
                bbox_actual,
                candidato.get("bbox", (0, 0, 0, 0))
            )
            similitud = float(
                np.dot(
                    embedding_actual,
                    candidato.get(
                        "embedding_semilla",
                        candidato["mejor_embedding"]
                    )
                )
            )
            posicion_fuerte = (
                iou >= MIN_IOU_REASOCIACION_CANDIDATO_FACIAL_FUERTE
                and similitud >= 0.05
            )
            coincidencia_combinada = (
                iou >= MIN_IOU_REASOCIACION_CANDIDATO_FACIAL
                and similitud
                >= MIN_SIMILITUD_REASOCIACION_CANDIDATO_FACIAL
            )
            if not posicion_fuerte and not coincidencia_combinada:
                continue

            puntuacion = iou + max(0.0, similitud) * 0.5
            if mejor is None or puntuacion > mejor[0]:
                mejor = (puntuacion, clave, candidato)

        if mejor is None:
            return None

        _, clave_anterior, candidato = mejor
        candidatos_desconocidos.pop(clave_anterior, None)
        return candidato

    def _manejar_desconocido(
        self,
        frame,
        modelo,
        tracker_id,
        box,
        nombre,
        similitud,
        embedding_actual,
        bbox_actual,
        referencias,
        candidatos_desconocidos,
        historial_reconocidos,
        persona_id,
        historial_personas,
        rostros_visibles
    ):
        x1, y1, x2, y2 = box.astype(int)
        clave_rostro = clave_candidato_desconocido(tracker_id)
        clave_candidato = clave_candidato_desconocido(
            tracker_id,
            persona_id
        )

        if (
            persona_id is not None
            and clave_candidato not in candidatos_desconocidos
            and clave_rostro in candidatos_desconocidos
        ):
            candidatos_desconocidos[clave_candidato] = (
                candidatos_desconocidos.pop(clave_rostro)
            )
        elif (
            persona_id is None
            and clave_candidato not in candidatos_desconocidos
        ):
            candidato_reciente = self._buscar_candidato_facial_reciente(
                tracker_id,
                bbox_actual,
                embedding_actual,
                candidatos_desconocidos,
                rostros_visibles
            )
            if candidato_reciente is not None:
                candidatos_desconocidos[clave_candidato] = candidato_reciente

        if tracker_id in historial_reconocidos:
            historial = historial_reconocidos[tracker_id]
            tiempo_desde_reconocido = time.time() - historial["ultimo_visto"]
            parece_misma_persona = (
                nombre == historial["nombre"]
                and similitud >= MIN_SIMILITUD_POSIBLE_MISMA_PERSONA
            )

            if tiempo_desde_reconocido <= TOLERANCIA_OCLUSION_SEGUNDOS or parece_misma_persona:
                if historial["tipo"] == "pendiente":
                    agregar_muestra_a_galeria(
                        frame,
                        bbox_actual,
                        historial["nombre"],
                        embedding_actual,
                        referencias
                    )
                historial["ultimo_visto"] = time.time()
                historial["bbox"] = bbox_actual
                eliminar_candidato_desconocido(
                    candidatos_desconocidos,
                    tracker_id,
                    persona_id
                )
                texto = f"ID {tracker_id} | {historial['nombre']} | oclusion {similitud:.2f}"
                return (0, 180, 255), texto

        historial_reidentificado, similitud_reidentificacion = (
            self._buscar_identidad_reciente(
                tracker_id,
                embedding_actual,
                bbox_actual,
                historial_reconocidos
            )
        )

        if historial_reidentificado is not None:
            historial_reconocidos[tracker_id] = {
                **historial_reidentificado,
                "ultimo_visto": time.time(),
                "bbox": bbox_actual
            }
            eliminar_candidato_desconocido(
                candidatos_desconocidos,
                tracker_id,
                persona_id
            )
            texto = (
                f"ID {tracker_id} | {historial_reidentificado['nombre']} "
                f"| reidentificado {similitud_reidentificacion:.2f}"
            )
            return (0, 180, 255), texto

        ahora = time.time()
        ancho_rostro = x2 - x1
        alto_rostro = y2 - y1
        area_rostro = ancho_rostro * alto_rostro
        calidad_actual = calcular_calidad_muestra(
            recortar_muestra(frame, bbox_actual)
        )

        if (
            nombre != "Desconocido"
            and similitud >= MIN_SIMILITUD_EVITAR_GALERIA_DUPLICADA
        ):
            eliminar_candidato_desconocido(
                candidatos_desconocidos,
                tracker_id,
                persona_id
            )
            return (
                (160, 160, 160),
                f"ID {tracker_id} | Posible {nombre} | esperando mejor angulo"
            )

        if ancho_rostro < MIN_ANCHO_ROSTRO or alto_rostro < MIN_ALTO_ROSTRO:
            return (0, 0, 255), f"ID {tracker_id} | Desconocido | rostro muy pequeno"

        if clave_candidato not in candidatos_desconocidos:
            candidatos_desconocidos[clave_candidato] = {
                "inicio": ahora,
                "ultimo_visto": ahora,
                "muestras": 1,
                "rostro_tracker_id": tracker_id,
                "persona_id": persona_id,
                "bbox": bbox_actual,
                "mejor_frame": frame.copy(),
                "mejor_bbox": bbox_actual,
                "mejor_area": area_rostro,
                "mejor_calidad": calidad_actual,
                "mejor_embedding": embedding_actual.copy(),
                "embedding_semilla": embedding_actual.copy(),
                "confirmaciones_incompatibles": 0,
                "guardado": False,
                "ultima_captura": 0
            }
        else:
            candidato = candidatos_desconocidos[clave_candidato]
            similitud_semilla = float(
                np.dot(
                    embedding_actual,
                    candidato.get(
                        "embedding_semilla",
                        candidato["mejor_embedding"]
                    )
                )
            )
            if similitud_semilla < MIN_SIMILITUD_MUESTRA_CON_SEMILLA:
                candidato["confirmaciones_incompatibles"] = (
                    candidato.get("confirmaciones_incompatibles", 0) + 1
                )
                if candidato["confirmaciones_incompatibles"] < 2:
                    candidato["ultimo_visto"] = ahora
                    return (
                        (160, 160, 160),
                        f"ID {tracker_id} | Candidato corporal en verificacion"
                    )

                candidato.update({
                    "inicio": ahora,
                    "ultimo_visto": ahora,
                    "muestras": 1,
                    "rostro_tracker_id": tracker_id,
                    "persona_id": persona_id,
                    "bbox": bbox_actual,
                    "mejor_frame": frame.copy(),
                    "mejor_bbox": bbox_actual,
                    "mejor_area": area_rostro,
                    "mejor_calidad": calidad_actual,
                    "mejor_embedding": embedding_actual.copy(),
                    "embedding_semilla": embedding_actual.copy(),
                    "confirmaciones_incompatibles": 0,
                    "guardado": False,
                    "ultima_captura": 0
                })
                candidato = candidatos_desconocidos[clave_candidato]
            else:
                candidato["confirmaciones_incompatibles"] = 0
                candidato["ultimo_visto"] = ahora
                candidato["muestras"] += 1
                candidato["rostro_tracker_id"] = tracker_id
                candidato["persona_id"] = persona_id
                candidato["bbox"] = bbox_actual

                mejor_calidad = candidato.get("mejor_calidad", 0.0)
                if (
                    calidad_actual > mejor_calidad
                    or (
                        calidad_actual == mejor_calidad
                        and area_rostro > candidato["mejor_area"]
                    )
                ):
                    candidato["mejor_frame"] = frame.copy()
                    candidato["mejor_bbox"] = bbox_actual
                    candidato["mejor_area"] = area_rostro
                    candidato["mejor_calidad"] = calidad_actual
                    candidato["mejor_embedding"] = embedding_actual.copy()

        candidato = candidatos_desconocidos[clave_candidato]
        tiempo_visible = ahora - candidato["inicio"]
        texto = f"ID {tracker_id} | Desconocido analizando... {tiempo_visible:.1f}s"
        tiempo_confirmacion = (
            TIEMPO_CONFIRMACION_DESCONOCIDO
            if persona_id is not None
            else TIEMPO_CONFIRMACION_DESCONOCIDO_SIN_CUERPO
        )
        muestras_requeridas = (
            MIN_MUESTRAS_DESCONOCIDO
            if persona_id is not None
            else MIN_MUESTRAS_DESCONOCIDO_SIN_CUERPO
        )

        if (
            tiempo_visible >= tiempo_confirmacion
            and candidato["muestras"] >= muestras_requeridas
            and not candidato["guardado"]
            and ahora - candidato["ultima_captura"] >= COOLDOWN_CAPTURA
        ):
            captura = guardar_desconocido(
                candidato,
                tracker_id,
                modelo
            )
            if captura is None:
                candidato.update({
                    "inicio": ahora,
                    "muestras": 0,
                    "mejor_frame": frame.copy(),
                    "mejor_bbox": bbox_actual,
                    "mejor_area": area_rostro,
                    "mejor_calidad": calidad_actual,
                    "mejor_embedding": embedding_actual.copy(),
                    "embedding_semilla": embedding_actual.copy(),
                    "confirmaciones_incompatibles": 0
                })
                return (
                    (160, 160, 160),
                    f"ID {tracker_id} | Esperando una captura reutilizable"
                )

            (
                nombre_temporal,
                ruta_muestra,
                embedding_muestra,
                calidad_muestra
            ) = captura
            (
                nombre_existente,
                similitud_existente,
                tipo_existente,
                reconocido_existente
            ) = comparar_con_referencias(
                embedding_muestra,
                referencias
            )

            if reconocido_existente:
                identidad_existente = {
                    "nombre": nombre_existente,
                    "similitud": similitud_existente,
                    "tipo": tipo_existente,
                    "embedding": embedding_muestra.copy()
                }
                rostros_revocados = set()
                if persona_id is not None:
                    rostros_revocados = self._resolver_propietarios_identidad(
                        persona_id,
                        identidad_existente,
                        historial_personas
                    )

                if rostros_revocados is not None:
                    ruta_muestra.unlink(missing_ok=True)
                    ruta_muestra.parent.rmdir()
                    for rostro_id in rostros_revocados:
                        historial_reconocidos.pop(rostro_id, None)
                        eliminar_candidato_desconocido(
                            candidatos_desconocidos,
                            tracker_id=rostro_id
                        )

                    historial_reconocidos[tracker_id] = {
                        **identidad_existente,
                        "ultimo_visto": ahora,
                        "bbox": bbox_actual
                    }
                    if persona_id is not None:
                        persona = historial_personas.setdefault(persona_id, {})
                        self._asignar_identidad_persona(
                            persona,
                            identidad_existente,
                            tracker_id
                        )

                    candidato["ultima_captura"] = ahora
                    candidato["guardado"] = True
                    texto = (
                        f"ID {tracker_id} | {nombre_existente} | "
                        f"reidentificado desde mejor captura "
                        f"{similitud_existente:.2f}"
                    )
                    with self.lock:
                        self.last_event = texto
                    color = (
                        (0, 255, 0)
                        if tipo_existente == "oficial"
                        else (0, 255, 255)
                    )
                    return color, texto

            posible_duplicado = (
                nombre_existente != "Desconocido"
                and similitud_existente
                >= MIN_SIMILITUD_EVITAR_GALERIA_DUPLICADA
            )
            if reconocido_existente or posible_duplicado:
                ruta_muestra.unlink(missing_ok=True)
                ruta_muestra.parent.rmdir()
                candidato.update({
                    "inicio": ahora,
                    "muestras": 0,
                    "mejor_frame": frame.copy(),
                    "mejor_bbox": bbox_actual,
                    "mejor_area": area_rostro,
                    "mejor_calidad": calidad_actual,
                    "mejor_embedding": embedding_actual.copy(),
                    "embedding_semilla": embedding_actual.copy(),
                    "confirmaciones_incompatibles": 0
                })
                estado = (
                    "coincidencia ambigua"
                    if reconocido_existente
                    else "esperando mejor angulo"
                )
                return (
                    (160, 160, 160),
                    f"ID {tracker_id} | Posible {nombre_existente} | {estado}"
                )

            datos_muestra = ruta_muestra.stat()
            referencias.append({
                "nombre": nombre_temporal,
                "embedding": embedding_muestra,
                "tipo": "pendiente",
                "firma_archivo": (
                    datos_muestra.st_mtime_ns,
                    datos_muestra.st_size
                ),
                "ruta": str(ruta_muestra),
                "calidad": calidad_muestra
            })
            identidad_provisional = {
                "nombre": nombre_temporal,
                "similitud": 1.0,
                "tipo": "pendiente",
                "embedding": embedding_muestra.copy()
            }
            historial_reconocidos[tracker_id] = {
                **identidad_provisional,
                "ultimo_visto": ahora,
                "bbox": bbox_actual
            }
            if persona_id is not None:
                persona = historial_personas.setdefault(persona_id, {})
                self._asignar_identidad_persona(
                    persona,
                    identidad_provisional,
                    tracker_id
                )

            candidato["ultima_captura"] = ahora
            candidato["guardado"] = True
            texto = f"ID {tracker_id} | Pendiente guardado: {nombre_temporal}"

            with self.lock:
                self.last_event = texto

        return (0, 0, 255), texto

    def _buscar_identidad_reciente(
        self,
        tracker_id,
        embedding_actual,
        bbox_actual,
        historial_reconocidos
    ):
        ahora = time.time()
        mejor_historial = None
        mejor_similitud = -1.0

        for otro_tracker_id, historial in historial_reconocidos.items():
            if otro_tracker_id == tracker_id or "embedding" not in historial:
                continue

            if ahora - historial["ultimo_visto"] > TOLERANCIA_OCLUSION_SEGUNDOS:
                continue

            similitud = float(np.dot(embedding_actual, historial["embedding"]))
            iou = calcular_iou(bbox_actual, historial.get("bbox", bbox_actual))
            misma_posicion = iou >= MIN_IOU_REIDENTIFICACION
            similitud_fuerte = similitud >= UMBRAL_SIMILITUD

            if (
                similitud >= MIN_SIMILITUD_REIDENTIFICACION
                and (misma_posicion or similitud_fuerte)
                and similitud > mejor_similitud
            ):
                mejor_historial = historial
                mejor_similitud = similitud

        return mejor_historial, mejor_similitud

    def _buscar_identidad_por_posicion(
        self,
        tracker_id,
        bbox_actual,
        historial_reconocidos
    ):
        ahora = time.time()
        mejor_historial = None
        mejor_iou = MIN_IOU_REIDENTIFICACION

        for otro_tracker_id, historial in historial_reconocidos.items():
            if otro_tracker_id == tracker_id:
                continue

            if ahora - historial["ultimo_visto"] > TOLERANCIA_OCLUSION_SEGUNDOS:
                continue

            iou = calcular_iou(bbox_actual, historial.get("bbox", bbox_actual))
            if iou >= mejor_iou:
                mejor_historial = historial
                mejor_iou = iou

        return mejor_historial

    def _dibujar_resultados(self, frame, resultados):
        for x1, y1, x2, y2, texto, color in resultados:
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(
                frame,
                texto,
                (x1, max(y1 - 10, 20)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                color,
                2
            )


# =========================
# ARCHIVOS
# =========================


def listar_galerias(carpeta):
    ruta = Path(carpeta)
    ruta.mkdir(exist_ok=True)
    galerias = []

    nombres = sorted({nombre for nombre, _ in iterar_muestras(ruta)})
    for nombre in nombres:
        muestras = [
            archivo
            for nombre_muestra, archivo in iterar_muestras(ruta)
            if nombre_muestra == nombre
        ]
        if not muestras:
            continue
        portada = max(
            muestras,
            key=lambda archivo: calcular_calidad_muestra(leer_imagen(archivo))
        )
        modificada = max(archivo.stat().st_mtime for archivo in muestras)
        relativa = quote(
            portada.resolve().relative_to(BASE_DIR).as_posix(),
            safe="/"
        )
        galerias.append({
            "name": nombre,
            "url": f"/{relativa}?v={portada.stat().st_mtime_ns}",
            "modified": modificada,
            "sampleCount": len(muestras),
        })

    return sorted(galerias, key=lambda item: item["modified"], reverse=True)


def contar_galerias(carpeta):
    return len({nombre for nombre, _ in iterar_muestras(carpeta)})


def firma_galerias():
    digest = hashlib.sha256()

    for etiqueta, carpeta in (
        ("references", CARPETA_REFERENCIAS),
        ("pending", CARPETA_PENDIENTES),
    ):
        digest.update(etiqueta.encode("utf-8"))
        muestras = sorted(
            iterar_muestras(carpeta),
            key=lambda muestra: (muestra[0].casefold(), muestra[1].name.casefold())
        )
        for nombre, archivo in muestras:
            datos = archivo.stat()
            digest.update(nombre.encode("utf-8"))
            digest.update(archivo.name.encode("utf-8"))
            digest.update(str(datos.st_mtime_ns).encode("ascii"))
            digest.update(str(datos.st_size).encode("ascii"))

    return digest.hexdigest()


def nombre_galeria_seguro(nombre):
    stem = Path(str(nombre)).name.strip()
    if not stem:
        raise ValueError("El nombre no puede estar vacio")

    caracteres_validos = []
    for caracter in stem:
        if caracter.isalnum() or caracter in ("-", "_"):
            caracteres_validos.append(caracter)
        elif caracter.isspace():
            caracteres_validos.append("_")

    stem_limpio = "".join(caracteres_validos).strip("_")

    if not stem_limpio:
        raise ValueError("El nombre debe tener letras o numeros")

    return stem_limpio


def ruta_galeria_segura(carpeta, nombre):
    return Path(carpeta) / nombre_galeria_seguro(nombre)


def ruta_directorio_unica(ruta):
    if not ruta.exists():
        return ruta

    contador = 1
    while True:
        candidata = ruta.with_name(f"{ruta.name}_{contador}")
        if not candidata.exists():
            return candidata
        contador += 1


def migrar_imagenes_sueltas(carpeta):
    raiz = Path(carpeta)
    raiz.mkdir(exist_ok=True)
    for archivo in list(raiz.iterdir()):
        if not archivo.is_file() or archivo.suffix.lower() not in EXTENSIONES_IMAGEN:
            continue
        galeria = ruta_directorio_unica(
            ruta_galeria_segura(carpeta, archivo.stem)
        )
        galeria.mkdir()
        shutil.move(str(archivo), str(galeria / archivo.name))


def aprobar_pendiente(nombre):
    origen = ruta_galeria_segura(CARPETA_PENDIENTES, nombre)
    destino = ruta_directorio_unica(
        ruta_galeria_segura(CARPETA_REFERENCIAS, nombre)
    )
    if not origen.is_dir():
        raise FileNotFoundError("La persona pendiente no existe")
    shutil.move(str(origen), str(destino))


def mover_referencia_a_pendiente(nombre):
    origen = ruta_galeria_segura(CARPETA_REFERENCIAS, nombre)
    destino = ruta_directorio_unica(
        ruta_galeria_segura(CARPETA_PENDIENTES, nombre)
    )
    if not origen.is_dir():
        raise FileNotFoundError("La persona de referencia no existe")
    shutil.move(str(origen), str(destino))


def renombrar_galeria(carpeta, nombre_actual, nombre_nuevo):
    origen = ruta_galeria_segura(carpeta, nombre_actual)
    if not origen.is_dir():
        raise FileNotFoundError("La persona no existe")
    destino = ruta_galeria_segura(carpeta, nombre_nuevo)
    if origen.name == destino.name:
        return
    if origen.resolve() == destino.resolve():
        temporal = ruta_directorio_unica(
            origen.with_name(f"__renombrando__{origen.name}")
        )
        origen.rename(temporal)
        temporal.rename(destino)
        return
    destino = ruta_directorio_unica(destino)
    origen.rename(destino)


def descartar_pendiente(nombre):
    ruta = ruta_galeria_segura(CARPETA_PENDIENTES, nombre)
    if not ruta.is_dir():
        raise FileNotFoundError("La persona pendiente no existe")
    shutil.rmtree(ruta)


def recortar_muestra(frame, bbox, margen=30):
    x1, y1, x2, y2 = bbox
    x1 = max(0, int(x1) - margen)
    y1 = max(0, int(y1) - margen)
    x2 = min(frame.shape[1], int(x2) + margen)
    y2 = min(frame.shape[0], int(y2) + margen)
    return frame[y1:y2, x1:x2]


def escribir_jpg(ruta, imagen):
    correcto, datos = cv2.imencode(".jpg", imagen)
    if not correcto:
        raise RuntimeError("No se pudo codificar la muestra facial")
    datos.tofile(str(ruta))


def agregar_muestra_a_galeria(frame, bbox, nombre, embedding, referencias):
    galeria = ruta_galeria_segura(CARPETA_PENDIENTES, nombre)
    if not galeria.is_dir():
        return False

    muestras_identidad = [
        referencia
        for referencia in referencias
        if referencia["nombre"] == nombre
        and referencia["tipo"] == "pendiente"
    ]
    if muestras_identidad:
        semilla = min(
            muestras_identidad,
            key=lambda referencia: (
                Path(referencia["ruta"]).stat().st_mtime_ns
                if referencia.get("ruta")
                and Path(referencia["ruta"]).exists()
                else 0
            )
        )
        similitud_semilla = float(
            np.dot(embedding, semilla["embedding"])
        )
        if similitud_semilla < MIN_SIMILITUD_MUESTRA_CON_SEMILLA:
            return False

        ultima = max(
            Path(referencia["ruta"]).stat().st_mtime
            for referencia in muestras_identidad
            if referencia.get("ruta") and Path(referencia["ruta"]).exists()
        )
        if time.time() - ultima < INTERVALO_NUEVA_MUESTRA_SEGUNDOS:
            return False
        if max(
            float(np.dot(embedding, referencia["embedding"]))
            for referencia in muestras_identidad
        ) >= MAX_SIMILITUD_MUESTRA_REDUNDANTE:
            return False

    recorte = recortar_muestra(frame, bbox)
    calidad = calcular_calidad_muestra(recorte)
    reemplazada = None
    if len(muestras_identidad) >= MAX_MUESTRAS_POR_PERSONA:
        peor = min(
            muestras_identidad,
            key=lambda referencia: referencia.get("calidad", 0.0)
        )
        if calidad < peor.get("calidad", 0.0) + MIN_MEJORA_CALIDAD_REEMPLAZO:
            return False
        reemplazada = peor

    ruta = galeria / f"muestra_{time.time_ns()}.jpg"
    escribir_jpg(ruta, recorte)
    datos = ruta.stat()
    if reemplazada is not None:
        ruta_anterior = Path(reemplazada["ruta"])
        if ruta_anterior.exists():
            ruta_anterior.unlink()
        referencias[:] = [
            referencia
            for referencia in referencias
            if referencia is not reemplazada
        ]

    referencias.append({
        "nombre": nombre,
        "embedding": embedding.copy(),
        "tipo": "pendiente",
        "firma_archivo": (datos.st_mtime_ns, datos.st_size),
        "ruta": str(ruta),
        "calidad": calidad
    })
    return True


def guardar_desconocido(candidato, tracker_id, modelo):
    mejor_frame = candidato["mejor_frame"]
    bx1, by1, bx2, by2 = candidato["mejor_bbox"]

    rostro_recortado = recortar_muestra(
        mejor_frame,
        (bx1, by1, bx2, by2)
    )
    rostros_validados = modelo.get(rostro_recortado)
    if not rostros_validados:
        print(
            "Captura descartada: SCRFD no pudo reutilizar el rostro recortado."
        )
        return None

    rostro_validado = obtener_rostro_principal(rostros_validados)
    captura_evaluable, motivo = evaluar_calidad_rostro(
        rostro_validado.bbox,
        rostro_validado.kps,
        float(rostro_validado.det_score),
        validar_tamano_confianza=False
    )
    if not captura_evaluable:
        print(f"Captura descartada: {motivo}.")
        return None

    embedding_validado = normalizar_vector(rostro_validado.embedding)
    calidad = calcular_calidad_muestra(rostro_recortado)
    nombre_galeria = datetime.now().strftime(
        f"desconocido_track_{tracker_id}_%Y%m%d_%H%M%S"
    )
    galeria = ruta_directorio_unica(
        ruta_galeria_segura(CARPETA_PENDIENTES, nombre_galeria)
    )
    galeria.mkdir(parents=True)
    ruta_guardado = galeria / "muestra_01.jpg"
    Path(CARPETA_PENDIENTES).mkdir(exist_ok=True)
    escribir_jpg(ruta_guardado, rostro_recortado)
    print(f"Rostro desconocido guardado para revision: {ruta_guardado}")
    return galeria.name, ruta_guardado, embedding_validado, calidad


# =========================
# SERVIDOR WEB
# =========================


motor = MotorReconocimiento()


class WitcamHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        return

    def do_GET(self):
        parsed = urlparse(self.path)
        path = unquote(parsed.path)

        if path == "/":
            self._servir_archivo("index.html")
            return

        if path == "/video_feed":
            self._servir_video()
            return

        if path == "/placeholder":
            self._servir_jpeg(frame_espera())
            return

        if path == "/api/status":
            self._json(motor.snapshot())
            return

        if path == "/api/list":
            self._json({
                "references": listar_galerias(CARPETA_REFERENCIAS),
                "pending": listar_galerias(CARPETA_PENDIENTES),
                "gallery_signature": firma_galerias(),
            })
            return

        self._servir_archivo(path.lstrip("/"))

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        data = self._leer_json()

        try:
            if path == "/api/start":
                motor.start()
                self._json({"ok": True})
                return

            if path == "/api/stop":
                motor.stop()
                self._json({"ok": True})
                return

            if path == "/api/approve":
                aprobar_pendiente(data.get("file", ""))
                self._json({"ok": True})
                return

            if path == "/api/unapprove":
                mover_referencia_a_pendiente(data.get("file", ""))
                self._json({"ok": True})
                return

            if path == "/api/rename":
                tipo = data.get("type", "")
                carpeta = CARPETA_PENDIENTES if tipo == "pending" else CARPETA_REFERENCIAS
                renombrar_galeria(carpeta, data.get("file", ""), data.get("newName", ""))
                self._json({"ok": True})
                return

            if path == "/api/reject":
                descartar_pendiente(data.get("file", ""))
                self._json({"ok": True})
                return

            self.send_error(404)
        except Exception as error:
            self._json({"ok": False, "error": str(error)}, status=400)

    def _leer_json(self):
        length = int(self.headers.get("Content-Length", "0"))
        if length == 0:
            return {}

        raw = self.rfile.read(length).decode("utf-8")
        return json.loads(raw)

    def _json(self, data, status=200):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _servir_archivo(self, relative_path):
        ruta = (BASE_DIR / relative_path).resolve()

        if not ruta.is_relative_to(BASE_DIR):
            self.send_error(403)
            return

        if not ruta.exists() or not ruta.is_file():
            self.send_error(404)
            return

        content_type = mimetypes.guess_type(str(ruta))[0] or "application/octet-stream"
        data = ruta.read_bytes()

        self.send_response(200)
        self.send_header("Content-Type", content_type)
        if ruta.suffix.lower() in EXTENSIONES_IMAGEN:
            self.send_header("Cache-Control", "no-store, max-age=0")
            self.send_header("Pragma", "no-cache")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _servir_video(self):
        self.send_response(200)
        self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
        self.end_headers()

        while True:
            frame = motor.get_frame()

            if frame is None:
                frame = frame_espera()

            try:
                self.wfile.write(b"--frame\r\n")
                self.wfile.write(b"Content-Type: image/jpeg\r\n\r\n")
                self.wfile.write(frame)
                self.wfile.write(b"\r\n")
                time.sleep(0.08)
            except (BrokenPipeError, ConnectionResetError):
                break

    def _servir_jpeg(self, frame):
        self.send_response(200)
        self.send_header("Content-Type", "image/jpeg")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(frame)))
        self.end_headers()
        self.wfile.write(frame)


def frame_espera():
    return crear_frame_mensaje("Presiona Iniciar en la interfaz")


def crear_frame_mensaje(mensaje):
    frame = np.zeros(
        (ALTO_MAX_VIDEO_WEB, ANCHO_MAX_VIDEO_WEB, 3),
        dtype=np.uint8
    )
    frame[:] = (24, 34, 30)
    escala = 1.25
    grosor = 2
    (ancho_texto, alto_texto), _ = cv2.getTextSize(
        mensaje,
        cv2.FONT_HERSHEY_SIMPLEX,
        escala,
        grosor
    )
    origen = (
        max(24, (ANCHO_MAX_VIDEO_WEB - ancho_texto) // 2),
        (ALTO_MAX_VIDEO_WEB + alto_texto) // 2
    )
    cv2.putText(
        frame,
        mensaje,
        origen,
        cv2.FONT_HERSHEY_SIMPLEX,
        escala,
        (255, 255, 255),
        grosor
    )
    correcto, buffer = cv2.imencode(".jpg", frame)
    return buffer.tobytes() if correcto else b""


def main():
    Path(CARPETA_REFERENCIAS).mkdir(exist_ok=True)
    Path(CARPETA_PENDIENTES).mkdir(exist_ok=True)
    migrar_imagenes_sueltas(CARPETA_REFERENCIAS)
    migrar_imagenes_sueltas(CARPETA_PENDIENTES)
    motor.latest_jpeg = frame_espera()

    try:
        servidor = ThreadingHTTPServer((HOST, PUERTO_WEB), WitcamHandler)
    except OSError:
        print(f"No se pudo iniciar Witcam en http://{HOST}:{PUERTO_WEB}/")
        print("Ese puerto probablemente esta ocupado por otro servidor, por ejemplo php -S.")
        print("Cierra ese servidor con Ctrl+C y vuelve a ejecutar: python app.py")
        return

    print(f"Witcam web listo en http://{HOST}:{PUERTO_WEB}/")
    print("Abre esa URL en Chrome y presiona Iniciar.")
    print("Ctrl+C para salir.")

    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("Cerrando Witcam...")
    finally:
        motor.stop()
        servidor.server_close()


if __name__ == "__main__":
    main()
