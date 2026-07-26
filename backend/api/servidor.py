from http.server import ThreadingHTTPServer

from backend.config import ConfiguracionServidor


class ServidorWitcam:
    def __init__(
        self,
        config: ConfiguracionServidor,
        handler,
    ):
        self.config = config
        self.handler = handler
        self.servidor: ThreadingHTTPServer | None = None
        self._sirviendo = False

    @property
    def direccion(self) -> tuple[str, int]:
        if self.servidor is not None:
            return self.servidor.server_address
        return self.config.host, self.config.puerto

    def abrir(self) -> None:
        self.servidor = ThreadingHTTPServer(
            (self.config.host, self.config.puerto),
            self.handler,
        )

    def servir(self) -> None:
        try:
            self.abrir()
        except OSError:
            print(
                "No se pudo iniciar Witcam en "
                f"http://{self.config.host}:{self.config.puerto}/"
            )
            print(
                "Ese puerto probablemente esta ocupado por otro servidor, "
                "por ejemplo php -S."
            )
            print(
                "Cierra ese servidor con Ctrl+C y vuelve a ejecutar: "
                "python main.py"
            )
            return
        print(
            "Witcam web listo en "
            f"http://{self.config.host}:{self.config.puerto}/"
        )
        print("Abre esa URL en Chrome y presiona Iniciar.")
        print("Ctrl+C para salir.")
        try:
            self._sirviendo = True
            self.servidor.serve_forever()
        except KeyboardInterrupt:
            print("Cerrando Witcam...")
        finally:
            self._sirviendo = False
            self.cerrar()

    def cerrar(self) -> None:
        if self.servidor is not None:
            if self._sirviendo:
                self.servidor.shutdown()
                self._sirviendo = False
            self.servidor.server_close()
            self.servidor = None
