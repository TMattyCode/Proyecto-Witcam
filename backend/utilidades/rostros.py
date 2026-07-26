import numpy as np

from backend.config import ConfiguracionRostro
from backend.dominio.modelos import Caja


def evaluar_calidad_rostro(
    caja: Caja,
    puntos_clave: np.ndarray | None,
    confianza: float,
    config: ConfiguracionRostro,
    validar_tamano_confianza: bool = True,
) -> tuple[bool, str | None]:
    x1, y1, x2, y2 = caja
    ancho = x2 - x1
    alto = y2 - y1
    if validar_tamano_confianza:
        if ancho < config.ancho_minimo or alto < config.alto_minimo:
            return False, "rostro muy pequeno"
        if confianza < config.confianza_minima:
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

    medio_ojos = (ojo_izquierdo + ojo_derecho) / 2.0
    medio_boca = (boca_izquierda + boca_derecha) / 2.0
    distancia_nariz_izquierda = float(np.linalg.norm(nariz - ojo_izquierdo))
    distancia_nariz_derecha = float(np.linalg.norm(nariz - ojo_derecho))
    distancia_mayor = max(distancia_nariz_izquierda, distancia_nariz_derecha)
    simetria = (
        min(distancia_nariz_izquierda, distancia_nariz_derecha)
        / distancia_mayor
        if distancia_mayor > 0
        else 0.0
    )
    eje_ojos_normalizado = eje_ojos / distancia_ojos
    eje_vertical = np.array(
        [-eje_ojos_normalizado[1], eje_ojos_normalizado[0]],
        dtype=np.float32,
    )
    if eje_vertical[1] < 0:
        eje_vertical *= -1
    descenso_nariz = float(np.dot(nariz - medio_ojos, eje_vertical))
    descenso_boca = float(np.dot(medio_boca - nariz, eje_vertical))
    proporcion_boca = (
        float(np.linalg.norm(boca_derecha - boca_izquierda)) / distancia_ojos
    )
    balance_vertical = (
        min(descenso_nariz, descenso_boca) / max(descenso_nariz, descenso_boca)
        if descenso_nariz > 0 and descenso_boca > 0
        else 0.0
    )
    desviacion_nariz = abs(
        float(np.dot(nariz - medio_ojos, eje_ojos_normalizado))
    ) / distancia_ojos

    if descenso_nariz / distancia_ojos > config.descenso_maximo_nariz:
        return False, "mirada demasiado baja"
    if distancia_ojos / max(ancho, 1.0) < config.proporcion_minima_ojos:
        return False, "puntos faciales poco fiables"
    if (
        descenso_nariz / distancia_ojos < config.descenso_minimo_nariz
        or descenso_boca / distancia_ojos < config.descenso_minimo_boca
        or proporcion_boca < config.proporcion_minima_boca
        or balance_vertical < config.balance_vertical_minimo
    ):
        return False, "componentes faciales incompletos"
    if (
        simetria < config.simetria_minima
        or desviacion_nariz > config.desviacion_maxima_nariz
    ):
        return False, "angulo insuficiente"
    return True, None
