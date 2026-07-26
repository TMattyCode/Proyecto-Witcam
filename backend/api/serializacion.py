import json


def codificar_json(datos: object) -> bytes:
    return json.dumps(datos).encode("utf-8")
