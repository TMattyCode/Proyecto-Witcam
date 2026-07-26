from typing import Protocol

import numpy as np

from backend.dominio.modelos import (
    DeteccionPersona,
    DeteccionRostro,
    RostroModelo,
)


class DetectorPersonas(Protocol):
    def detectar(self, frame: np.ndarray) -> list[tuple[np.ndarray, float]]:
        """Devuelve cajas XYXY y confianzas de personas."""


class DetectorRostros(Protocol):
    def detectar(self, frame: np.ndarray) -> list[DeteccionRostro]:
        """Detecta rostros y sus cinco puntos faciales."""


class ReconocedorFacial(Protocol):
    def generar_embeddings(
        self,
        frame: np.ndarray,
        puntos_clave: list[np.ndarray],
    ) -> list[np.ndarray]:
        """Alinea rostros y genera sus embeddings."""

    def analizar(self, imagen: np.ndarray) -> list[RostroModelo]:
        """Detecta y reconoce todos los rostros de una imagen."""


class RastreadorObjetos(Protocol):
    def actualizar(
        self,
        cajas: list[np.ndarray],
        confianzas: list[float],
    ) -> list[DeteccionPersona]:
        """Actualiza IDs persistentes para un conjunto de cajas."""


class AnalizadorFrame(Protocol):
    def analizar(self, frame: np.ndarray) -> list[object]:
        """Punto de extension para modelos futuros."""
