from backend.dominio.modelos import Caja


def calcular_iou(caja_a: Caja, caja_b: Caja) -> float:
    ax1, ay1, ax2, ay2 = caja_a
    bx1, by1, bx2, by2 = caja_b

    inter_x1 = max(ax1, bx1)
    inter_y1 = max(ay1, by1)
    inter_x2 = min(ax2, bx2)
    inter_y2 = min(ay2, by2)

    inter_ancho = max(0, inter_x2 - inter_x1)
    inter_alto = max(0, inter_y2 - inter_y1)
    inter_area = inter_ancho * inter_alto
    area_a = max(0, ax2 - ax1) * max(0, ay2 - ay1)
    area_b = max(0, bx2 - bx1) * max(0, by2 - by1)
    union = area_a + area_b - inter_area
    return inter_area / union if union > 0 else 0.0
