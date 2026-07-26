from backend.container import construir_aplicacion


def main() -> None:
    aplicacion = construir_aplicacion()
    aplicacion.ejecutar()


if __name__ == "__main__":
    main()
