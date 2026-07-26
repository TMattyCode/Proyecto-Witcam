class ErrorWitcam(Exception):
    """Error base del backend modular."""


class ErrorFuenteVideo(ErrorWitcam):
    """La fuente de video no se pudo abrir o dejo de responder."""


class ErrorGaleria(ErrorWitcam):
    """Una operacion sobre una galeria no pudo completarse."""
