import json
import mimetypes
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

# =========================
# CONFIGURACION
# =========================

CAMARA = 0
HOST = "localhost"
PUERTO_WEB = 8000

CARPETA_REFERENCIAS = "referencias_reconocimiento"
CARPETA_PENDIENTES = "referencias_pendientes"
INTERVALO_REVISION_CARPETAS = 2.0

CARPETAS_REFERENCIAS = [
    {"ruta": CARPETA_REFERENCIAS, "tipo": "oficial"},
    {"ruta": CARPETA_PENDIENTES, "tipo": "pendiente"},
]

TIEMPO_CONFIRMACION_DESCONOCIDO = 3.0
MIN_MUESTRAS_DESCONOCIDO = 4
MIN_ANCHO_ROSTRO = 70
MIN_ALTO_ROSTRO = 70
COOLDOWN_CAPTURA = 15
TOLERANCIA_OCLUSION_SEGUNDOS = 6.0
MIN_SIMILITUD_POSIBLE_MISMA_PERSONA = 0.30

UMBRAL_SIMILITUD = 0.45

ANCHO_CAMARA = 640
ALTO_CAMARA = 480
ANCHO_ANALISIS = 416
ALTO_ANALISIS = 312
ANALIZAR_CADA_N_FRAMES = 10
DET_SIZE = 256
JPEG_QUALITY = 82

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
        providers=["CPUExecutionProvider"]
    )

    modelo.prepare(
        ctx_id=-1,
        det_size=(DET_SIZE, DET_SIZE)
    )

    return modelo


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
            self.latest_jpeg = buffer.tobytes()
            self.streaming = True

    def _run(self):
        modelo = None
        camara = None

        try:
            with self.lock:
                self.running = True
                self.streaming = False
                self.last_error = None
                self.last_event = "Cargando modelo"

            modelo = crear_modelo()
            referencias = cargar_referencias(modelo)
            estado_carpetas = obtener_estado_carpetas()
            ultima_revision_carpetas = time.time()

            Path(CARPETA_PENDIENTES).mkdir(exist_ok=True)

            candidatos_desconocidos = {}
            historial_reconocidos = {}

            camara = cv2.VideoCapture(CAMARA, cv2.CAP_DSHOW)
            camara.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
            camara.set(cv2.CAP_PROP_FPS, 15)
            camara.set(cv2.CAP_PROP_FRAME_WIDTH, ANCHO_CAMARA)
            camara.set(cv2.CAP_PROP_FRAME_HEIGHT, ALTO_CAMARA)
            camara.set(cv2.CAP_PROP_BUFFERSIZE, 1)

            if not camara.isOpened():
                raise RuntimeError("No se pudo abrir la webcam. Prueba CAMARA = 1 o CAMARA = 2.")

            fps_camara = camara.get(cv2.CAP_PROP_FPS)
            if fps_camara <= 0:
                fps_camara = 15

            tracker = sv.ByteTrack(
                track_activation_threshold=0.25,
                lost_track_buffer=30,
                minimum_matching_threshold=0.8,
                frame_rate=fps_camara,
                minimum_consecutive_frames=1
            )

            contador_frames = 0
            ultimos_resultados = []

            with self.lock:
                self.last_event = "Webcam activa"
                self.references_count = len(referencias)

            while not self.stop_event.is_set():
                correcto, frame = camara.read()

                if not correcto:
                    raise RuntimeError("No se pudo leer la imagen de la webcam.")

                ahora_revision = time.time()

                if ahora_revision - ultima_revision_carpetas >= INTERVALO_REVISION_CARPETAS:
                    nuevo_estado_carpetas = obtener_estado_carpetas()

                    if nuevo_estado_carpetas != estado_carpetas:
                        referencias = cargar_referencias(modelo)
                        estado_carpetas = nuevo_estado_carpetas
                        candidatos_desconocidos.clear()
                        historial_reconocidos.clear()

                        with self.lock:
                            self.references_count = len(referencias)
                            self.last_event = "Referencias actualizadas"

                    ultima_revision_carpetas = ahora_revision

                contador_frames += 1

                if contador_frames % ANALIZAR_CADA_N_FRAMES == 0:
                    ultimos_resultados = self._analizar_frame(
                        frame,
                        modelo,
                        referencias,
                        tracker,
                        candidatos_desconocidos,
                        historial_reconocidos
                    )

                    limpiar_tracks_antiguos(candidatos_desconocidos)
                    limpiar_historial_reconocidos(historial_reconocidos)

                    with self.lock:
                        self.detections = [
                            {"texto": texto, "color": color}
                            for _, _, _, _, texto, color in ultimos_resultados
                        ]

                self._dibujar_resultados(frame, ultimos_resultados)
                self._set_frame(frame)

        except Exception as error:
            with self.lock:
                self.last_error = str(error)
                self.last_event = "Error"
            print(f"Error en motor de reconocimiento: {error}")
        finally:
            if camara is not None:
                camara.release()

            with self.lock:
                self.running = False
                self.streaming = False
                self.latest_jpeg = crear_frame_mensaje("Presiona Iniciar en la interfaz")
                self.last_event = "Detenido"
                self.detections = []

    def _analizar_frame(
        self,
        frame,
        modelo,
        referencias,
        tracker,
        candidatos_desconocidos,
        historial_reconocidos
    ):
        frame_ia = cv2.resize(frame, (ANCHO_ANALISIS, ALTO_ANALISIS))
        rostros = modelo.get(frame_ia)
        resultados_actuales = []

        cajas_originales = []
        confianzas_originales = []
        analisis_rostros = []

        escala_x = frame.shape[1] / frame_ia.shape[1]
        escala_y = frame.shape[0] / frame_ia.shape[0]

        for rostro in rostros:
            x1, y1, x2, y2 = rostro.bbox.astype(int)

            x1 = int(x1 * escala_x)
            x2 = int(x2 * escala_x)
            y1 = int(y1 * escala_y)
            y2 = int(y2 * escala_y)

            bbox_actual = [x1, y1, x2, y2]
            embedding_actual = normalizar_vector(rostro.embedding)
            nombre, similitud, tipo, reconocido = comparar_con_referencias(
                embedding_actual,
                referencias
            )

            cajas_originales.append(bbox_actual)
            confianzas_originales.append(float(rostro.det_score))
            analisis_rostros.append({
                "bbox": bbox_actual,
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

            nombre = mejor_dato["nombre"]
            similitud = mejor_dato["similitud"]
            tipo = mejor_dato["tipo"]
            reconocido = mejor_dato["reconocido"]
            embedding_actual = mejor_dato["embedding"]
            bbox_actual = tuple(mejor_dato["bbox"])

            if reconocido:
                historial_reconocidos[tracker_id] = {
                    "nombre": nombre,
                    "similitud": similitud,
                    "tipo": tipo,
                    "ultimo_visto": time.time()
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
                candidatos_desconocidos.pop(tracker_id, None)
                texto = f"ID {tracker_id} | {historial['nombre']} | oclusion {similitud:.2f}"
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

        imagenes.append({
            "name": archivo.name,
            "url": f"/{carpeta}/{archivo.name}",
            "modified": archivo.stat().st_mtime,
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
        print("Cierra ese servidor con Ctrl+C y vuelve a ejecutar: python webcam_reconocimiento.py")
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
