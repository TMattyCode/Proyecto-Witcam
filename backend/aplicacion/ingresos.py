from datetime import datetime

from backend.aplicacion.autenticacion import ServicioAutenticacion
from backend.database.ingresos import RepositorioIngresos


class ServicioIngresos:
    def __init__(
        self,
        repositorio: RepositorioIngresos,
        autenticacion: ServicioAutenticacion,
    ):
        self.repositorio = repositorio
        self.autenticacion = autenticacion

    def listar(self, token: str, filtros: dict | None = None) -> dict:
        filtros = filtros or {}
        if not isinstance(filtros, dict):
            raise ValueError("Los parametros de ingresos no son validos")
        pagina = self._validar_entero(
            filtros.get("pagina", 1),
            "pagina",
            minimo=1,
        )
        limite = self._validar_entero(
            filtros.get("limite", 25),
            "limite",
            minimo=1,
            maximo=100,
        )
        filtros_validados = self._validar_filtros(filtros)
        sesion = self.autenticacion.obtener_sesion(token)
        id_cuenta = sesion["user"]["idCuenta"]
        return {
            "ok": True,
            **self.repositorio.listar(
                id_cuenta,
                pagina,
                limite,
                filtros_validados,
            ),
        }

    def listar_camaras(self, token: str) -> dict:
        sesion = self.autenticacion.obtener_sesion(token)
        id_cuenta = sesion["user"]["idCuenta"]
        return {
            "ok": True,
            "camaras": self.repositorio.listar_camaras(id_cuenta),
        }

    def _validar_filtros(self, filtros: dict) -> dict:
        fecha_desde = self._validar_fecha(
            filtros.get("fechaDesde"),
            "fechaDesde",
        )
        fecha_hasta = self._validar_fecha(
            filtros.get("fechaHasta"),
            "fechaHasta",
        )
        if (
            fecha_desde is not None
            and fecha_hasta is not None
            and fecha_desde > fecha_hasta
        ):
            raise ValueError(
                "La fecha inicial no puede ser posterior a la fecha final"
            )
        id_camara = None
        valor_camara = filtros.get("idCamara")
        if valor_camara not in (None, ""):
            id_camara = self._validar_entero(
                valor_camara,
                "idCamara",
                minimo=1,
            )
        return {
            "fecha_desde": fecha_desde,
            "fecha_hasta": fecha_hasta,
            "id_camara": id_camara,
        }

    @staticmethod
    def _validar_fecha(valor, nombre: str) -> datetime | None:
        if valor in (None, ""):
            return None
        if not isinstance(valor, str):
            raise ValueError(f"El parametro {nombre} no es valido")
        try:
            return datetime.fromisoformat(valor)
        except ValueError as error:
            raise ValueError(
                f"El parametro {nombre} no es valido"
            ) from error

    @staticmethod
    def _validar_entero(
        valor,
        nombre: str,
        minimo: int,
        maximo: int | None = None,
    ) -> int:
        try:
            numero = int(valor)
        except (TypeError, ValueError) as error:
            raise ValueError(
                f"El parametro {nombre} no es valido"
            ) from error
        if isinstance(valor, bool) or numero < minimo or (
            maximo is not None and numero > maximo
        ):
            raise ValueError(f"El parametro {nombre} no es valido")
        return numero
