import time
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
import supervision as sv
from insightface.app import FaceAnalysis

# =========================
# CONFIGURACION
# =========================

CAMARA = 0  # 0 = webcam principal. Si no funciona, prueba 1 o 2.
CARPETA_REFERENCIAS = "referencias"
CARPETA_PENDIENTES = "referencias_pendientes"
INTERVALO_REVISION_CARPETAS = 2.0  # segundos

CARPETAS_REFERENCIAS = [
    {
        "ruta": CARPETA_REFERENCIAS,
        "tipo": "oficial"
    },
    {
        "ruta": CARPETA_PENDIENTES,
        "tipo": "pendiente"
    }
]

TIEMPO_CONFIRMACION_DESCONOCIDO = 3.0  # segundos
MIN_MUESTRAS_DESCONOCIDO = 4
MIN_ANCHO_ROSTRO = 70
MIN_ALTO_ROSTRO = 70
COOLDOWN_CAPTURA = 15  # segundos para no guardar la misma cara muchas veces
TOLERANCIA_OCLUSION_SEGUNDOS = 6.0
MIN_SIMILITUD_POSIBLE_MISMA_PERSONA = 0.30

# En InsightFace el umbral no es 45, sino 0.45.
# Mas bajo = reconoce mas facil, pero puede equivocarse mas.
# Mas alto = mas estricto.
UMBRAL_SIMILITUD = 0.45

ANCHO_CAMARA = 640
ALTO_CAMARA = 480
ANCHO_ANALISIS = 416
ALTO_ANALISIS = 312
ANALIZAR_CADA_N_FRAMES = 10
DET_SIZE = 256

# =========================
# FUNCIONES
# =========================


def normalizar_vector(vector):
    return vector / np.linalg.norm(vector)


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

        imagenes = (
            list(carpeta.glob("*.jpg")) +
            list(carpeta.glob("*.jpeg")) +
            list(carpeta.glob("*.png"))
        )

        for ruta_imagen in imagenes:
            imagen = cv2.imread(str(ruta_imagen))

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
        raise Exception("No se pudo cargar ningun rostro de referencia valido.")

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

        imagenes = (
            list(carpeta.glob("*.jpg")) +
            list(carpeta.glob("*.jpeg")) +
            list(carpeta.glob("*.png"))
        )

        for imagen in imagenes:
            datos = imagen.stat()
            estado.append((
                str(imagen),
                datos.st_mtime,
                datos.st_size
            ))

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


def main():
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
        print("No se pudo abrir la webcam.")
        print("Prueba cambiando CAMARA = 1 o CAMARA = 2.")
        return

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

    print("Webcam iniciada.")
    print("Usando SCRFD + InsightFace + ByteTrack.")
    print("Presiona Q para salir.")

    contador_frames = 0
    ultimos_resultados = []

    while True:
        correcto, frame = camara.read()

        if not correcto:
            print("No se pudo leer la imagen de la webcam.")
            break

        ahora_revision = time.time()

        if ahora_revision - ultima_revision_carpetas >= INTERVALO_REVISION_CARPETAS:
            nuevo_estado_carpetas = obtener_estado_carpetas()

            if nuevo_estado_carpetas != estado_carpetas:
                print("Se detectaron cambios en las carpetas de referencias.")
                print("Recargando referencias...")

                referencias = cargar_referencias(modelo)
                estado_carpetas = nuevo_estado_carpetas
                candidatos_desconocidos.clear()
                historial_reconocidos.clear()

                print("Referencias actualizadas.")

            ultima_revision_carpetas = ahora_revision

        contador_frames += 1

        if contador_frames % ANALIZAR_CADA_N_FRAMES == 0:
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

            if detections.tracker_id is not None:
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
                            nombre = historial["nombre"]
                            similitud = historial["similitud"]
                            tipo = historial["tipo"]
                            color = (0, 255, 0) if tipo == "oficial" else (0, 255, 255)
                            texto = f"ID {tracker_id} | {nombre} | {similitud:.2f}"
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
                        if tracker_id in historial_reconocidos:
                            historial = historial_reconocidos[tracker_id]
                            tiempo_desde_reconocido = time.time() - historial["ultimo_visto"]
                            parece_misma_persona = (
                                nombre == historial["nombre"]
                                and similitud >= MIN_SIMILITUD_POSIBLE_MISMA_PERSONA
                            )

                            if (
                                tiempo_desde_reconocido <= TOLERANCIA_OCLUSION_SEGUNDOS
                                or parece_misma_persona
                            ):
                                historial["ultimo_visto"] = time.time()
                                candidatos_desconocidos.pop(tracker_id, None)
                                color = (0, 180, 255)
                                texto = (
                                    f"ID {tracker_id} | {historial['nombre']} "
                                    f"| oclusion {similitud:.2f}"
                                )
                                resultados_actuales.append((x1, y1, x2, y2, texto, color))
                                continue

                        ahora = time.time()
                        ancho_rostro = x2 - x1
                        alto_rostro = y2 - y1
                        area_rostro = ancho_rostro * alto_rostro
                        color = (0, 0, 255)

                        if ancho_rostro >= MIN_ANCHO_ROSTRO and alto_rostro >= MIN_ALTO_ROSTRO:
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

                                cv2.imwrite(str(ruta_guardado), rostro_recortado)
                                print(f"Rostro desconocido guardado para revision: {ruta_guardado}")

                                nombre_temporal = Path(nombre_archivo).stem
                                referencias.append({
                                    "nombre": nombre_temporal,
                                    "embedding": embedding_actual.copy(),
                                    "tipo": "pendiente"
                                })

                                print(f"Referencia temporal agregada: {nombre_temporal}")

                                candidato["ultima_captura"] = ahora
                                candidato["guardado"] = True
                                texto = f"ID {tracker_id} | Pendiente guardado: {nombre_temporal}"
                        else:
                            texto = f"ID {tracker_id} | Desconocido | rostro muy pequeno"

                    resultados_actuales.append((x1, y1, x2, y2, texto, color))

            limpiar_tracks_antiguos(candidatos_desconocidos)
            limpiar_historial_reconocidos(historial_reconocidos)
            ultimos_resultados = resultados_actuales

        for x1, y1, x2, y2, texto, color in ultimos_resultados:
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(
                frame,
                texto,
                (x1, y1 - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                color,
                2
            )

        cv2.imshow("Witcam - Reconocimiento facial en tiempo real", frame)

        tecla = cv2.waitKey(1) & 0xFF
        if tecla == ord("q"):
            break

    camara.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
