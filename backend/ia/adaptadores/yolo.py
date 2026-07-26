import numpy as np
from ultralytics import YOLO

from backend.config import ConfiguracionYolo


class DetectorYoloPersonas:
    def __init__(self, config: ConfiguracionYolo):
        self.config = config
        print("Cargando modelo YOLO de deteccion de personas...")
        self.modelo = YOLO(str(config.ruta_modelo))

    def detectar(self, frame: np.ndarray) -> list[tuple[np.ndarray, float]]:
        resultado = self.modelo.predict(
            frame,
            classes=[0],
            conf=self.config.confianza,
            imgsz=self.config.tamano_imagen,
            device="cpu",
            verbose=False,
        )[0]
        if resultado.boxes is None or len(resultado.boxes) == 0:
            return []
        cajas = resultado.boxes.xyxy.cpu().numpy().astype(np.float32)
        confianzas = resultado.boxes.conf.cpu().numpy().astype(np.float32)
        return [
            (caja, float(confianza))
            for caja, confianza in zip(cajas, confianzas)
        ]
