from pathlib import Path

import cv2
import numpy as np

from backend.dominio.modelos import Caja


def normalizar_vector(vector: np.ndarray) -> np.ndarray:
    norma = np.linalg.norm(vector)
    return vector if norma == 0 else vector / norma


def leer_imagen(ruta: Path) -> np.ndarray | None:
    datos = np.fromfile(str(ruta), dtype=np.uint8)
    if datos.size == 0:
        return None
    return cv2.imdecode(datos, cv2.IMREAD_COLOR)


def escribir_jpg(ruta: Path, imagen: np.ndarray) -> None:
    correcto, datos = cv2.imencode(".jpg", imagen)
    if not correcto:
        raise RuntimeError("No se pudo codificar la muestra facial")
    datos.tofile(str(ruta))


def recortar_muestra(
    frame: np.ndarray,
    bbox: Caja,
    margen: int = 30,
) -> np.ndarray:
    x1, y1, x2, y2 = bbox
    x1 = max(0, int(x1) - margen)
    y1 = max(0, int(y1) - margen)
    x2 = min(frame.shape[1], int(x2) + margen)
    y2 = min(frame.shape[0], int(y2) + margen)
    return frame[y1:y2, x1:x2]


def calcular_calidad_muestra(imagen: np.ndarray | None) -> float:
    if imagen is None or imagen.size == 0:
        return 0.0
    alto, ancho = imagen.shape[:2]
    proporcion_tamano = min(1.0, (ancho * alto) / float(160 * 160))
    gris = cv2.cvtColor(imagen, cv2.COLOR_BGR2GRAY)
    nitidez = float(cv2.Laplacian(gris, cv2.CV_64F).var())
    proporcion_nitidez = min(1.0, nitidez / 300.0)
    return proporcion_tamano * 0.45 + proporcion_nitidez * 0.55
