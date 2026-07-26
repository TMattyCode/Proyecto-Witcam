import numpy as np
from insightface.app import FaceAnalysis
from insightface.utils import face_align

from backend.config import ConfiguracionRostro
from backend.dominio.modelos import DeteccionRostro, RostroModelo


class SesionInsightFace:
    """Comparte una sola instancia de FaceAnalysis entre detector y reconocedor."""

    def __init__(self, config: ConfiguracionRostro):
        print("Cargando modelo de reconocimiento facial...")
        self.modelo = FaceAnalysis(
            name="buffalo_l",
            allowed_modules=["detection", "recognition"],
            providers=["CPUExecutionProvider"],
        )
        self.modelo.prepare(
            ctx_id=-1,
            det_size=(config.tamano_detector, config.tamano_detector),
        )


class DetectorScrfd:
    def __init__(self, sesion: SesionInsightFace):
        self.sesion = sesion

    def detectar(self, frame: np.ndarray) -> list[DeteccionRostro]:
        cajas, puntos_clave = self.sesion.modelo.det_model.detect(
            frame,
            max_num=0,
            metric="default",
        )
        detecciones = []
        for indice, caja in enumerate(cajas):
            puntos = (
                np.asarray(puntos_clave[indice], dtype=np.float32)
                if puntos_clave is not None and indice < len(puntos_clave)
                else None
            )
            detecciones.append(
                DeteccionRostro(
                    bbox=tuple(caja[:4].astype(int)),
                    confianza=float(caja[4]),
                    puntos_clave=puntos,
                )
            )
        return detecciones


class ReconocedorInsightFace:
    def __init__(self, sesion: SesionInsightFace):
        self.sesion = sesion

    def generar_embeddings(
        self,
        frame: np.ndarray,
        puntos_clave: list[np.ndarray],
    ) -> list[np.ndarray]:
        if not puntos_clave:
            return []
        recortes = [
            face_align.norm_crop(
                frame,
                landmark=puntos,
                image_size=112,
            )
            for puntos in puntos_clave
        ]
        embeddings = self.sesion.modelo.models["recognition"].get_feat(
            recortes
        )
        return [np.asarray(embedding) for embedding in embeddings]

    def analizar(self, imagen: np.ndarray) -> list[RostroModelo]:
        rostros = self.sesion.modelo.get(imagen)
        return [
            RostroModelo(
                bbox=tuple(rostro.bbox.astype(int)),
                confianza=float(rostro.det_score),
                puntos_clave=(
                    np.asarray(rostro.kps, dtype=np.float32)
                    if rostro.kps is not None
                    else None
                ),
                embedding=np.asarray(rostro.embedding),
            )
            for rostro in rostros
        ]
