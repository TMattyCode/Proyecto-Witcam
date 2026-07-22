import json
import mimetypes
import os
import shutil
import threading
import time
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

import cv2
import numpy as np
import supervision as sv
from insightface.app import FaceAnalysis
from insightface.utils import face_align
from ultralytics import YOLO

# =========================
# CONFIGURACION
# =========================

CAMARA = "rtsp://127.0.0.1:8554/camara1"
HOST = "localhost"
PUERTO_WEB = 8000

CARPETA_REFERENCIAS = "referencias_reconocimiento"
CARPETA_PENDIENTES = "referencias_pendientes"
INTERVALO_REVISION_CARPETAS = 2.0

CARPETAS_REFERENCIAS = [
    {"ruta": CARPETA_REFERENCIAS, "tipo": "oficial"},
    {"ruta": CARPETA_PENDIENTES, "tipo": "pendiente"},
]

TIEMPO_CONFIRMACION_DESCONOCIDO = 1.5
MIN_MUESTRAS_DESCONOCIDO = 3
MIN_ANCHO_ROSTRO = 55
MIN_ALTO_ROSTRO = 55
MIN_CONFIANZA_ROSTRO_ANALIZABLE = 0.60
MIN_SIMETRIA_ROSTRO_ANALIZABLE = 0.45
MAX_DESVIACION_NARIZ_ANALIZABLE = 0.35
COOLDOWN_CAPTURA = 15
TOLERANCIA_OCLUSION_SEGUNDOS = 6.0
MIN_SIMILITUD_POSIBLE_MISMA_PERSONA = 0.30
MIN_SIMILITUD_REIDENTIFICACION = 0.35
MIN_IOU_REIDENTIFICACION = 0.10

UMBRAL_SIMILITUD = 0.45

ANCHO_CAMARA = 640
ALTO_CAMARA = 480
ANCHO_ANALISIS = 512
ALTO_ANALISIS = 384
DETECTAR_CADA_N_FRAMES = 1
RECONOCER_CADA_N_DETECCIONES = 6
DET_SIZE = 352
USAR_YOLO_PERSONAS = True
MODELO_YOLO = str(Path(__file__).with_name("yolo26n.pt"))
YOLO_IMGSZ = 416
YOLO_CONFIANZA = 0.35
DETECTAR_PERSONAS_CADA_N_CICLOS = 3
TOLERANCIA_IDENTIDAD_CORPORAL_SEGUNDOS = 3.0
MIN_CONFIRMACIONES_IDENTIDAD_INICIAL = 2
MIN_SIMILITUD_IDENTIDAD_INICIAL = 0.50
MIN_CONFIRMACIONES_CAMBIO_IDENTIDAD = 2
MIN_SIMILITUD_CAMBIO_IDENTIDAD = 0.60
MIN_SIMILITUD_TRASPASO_IDENTIDAD = 0.60
MARGEN_SIMILITUD_TRASPASO_IDENTIDAD = 0.05
MAX_SEGUNDOS_EVIDENCIA_FACIAL_ANTIGUA = 1.5
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


def cargar_referencias(modelo):
    referencias = []

    print("Cargando rostros de referencia...")

    for carpeta_info in CARPETAS_REFERENCIAS:
        carpeta = Path(carpeta_info["ruta"])
        tipo = carpeta_info["tipo"]
        carpeta.mkdir(exist_ok=True)

        imagenes = []
        for extension in ("*.jpg", "*.jpeg", "*.png", "*.webp"):
            imagenes.extend(carpeta.glob(extension))

        for ruta_imagen in imagenes:
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
                "nombre": ruta_imagen.stem,
                "embedding": embedding,
                "tipo": tipo
            })

            print(f"Referencia cargada: {ruta_imagen.stem} | tipo: {tipo}")

    if not referencias:
        print("No hay rostros de referencia validos todavia.")
        print(f"Puedes agregar imagenes manualmente en: {CARPETA_REFERENCIAS}")
        print(f"Las capturas de desconocidos se guardaran en: {CARPETA_PENDIENTES}")

    return referencias


def comparar_con_referencias(embedding_actual, referencias):
    mejor_nombre = "Desconocido"
    mejor_similitud = -1
    mejor_tipo = None

    for referencia in referencias:
        similitud = float(np.dot(embedding_actual, referencia["embedding"]))

        if similitud > mejor_similitud:
            mejor_similitud = similitud
            mejor_nombre = referencia["nombre"]
            mejor_tipo = referencia["tipo"]

    reconocido = mejor_similitud >= UMBRAL_SIMILITUD
    return mejor_nombre, mejor_similitud, mejor_tipo, reconocido


