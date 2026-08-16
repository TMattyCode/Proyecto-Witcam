from datetime import datetime

from backend.aplicacion.autenticacion import ServicioAutenticacion
from backend.database.ingresos import RepositorioIngresos
from backend.galerias.almacenamiento import AlmacenamientoPorCuenta


class ServicioIngresos:
    def __init__(
        self,
        repositorio: RepositorioIngresos,
        autenticacion: ServicioAutenticacion,
        almacenamiento: AlmacenamientoPorCuenta | None = None,
    ):
        self.repositorio = repositorio
        self.autenticacion = autenticacion
        self.almacenamiento = almacenamiento

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

    def listar_historial(self, token: str, id_persona) -> dict:
        identificador = self._validar_entero(
            id_persona,
            "idPersona",
            minimo=1,
        )
        sesion = self.autenticacion.obtener_sesion(token)
        historial = self.repositorio.listar_historial(
            sesion["user"]["idCuenta"],
            identificador,
        )
        if historial is None:
            raise ValueError("La persona no existe en esta cuenta")
        return {"ok": True, **historial}

    def agregar_lista_observacion(self, token: str, datos) -> dict:
        if not isinstance(datos, dict):
            raise ValueError("Los datos de la lista de observacion no son validos")
        id_persona = self._validar_entero(
            datos.get("idPersona"),
            "idPersona",
            minimo=1,
        )
        usuario = self.autenticacion.obtener_sesion(token)["user"]
        if not self.repositorio.agregar_lista_observacion(
            usuario["idCuenta"],
            usuario["id"],
            id_persona,
            "En progreso",
        ):
            raise ValueError("La persona no existe en esta cuenta")
        return {
            "ok": True,
            "idPersona": id_persona,
            "enListaObservacion": True,
            "motivo": "En progreso",
        }

    def listar_observacion(self, token: str) -> dict:
        usuario = self.autenticacion.obtener_sesion(token)["user"]
        registros = self.repositorio.listar_observacion(
            usuario["idCuenta"]
        )
        return {"ok": True, "registros": registros, "total": len(registros)}

    def eliminar_persona(self, token: str, datos) -> dict:
        if not isinstance(datos, dict):
            raise ValueError("Los datos de la persona no son validos")
        id_persona = self._validar_entero(
            datos.get("idPersona"),
            "idPersona",
            minimo=1,
        )
        usuario = self.autenticacion.exigir_permiso(token, "eliminar")
        id_cuenta = usuario["idCuenta"]
        if self.almacenamiento is None:
            resultado = self.repositorio.eliminar_persona(
                id_cuenta,
                id_persona,
            )
        else:
            repositorio_galeria = self.almacenamiento.obtener(id_cuenta)
            with repositorio_galeria.transaccion():
                resultado = self.repositorio.eliminar_persona(
                    id_cuenta,
                    id_persona,
                )
                if resultado is not None:
                    self.almacenamiento.eliminar_archivos_persona(
                        id_cuenta,
                        resultado.id_persona,
                        resultado.nombre,
                        resultado.rutas_archivos,
                    )
        if resultado is None:
            raise ValueError("La persona no existe en esta cuenta")
        return {
            "ok": True,
            "idPersona": resultado.id_persona,
            "nombrePersona": resultado.nombre,
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
