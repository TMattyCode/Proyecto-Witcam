class ErrorWitcam(Exception):
    """Error base del backend modular."""


class ErrorFuenteVideo(ErrorWitcam):
    """La fuente de video no se pudo abrir o dejo de responder."""


class ErrorGaleria(ErrorWitcam):
    """Una operacion sobre una galeria no pudo completarse."""


class ErrorAutenticacion(ErrorWitcam):
    """Una operacion de autenticacion no pudo completarse."""


class CredencialesInvalidas(ErrorAutenticacion):
    """El usuario o la contrasena no son validos."""


class RegistroDuplicado(ErrorAutenticacion):
    """El usuario o correo ya se encuentran registrados."""
