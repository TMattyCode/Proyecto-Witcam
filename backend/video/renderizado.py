import cv2
import numpy as np

from backend.config import ConfiguracionVideo
from backend.dominio.modelos import ResultadoVisual


def dibujar_resultados(
    frame: np.ndarray,
    resultados: list[ResultadoVisual],
) -> None:
    for resultado in resultados:
        x1, y1, x2, y2 = resultado.bbox
        cv2.rectangle(frame, (x1, y1), (x2, y2), resultado.color, 2)
        cv2.putText(
            frame,
            resultado.texto,
            (x1, max(y1 - 10, 20)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            resultado.color,
            2,
        )


def ajustar_para_web(
    frame: np.ndarray,
    config: ConfiguracionVideo,
) -> np.ndarray:
    alto, ancho = frame.shape[:2]
    factor = min(
        1.0,
        config.ancho_maximo_web / ancho,
        config.alto_maximo_web / alto,
    )
    if factor >= 1.0:
        return frame
    return cv2.resize(
        frame,
        (max(1, round(ancho * factor)), max(1, round(alto * factor))),
        interpolation=cv2.INTER_AREA,
    )


def codificar_jpeg(
    frame: np.ndarray,
    config: ConfiguracionVideo,
) -> bytes | None:
    correcto, buffer = cv2.imencode(
        ".jpg",
        frame,
        [int(cv2.IMWRITE_JPEG_QUALITY), config.calidad_jpeg],
    )
    return buffer.tobytes() if correcto else None


def crear_frame_mensaje(
    mensaje: str,
    config: ConfiguracionVideo,
) -> bytes:
    frame = np.zeros(
        (config.alto_maximo_web, config.ancho_maximo_web, 3),
        dtype=np.uint8,
    )
    frame[:] = (24, 34, 30)
    escala = 1.25
    grosor = 2
    (ancho_texto, alto_texto), _ = cv2.getTextSize(
        mensaje,
        cv2.FONT_HERSHEY_SIMPLEX,
        escala,
        grosor,
    )
    origen = (
        max(24, (config.ancho_maximo_web - ancho_texto) // 2),
        (config.alto_maximo_web + alto_texto) // 2,
    )
    cv2.putText(
        frame,
        mensaje,
        origen,
        cv2.FONT_HERSHEY_SIMPLEX,
        escala,
        (255, 255, 255),
        grosor,
    )
    correcto, buffer = cv2.imencode(".jpg", frame)
    return buffer.tobytes() if correcto else b""