def obtener_estado_carpetas():
    estado = []

    for carpeta_info in CARPETAS_REFERENCIAS:
        carpeta = Path(carpeta_info["ruta"])
        carpeta.mkdir(exist_ok=True)

        for imagen in carpeta.iterdir():
            if not imagen.is_file() or imagen.suffix.lower() not in EXTENSIONES_IMAGEN:
                continue

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


def evaluar_calidad_rostro(caja, puntos_clave, confianza):
    x1, y1, x2, y2 = caja
    ancho = x2 - x1
    alto = y2 - y1

    if ancho < MIN_ANCHO_ROSTRO or alto < MIN_ALTO_ROSTRO:
        return False, "rostro muy pequeno"

    if confianza < MIN_CONFIANZA_ROSTRO_ANALIZABLE:
        return False, "baja confianza"

    if puntos_clave is None or len(puntos_clave) < 3:
        return False, "puntos faciales insuficientes"

    ojo_izquierdo = np.asarray(puntos_clave[0], dtype=np.float32)
    ojo_derecho = np.asarray(puntos_clave[1], dtype=np.float32)
    nariz = np.asarray(puntos_clave[2], dtype=np.float32)
    eje_ojos = ojo_derecho - ojo_izquierdo
    distancia_ojos = float(np.linalg.norm(eje_ojos))

    if distancia_ojos <= 1.0:
        return False, "ojos no visibles"

    distancia_nariz_izquierda = float(np.linalg.norm(nariz - ojo_izquierdo))
    distancia_nariz_derecha = float(np.linalg.norm(nariz - ojo_derecho))
    distancia_mayor = max(distancia_nariz_izquierda, distancia_nariz_derecha)
    simetria = (
        min(distancia_nariz_izquierda, distancia_nariz_derecha) / distancia_mayor
        if distancia_mayor > 0
        else 0.0
    )

    punto_medio_ojos = (ojo_izquierdo + ojo_derecho) / 2.0
    eje_ojos_normalizado = eje_ojos / distancia_ojos
    desviacion_nariz = abs(
        float(np.dot(nariz - punto_medio_ojos, eje_ojos_normalizado))
    ) / distancia_ojos

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
        self.stop_event = stop_event
        self.local_stop_event = threading.Event()
        self.lock = threading.Lock()
        self.camara = None
        self.thread = None
        self.latest_frame = None
        self.sequence = 0
        self.error = None
        self.fps = 15.0

    def start(self):
        self._abrir_camara()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def _abrir_camara(self):
        if isinstance(self.fuente, str):
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

        while not self.stop_event.is_set() and not self.local_stop_event.is_set():
            correcto, frame = self.camara.read()

            if not correcto:
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
                "references_files": len(listar_imagenes(CARPETA_REFERENCIAS)),
                "pending_files": len(listar_imagenes(CARPETA_PENDIENTES)),
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

            with self.lock:
                self.last_event = "Cargando modelo"

            modelo = crear_modelo()
            if USAR_YOLO_PERSONAS:
                modelo_personas = crear_modelo_personas()
            referencias = cargar_referencias(modelo)
            estado_carpetas = obtener_estado_carpetas()
            ultima_revision_carpetas = time.time()

            Path(CARPETA_PENDIENTES).mkdir(exist_ok=True)

            candidatos_desconocidos = {}
            historial_reconocidos = {}
            historial_personas = {}

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
                        referencias = cargar_referencias(modelo)
                        estado_carpetas = nuevo_estado_carpetas
                        candidatos_desconocidos.clear()
                        historial_reconocidos.clear()
                        historial_personas.clear()
                        contador_detecciones = RECONOCER_CADA_N_DETECCIONES - 1

                        with self.lock:
                            self.references_count = len(referencias)
                            self.last_event = "Referencias actualizadas"
                            self.resultados_dibujo = []

                    ultima_revision_carpetas = ahora_revision

                if secuencia - ultima_secuencia_detectada < DETECTAR_CADA_N_FRAMES:
                    self.stop_event.wait(0.01)
                    continue

                contador_detecciones += 1
                realizar_reconocimiento = (
                    contador_detecciones >= RECONOCER_CADA_N_DETECCIONES
                )

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
                        historial_personas
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
                    historial_personas
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

                limpiar_tracks_antiguos(candidatos_desconocidos)
                limpiar_historial_reconocidos(historial_reconocidos)
                limpiar_tracks_antiguos(
                    historial_personas,
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
        historial_personas
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

        for box, tracker_id in zip(detections.xyxy, detections.tracker_id):
            x1, y1, x2, y2 = box.astype(int)
            tracker_id = int(tracker_id)

            mejor_dato = None
            mejor_iou = 0.0

            for dato_rostro in analisis_rostros:
                iou_actual = calcular_iou(box, dato_rostro["bbox"])

                if iou_actual > mejor_iou:
                    mejor_iou = iou_actual
                    mejor_dato = dato_rostro

            persona = self._buscar_persona_para_rostro(
                box,
                personas_seguidas
            )
            persona_id = persona["tracker_id"] if persona is not None else None

            if persona_id is not None:
                if mejor_dato is not None and mejor_dato["reconocido"]:
                    rostros_revocados = self._registrar_identidad_persona(
                        persona_id,
                        mejor_dato,
                        historial_personas,
                        tracker_id
                    )
                    for rostro_id in rostros_revocados:
                        historial_reconocidos.pop(rostro_id, None)
                        candidatos_desconocidos.pop(rostro_id, None)

                identidad_corporal = historial_personas.get(persona_id)
                if identidad_corporal is not None and "nombre" in identidad_corporal:
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
                    candidatos_desconocidos.pop(tracker_id, None)
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
                    candidatos_desconocidos.pop(tracker_id, None)
                    historial["ultimo_visto"] = time.time()
                    historial["bbox"] = bbox_actual
                    color = (0, 180, 255)
                    texto = (
                        f"ID {tracker_id} | {historial['nombre']} | "
                        f"{mejor_dato['motivo_no_evaluable']}"
                    )
                else:
                    candidato = candidatos_desconocidos.get(tracker_id)
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
                    candidatos_desconocidos.pop(tracker_id, None)
                    color = (
                        (0, 255, 0)
                        if historial["tipo"] == "oficial"
                        else (0, 255, 255)
                    )
                    texto = f"ID {tracker_id} | {historial['nombre']} | seguimiento"
                else:
                    candidato = candidatos_desconocidos.get(tracker_id)
                    if candidato is not None:
                        ahora = time.time()
                        area_rostro = max(0, x2 - x1) * max(0, y2 - y1)
                        candidato["ultimo_visto"] = ahora
                        candidato["bbox"] = bbox_actual

                        if area_rostro > candidato["mejor_area"]:
                            candidato["mejor_frame"] = frame.copy()
                            candidato["mejor_bbox"] = bbox_actual
                            candidato["mejor_area"] = area_rostro

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
                candidatos_desconocidos.pop(tracker_id, None)
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
                historial_reconocidos[tracker_id] = {
                    "nombre": nombre,
                    "similitud": similitud,
                    "tipo": tipo,
                    "ultimo_visto": time.time(),
                    "embedding": embedding_actual.copy(),
                    "bbox": bbox_actual
                }
                candidatos_desconocidos.pop(tracker_id, None)

                if tipo == "oficial":
                    color = (0, 255, 0)
                    texto = f"ID {tracker_id} | {nombre} | {similitud:.2f}"
                else:
                    color = (0, 255, 255)
                    texto = f"ID {tracker_id} | Pendiente: {nombre} | {similitud:.2f}"
            else:
                resultado = self._manejar_desconocido(
                    frame,
                    tracker_id,
                    box,
                    nombre,
                    similitud,
                    embedding_actual,
                    bbox_actual,
                    referencias,
                    candidatos_desconocidos,
                    historial_reconocidos
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
    def _actualizar_personas_visibles(personas, historial_personas):
        ahora = time.time()
        for persona in personas:
            datos = historial_personas.setdefault(persona["tracker_id"], {})
            datos["ultimo_visto"] = ahora
            datos["bbox"] = persona["bbox"]

    @staticmethod
    def _buscar_persona_para_rostro(caja_rostro, personas):
        rx1, ry1, rx2, ry2 = caja_rostro
        centro_x = (rx1 + rx2) / 2.0
        centro_y = (ry1 + ry2) / 2.0
        candidatas = []

        for persona in personas:
            px1, py1, px2, py2 = persona["bbox"]
            if not (px1 <= centro_x <= px2 and py1 <= centro_y <= py2):
                continue

            ancho = max(1, px2 - px1)
            alto = max(1, py2 - py1)
            centro_cabeza_x = px1 + ancho / 2.0
            centro_cabeza_y = py1 + alto * 0.20
            distancia = (
                abs(centro_x - centro_cabeza_x) / ancho
                + abs(centro_y - centro_cabeza_y) / alto
            )
            candidatas.append((distancia, persona))

        if not candidatas:
            return None

        return min(candidatas, key=lambda candidata: candidata[0])[1]

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
            evidencia_antigua = (
                ahora - propietario.get("ultima_evidencia_facial", 0)
                > MAX_SEGUNDOS_EVIDENCIA_FACIAL_ANTIGUA
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
            if not evidencia_suficiente or not (
                evidencia_antigua or evidencia_mas_fuerte
            ):
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
            "datos_cambio"
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
            "confirmaciones_cambio": 0
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
            if "nombre" in identidad:
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

    def _manejar_desconocido(
        self,
        frame,
        tracker_id,
        box,
        nombre,
        similitud,
        embedding_actual,
        bbox_actual,
        referencias,
        candidatos_desconocidos,
        historial_reconocidos
    ):
        x1, y1, x2, y2 = box.astype(int)

        if tracker_id in historial_reconocidos:
            historial = historial_reconocidos[tracker_id]
            tiempo_desde_reconocido = time.time() - historial["ultimo_visto"]
            parece_misma_persona = (
                nombre == historial["nombre"]
                and similitud >= MIN_SIMILITUD_POSIBLE_MISMA_PERSONA
            )

            if tiempo_desde_reconocido <= TOLERANCIA_OCLUSION_SEGUNDOS or parece_misma_persona:
                historial["ultimo_visto"] = time.time()
                historial["bbox"] = bbox_actual
                candidatos_desconocidos.pop(tracker_id, None)
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
            candidatos_desconocidos.pop(tracker_id, None)
            texto = (
                f"ID {tracker_id} | {historial_reidentificado['nombre']} "
                f"| reidentificado {similitud_reidentificacion:.2f}"
            )
            return (0, 180, 255), texto

        ahora = time.time()
        ancho_rostro = x2 - x1
        alto_rostro = y2 - y1
        area_rostro = ancho_rostro * alto_rostro

        if ancho_rostro < MIN_ANCHO_ROSTRO or alto_rostro < MIN_ALTO_ROSTRO:
            return (0, 0, 255), f"ID {tracker_id} | Desconocido | rostro muy pequeno"

        if tracker_id not in candidatos_desconocidos:
            candidatos_desconocidos[tracker_id] = {
                "inicio": ahora,
                "ultimo_visto": ahora,
                "muestras": 1,
                "bbox": bbox_actual,
                "mejor_frame": frame.copy(),
                "mejor_bbox": bbox_actual,
                "mejor_area": area_rostro,
                "guardado": False,
                "ultima_captura": 0
            }
        else:
            candidato = candidatos_desconocidos[tracker_id]
            candidato["ultimo_visto"] = ahora
            candidato["muestras"] += 1
            candidato["bbox"] = bbox_actual

            if area_rostro > candidato["mejor_area"]:
                candidato["mejor_frame"] = frame.copy()
                candidato["mejor_bbox"] = bbox_actual
                candidato["mejor_area"] = area_rostro

        candidato = candidatos_desconocidos[tracker_id]
        tiempo_visible = ahora - candidato["inicio"]
        texto = f"ID {tracker_id} | Desconocido analizando... {tiempo_visible:.1f}s"

        if (
            tiempo_visible >= TIEMPO_CONFIRMACION_DESCONOCIDO
            and candidato["muestras"] >= MIN_MUESTRAS_DESCONOCIDO
            and not candidato["guardado"]
            and ahora - candidato["ultima_captura"] >= COOLDOWN_CAPTURA
        ):
            nombre_temporal = guardar_desconocido(candidato, tracker_id)
            referencias.append({
                "nombre": nombre_temporal,
                "embedding": embedding_actual.copy(),
                "tipo": "pendiente"
            })

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


def listar_imagenes(carpeta):
    ruta = Path(carpeta)
    ruta.mkdir(exist_ok=True)
    imagenes = []

    for archivo in ruta.iterdir():
        if not archivo.is_file() or archivo.suffix.lower() not in EXTENSIONES_IMAGEN:
            continue

        datos = archivo.stat()
        imagenes.append({
            "name": archivo.name,
            "url": f"/{carpeta}/{archivo.name}?v={datos.st_mtime_ns}",
            "modified": datos.st_mtime,
        })

    return sorted(imagenes, key=lambda item: item["modified"], reverse=True)


def ruta_segura(carpeta, nombre_archivo):
    nombre = Path(nombre_archivo).name
    ruta = Path(carpeta) / nombre

    if ruta.suffix.lower() not in EXTENSIONES_IMAGEN:
        raise ValueError("Extension de imagen no permitida")

    return ruta


def nombre_archivo_seguro(nombre_archivo, extension_original=None):
    ruta_nombre = Path(nombre_archivo).name
    stem = Path(ruta_nombre).stem.strip()
    extension = Path(ruta_nombre).suffix.lower()

    if not stem:
        raise ValueError("El nombre no puede estar vacio")

    if extension_original and not extension:
        extension = extension_original

    if extension not in EXTENSIONES_IMAGEN:
        raise ValueError("Extension de imagen no permitida")

    caracteres_validos = []
    for caracter in stem:
        if caracter.isalnum() or caracter in ("-", "_"):
            caracteres_validos.append(caracter)
        elif caracter.isspace():
            caracteres_validos.append("_")

    stem_limpio = "".join(caracteres_validos).strip("_")

    if not stem_limpio:
        raise ValueError("El nombre debe tener letras o numeros")

    return f"{stem_limpio}{extension}"


def ruta_unica(ruta):
    if not ruta.exists():
        return ruta

    contador = 1
    while True:
        candidata = ruta.with_name(f"{ruta.stem}_{contador}{ruta.suffix}")
        if not candidata.exists():
            return candidata
        contador += 1


def aprobar_pendiente(nombre_archivo):
    origen = ruta_segura(CARPETA_PENDIENTES, nombre_archivo)
    destino = ruta_unica(ruta_segura(CARPETA_REFERENCIAS, nombre_archivo))

    if not origen.exists():
        raise FileNotFoundError("La imagen pendiente no existe")

    shutil.move(str(origen), str(destino))


def mover_referencia_a_pendiente(nombre_archivo):
    origen = ruta_segura(CARPETA_REFERENCIAS, nombre_archivo)
    destino = ruta_unica(ruta_segura(CARPETA_PENDIENTES, nombre_archivo))

    if not origen.exists():
        raise FileNotFoundError("La imagen de referencia no existe")

    shutil.move(str(origen), str(destino))


def renombrar_imagen(carpeta, nombre_actual, nombre_nuevo):
    origen = ruta_segura(carpeta, nombre_actual)

    if not origen.exists():
        raise FileNotFoundError("La imagen no existe")

    nuevo_nombre = nombre_archivo_seguro(nombre_nuevo, origen.suffix.lower())
    destino = ruta_segura(carpeta, nuevo_nombre)

    if origen.name == destino.name:
        return

    if origen.resolve() == destino.resolve():
        temporal = ruta_unica(origen.with_name(f"__renombrando__{origen.name}"))
        origen.rename(temporal)
        temporal.rename(destino)
        return

    destino = ruta_unica(destino)
    origen.rename(destino)


def descartar_pendiente(nombre_archivo):
    ruta = ruta_segura(CARPETA_PENDIENTES, nombre_archivo)

    if not ruta.exists():
        raise FileNotFoundError("La imagen pendiente no existe")

    ruta.unlink()


def guardar_desconocido(candidato, tracker_id):
    mejor_frame = candidato["mejor_frame"]
    bx1, by1, bx2, by2 = candidato["mejor_bbox"]

    margen = 30
    bx1 = max(0, bx1 - margen)
    by1 = max(0, by1 - margen)
    bx2 = min(mejor_frame.shape[1], bx2 + margen)
    by2 = min(mejor_frame.shape[0], by2 + margen)

    rostro_recortado = mejor_frame[by1:by2, bx1:bx2]

    nombre_archivo = datetime.now().strftime(
        f"desconocido_track_{tracker_id}_%Y%m%d_%H%M%S.jpg"
    )
    ruta_guardado = Path(CARPETA_PENDIENTES) / nombre_archivo
    Path(CARPETA_PENDIENTES).mkdir(exist_ok=True)

    cv2.imwrite(str(ruta_guardado), rostro_recortado)
    print(f"Rostro desconocido guardado para revision: {ruta_guardado}")

    return ruta_guardado.stem


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
                "references": listar_imagenes(CARPETA_REFERENCIAS),
                "pending": listar_imagenes(CARPETA_PENDIENTES),
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
                renombrar_imagen(carpeta, data.get("file", ""), data.get("newName", ""))
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
        ruta = Path(relative_path)

        if ".." in ruta.parts:
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
    frame = np.zeros((ALTO_CAMARA, ANCHO_CAMARA, 3), dtype=np.uint8)
    frame[:] = (24, 34, 30)
    cv2.putText(
        frame,
        mensaje,
        (35, ALTO_CAMARA // 2),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (255, 255, 255),
        2
    )
    correcto, buffer = cv2.imencode(".jpg", frame)
    return buffer.tobytes() if correcto else b""


def main():
    Path(CARPETA_REFERENCIAS).mkdir(exist_ok=True)
    Path(CARPETA_PENDIENTES).mkdir(exist_ok=True)
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
