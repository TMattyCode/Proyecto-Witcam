import time


def limpiar_historial(
    historial: dict,
    tolerancia: float,
) -> None:
    ahora = time.time()
    for clave, datos in list(historial.items()):
        ultimo_visto = (
            datos.get("ultimo_visto", 0)
            if isinstance(datos, dict)
            else getattr(datos, "ultimo_visto", 0)
        )
        if ahora - ultimo_visto > tolerancia:
            historial.pop(clave, None)
