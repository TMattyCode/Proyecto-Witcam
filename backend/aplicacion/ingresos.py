from datetime import datetime

from backend.aplicacion.autenticacion import ServicioAutenticacion
from backend.database.ingresos import RepositorioIngresos
from backend.exceptions import ErrorGaleria
from backend.galerias.almacenamiento import AlmacenamientoPorCuenta
from backend.galerias.repositorio import RepositorioGalerias


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
        usuario = self.autenticacion.exigir_permiso(token, "ver_ingresos")
        id_cuenta = usuario["idCuenta"]
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
        usuario = self.autenticacion.exigir_permiso(token, "ver_ingresos")
        id_cuenta = usuario["idCuenta"]
        return {
            "ok": True,
            "camaras": self.repositorio.listar_camaras(id_cuenta),
        }

    def listar_alertas(self, token: str, limite=50) -> dict:
        limite_validado = self._validar_entero(
            limite, "limite", minimo=1, maximo=100
        )
        usuario = self.autenticacion.exigir_algun_permiso(
            token, {"ver_resumen", "ver_ingresos", "ver_observacion"}
        )
        return {
            "ok": True,
            "alertas": self.repositorio.listar_alertas(
                usuario["idCuenta"], limite_validado
            ),
        }

    def listar_ultimos(self, token: str, limite=5) -> dict:
        limite_validado = self._validar_entero(
            limite, "limite", minimo=1, maximo=20
        )
        usuario = self.autenticacion.exigir_algun_permiso(
            token, {"ver_resumen", "ver_ingresos"}
        )
        return {
            "ok": True,
            "ingresos": self.repositorio.listar_ultimos_ingresos(
                usuario["idCuenta"], limite_validado
            ),
        }

    def listar_historial(self, token: str, id_persona) -> dict:
        identificador = self._validar_entero(
            id_persona,
            "idPersona",
            minimo=1,
        )
        usuario = self.autenticacion.exigir_algun_permiso(
            token, {"ver_ingresos", "ver_observacion"}
        )
        historial = self.repositorio.listar_historial(
            usuario["idCuenta"],
            identificador,
        )
        if historial is None:
            raise ValueError("La persona no existe en esta cuenta")
        return {"ok": True, **historial}

    def obtener_rostro_deteccion(self, token: str, id_deteccion):
        identificador = self._validar_entero(
            id_deteccion,
            "idDeteccion",
            minimo=1,
        )
        usuario = self.autenticacion.exigir_algun_permiso(
            token, {"ver_ingresos", "ver_observacion"}
        )
        id_cuenta = usuario["idCuenta"]
        ruta = self.repositorio.obtener_ruta_imagen_deteccion(
            id_cuenta,
            identificador,
        )
        if ruta is None or self.almacenamiento is None:
            raise FileNotFoundError(
                "La deteccion no tiene un rostro disponible"
            )
        return self.almacenamiento.obtener_imagen_deteccion(
            id_cuenta,
            ruta,
        )

    def obtener_rostro(self, token: str, id_persona):
        identificador = self._validar_entero(
            id_persona,
            "idPersona",
            minimo=1,
        )
        usuario = self.autenticacion.exigir_algun_permiso(
            token, {"ver_ingresos", "ver_observacion"}
        )
        id_cuenta = usuario["idCuenta"]
        persona = self.repositorio.obtener_persona(
            id_cuenta,
            identificador,
        )
        if persona is None:
            raise ValueError("La persona no existe en esta cuenta")
        if self.almacenamiento is None:
            raise FileNotFoundError("La persona no tiene una muestra facial")
        return self.almacenamiento.obtener(
            id_cuenta
        ).obtener_portada_persona(
            id_cuenta,
            identificador,
            persona["nombre"],
        )

    def renombrar_persona(self, token: str, datos) -> dict:
        if not isinstance(datos, dict):
            raise ValueError("Los datos de la persona no son validos")
        id_persona = self._validar_entero(
            datos.get("idPersona"),
            "idPersona",
            minimo=1,
        )
        nombre_nuevo = datos.get("nombre")
        if not isinstance(nombre_nuevo, str):
            raise ValueError("El nombre de la persona no es valido")
        nombre_nuevo = nombre_nuevo.strip()
        if not nombre_nuevo:
            raise ValueError("El nombre de la persona no puede estar vacio")
        if len(nombre_nuevo) > 150:
            raise ValueError("El nombre no puede superar los 150 caracteres")
        try:
            nombre_seguro = RepositorioGalerias.nombre_persona_seguro(
                nombre_nuevo
            )
        except ErrorGaleria as error:
            raise ValueError("El nombre de la persona no es valido") from error
        if nombre_seguro != nombre_nuevo:
            raise ValueError(
                "El nombre solo puede contener letras, numeros, espacios, "
                "guiones y guiones bajos"
            )

        usuario = self.autenticacion.exigir_permiso(token, "gestionar_identidades")
        id_cuenta = usuario["idCuenta"]
        persona = self.repositorio.obtener_persona(id_cuenta, id_persona)
        if persona is None:
            raise ValueError("La persona no existe en esta cuenta")
        if persona["nombre"] == nombre_nuevo:
            return {
                "ok": True,
                "idPersona": id_persona,
                "nombrePersona": nombre_nuevo,
            }

        repositorio_galeria = (
            self.almacenamiento.obtener(id_cuenta)
            if self.almacenamiento is not None
            else None
        )
        renombrada = None
        if repositorio_galeria is None:
            anterior = self.repositorio.renombrar_persona(
                id_cuenta,
                id_persona,
                nombre_nuevo,
            )
        else:
            with repositorio_galeria.transaccion():
                renombrada = repositorio_galeria.renombrar_persona(
                    id_cuenta,
                    id_persona,
                    persona["nombre"],
                    nombre_nuevo,
                )
                try:
                    anterior = self.repositorio.renombrar_persona(
                        id_cuenta,
                        id_persona,
                        nombre_nuevo,
                    )
                except Exception:
                    if renombrada is not None:
                        tipo, nombre_anterior, nombre_actual = renombrada
                        repositorio_galeria.renombrar_persona(
                            id_cuenta,
                            id_persona,
                            nombre_actual,
                            nombre_anterior,
                        )
                    raise
        if anterior is None:
            if renombrada is not None:
                tipo, nombre_anterior, nombre_actual = renombrada
                repositorio_galeria.renombrar_persona(
                    id_cuenta,
                    id_persona,
                    nombre_actual,
                    nombre_anterior,
                )
            raise ValueError("La persona no existe en esta cuenta")
        return {
            "ok": True,
            "idPersona": id_persona,
            "nombrePersona": nombre_nuevo,
        }

    def agregar_lista_observacion(self, token: str, datos) -> dict:
        if not isinstance(datos, dict):
            raise ValueError("Los datos de la lista de observacion no son validos")
        id_persona = self._validar_entero(
            datos.get("idPersona"),
            "idPersona",
            minimo=1,
        )
        motivo = datos.get("motivo", "")
        if motivo is None:
            motivo = ""
        if not isinstance(motivo, str):
            raise ValueError("El motivo de observacion no es valido")
        motivo = motivo.strip()
        if len(motivo) > 500:
            raise ValueError("El motivo no puede superar los 500 caracteres")
        usuario = self.autenticacion.exigir_permiso(token, "gestionar_identidades")
        id_cuenta = usuario["idCuenta"]
        persona = self.repositorio.obtener_persona(id_cuenta, id_persona)
        if persona is None:
            raise ValueError("La persona no existe en esta cuenta")
        repositorio_galeria = (
            self.almacenamiento.obtener(id_cuenta)
            if self.almacenamiento is not None
            else None
        )
        if repositorio_galeria is None:
            agregado = self.repositorio.agregar_lista_observacion(
                id_cuenta,
                usuario["id"],
                id_persona,
                motivo,
            )
        else:
            with repositorio_galeria.transaccion():
                movida = repositorio_galeria.aprobar_persona(
                    id_cuenta,
                    id_persona,
                    persona["nombre"],
                )
                try:
                    agregado = self.repositorio.agregar_lista_observacion(
                        id_cuenta,
                        usuario["id"],
                        id_persona,
                        motivo,
                    )
                except Exception:
                    if movida is not None:
                        repositorio_galeria.devolver_persona_a_pendiente(
                            id_cuenta,
                            id_persona,
                            persona["nombre"],
                        )
                    raise
                if not agregado and movida is not None:
                    repositorio_galeria.devolver_persona_a_pendiente(
                        id_cuenta,
                        id_persona,
                        persona["nombre"],
                    )
        if not agregado:
            raise ValueError("La persona no existe en esta cuenta")
        return {
            "ok": True,
            "idPersona": id_persona,
            "enListaObservacion": True,
            "motivo": motivo,
        }

    def listar_observacion(
        self,
        token: str,
        parametros: dict | None = None,
    ) -> dict:
        parametros = parametros or {}
        pagina = self._validar_entero(
            parametros.get("pagina", 1),
            "pagina",
            minimo=1,
        )
        limite = self._validar_entero(
            parametros.get("limite", 25),
            "limite",
            minimo=1,
            maximo=100,
        )
        usuario = self.autenticacion.exigir_permiso(token, "ver_observacion")
        resultado = self.repositorio.listar_observacion(
            usuario["idCuenta"],
            pagina,
            limite,
        )
        return {"ok": True, **resultado}

    def quitar_lista_observacion(self, token: str, datos) -> dict:
        if not isinstance(datos, dict):
            raise ValueError("Los datos de la lista de observacion no son validos")
        id_persona = self._validar_entero(
            datos.get("idPersona"),
            "idPersona",
            minimo=1,
        )
        usuario = self.autenticacion.exigir_permiso(token, "gestionar_observacion")
        id_cuenta = usuario["idCuenta"]
        persona = self.repositorio.obtener_persona(id_cuenta, id_persona)
        if persona is None:
            raise ValueError("La persona no existe en esta cuenta")
        repositorio_galeria = (
            self.almacenamiento.obtener(id_cuenta)
            if self.almacenamiento is not None
            else None
        )
        if repositorio_galeria is None:
            quitada = self.repositorio.quitar_lista_observacion(
                id_cuenta,
                id_persona,
            )
        else:
            with repositorio_galeria.transaccion():
                movida = repositorio_galeria.devolver_persona_a_pendiente(
                    id_cuenta,
                    id_persona,
                    persona["nombre"],
                )
                try:
                    quitada = self.repositorio.quitar_lista_observacion(
                        id_cuenta,
                        id_persona,
                    )
                except Exception:
                    if movida is not None:
                        repositorio_galeria.aprobar_persona(
                            id_cuenta,
                            id_persona,
                            persona["nombre"],
                        )
                    raise
                if not quitada and movida is not None:
                    repositorio_galeria.aprobar_persona(
                        id_cuenta,
                        id_persona,
                        persona["nombre"],
                    )
        if not quitada:
            raise ValueError(
                "La persona no esta activa en la lista de observacion de esta cuenta"
            )
        return {
            "ok": True,
            "idPersona": id_persona,
            "enListaObservacion": False,
        }

    def eliminar_persona(self, token: str, datos) -> dict:
        if not isinstance(datos, dict):
            raise ValueError("Los datos de la persona no son validos")
        id_persona = self._validar_entero(
            datos.get("idPersona"),
            "idPersona",
            minimo=1,
        )
        usuario = self.autenticacion.exigir_permiso(token, "eliminar_identidades")
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
