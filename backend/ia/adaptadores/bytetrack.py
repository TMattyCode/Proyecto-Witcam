import numpy as np
import supervision as sv

from backend.dominio.modelos import DeteccionPersona


class RastreadorByteTrack:
    def __init__(
        self,
        umbral_activacion: float,
        fps: float,
    ):
        self.tracker = sv.ByteTrack(
            track_activation_threshold=umbral_activacion,
            lost_track_buffer=30,
            minimum_matching_threshold=0.8,
            frame_rate=max(1, fps),
            minimum_consecutive_frames=1,
        )

    def actualizar(
        self,
        cajas: list[np.ndarray],
        confianzas: list[float],
    ) -> list[DeteccionPersona]:
        if cajas:
            detecciones = sv.Detections(
                xyxy=np.asarray(cajas, dtype=np.float32),
                confidence=np.asarray(confianzas, dtype=np.float32),
                class_id=np.zeros(len(cajas), dtype=int),
            )
        else:
            detecciones = sv.Detections.empty()
        seguidas = self.tracker.update_with_detections(detecciones)
        if seguidas.tracker_id is None:
            return []
        return [
            DeteccionPersona(
                bbox=tuple(caja.astype(int)),
                tracker_id=int(tracker_id),
            )
            for caja, tracker_id in zip(
                seguidas.xyxy,
                seguidas.tracker_id,
            )
        ]
