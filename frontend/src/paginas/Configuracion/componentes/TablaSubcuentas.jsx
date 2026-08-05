import { useDeferredValue, useEffect, useRef, useState } from "react";

import {
  actualizarEstadoSubusuario,
  crearSubusuario,
  editarSubusuario,
  obtenerSubusuarios,
} from "../../../servicios/api";
import {
  validarEdicionSubusuario,
  validarSubusuario,
} from "../../../utilidades/validacionAutenticacion";
import iconoOjo from "../../../assets/iconos/008 icono-ojo-sinrelleno.png";
import "./TablaSubcuentas.css";

const FORMULARIO_INICIAL = {
  nombre: "",
  apellido: "",
  nombreUsuario: "",
  correo: "",
  telefono: "",
  contrasena: "",
  confirmarContrasena: "",
  permisos: [],
};

const FILTROS_INICIALES = {
  usuario: "",
  permiso: "",
  registroDesde: "",
  registroHasta: "",
  accesoDesde: "",
  accesoHasta: "",
  sinAcceso: false,
};

const FORMATEADOR_FECHA = new Intl.DateTimeFormat("es-CL", {
  day: "2-digit",
  month: "2-digit",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
  hour12: false,
});

function formatearFecha(fecha, textoVacio) {
  if (!fecha) return textoVacio;
  const valor = new Date(fecha);
  return Number.isNaN(valor.getTime())
    ? "No disponible"
    : FORMATEADOR_FECHA.format(valor);
}

function formatearFechaFiltro(fecha) {
  if (!fecha) return "";
  const [anio, mes, dia] = fecha.split("-");
  return `${dia}-${mes}-${anio}`;
}

function IconoDesactivar() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <circle cx="9" cy="8" r="3.25" />
      <path d="M3.5 19c.4-3.1 2.2-5 5.5-5 2.2 0 3.8.8 4.7 2.3" />
      <path d="M15.5 17.5h5" />
    </svg>
  );
}

function IndicadorPermiso({ activo, nombre }) {
  return (
    <span
      className={`permiso ${activo ? "permiso-activo" : "permiso-inactivo"}`}
      aria-label={`${nombre}: ${activo ? "permitido" : "no permitido"}`}
      title={`${nombre}: ${activo ? "permitido" : "no permitido"}`}
    >
      {activo ? "✓" : "×"}
    </span>
  );
}

function CampoPassword({ label, name, value, onChange, required = true }) {
  const [visible, setVisible] = useState(false);

  return (
    <label>
      <span>{label}</span>
      <div className="campo-password-subusuario">
        <input
          type={visible ? "text" : "password"}
          name={name}
          value={value}
          onChange={onChange}
          minLength={8}
          maxLength={128}
          autoComplete="new-password"
          required={required}
        />
        <button
          type="button"
          className={visible ? "password-visible" : ""}
          onClick={() => setVisible((actual) => !actual)}
          aria-label={visible ? "Ocultar contraseña" : "Mostrar contraseña"}
          aria-pressed={visible}
          title={visible ? "Ocultar contraseña" : "Mostrar contraseña"}
        >
          <img src={iconoOjo} alt="" />
        </button>
      </div>
    </label>
  );
}

function ModalSubusuario({ permisos, subusuario, onCerrar, onGuardado }) {
  const editando = Boolean(subusuario);
  const [formulario, setFormulario] = useState(() =>
    subusuario
      ? {
          nombre: subusuario.nombre,
          apellido: subusuario.apellido,
          nombreUsuario: subusuario.nombreUsuario,
          correo: subusuario.correo,
          telefono: subusuario.telefono || "",
          contrasena: "",
          confirmarContrasena: "",
          permisos: [...subusuario.permisos],
        }
      : FORMULARIO_INICIAL,
  );
  const [error, setError] = useState("");
  const [enviando, setEnviando] = useState(false);
  const envioEnCurso = useRef(false);

  const actualizarCampo = (evento) => {
    const { name, value } = evento.target;
    setFormulario((actual) => ({ ...actual, [name]: value }));
  };

  const alternarPermiso = (codigo) => {
    setFormulario((actual) => ({
      ...actual,
      permisos: actual.permisos.includes(codigo)
        ? actual.permisos.filter((permiso) => permiso !== codigo)
        : [...actual.permisos, codigo],
    }));
  };

  const guardar = async (evento) => {
    evento.preventDefault();
    if (envioEnCurso.current) return;
    envioEnCurso.current = true;
    setEnviando(true);
    setError("");
    try {
      const respuesta = editando
        ? await editarSubusuario(
            validarEdicionSubusuario({ ...formulario, id: subusuario.id }),
          )
        : await crearSubusuario(validarSubusuario(formulario));
      onGuardado(respuesta.subusuario);
    } catch (errorSolicitud) {
      setError(errorSolicitud.message);
    } finally {
      envioEnCurso.current = false;
      setEnviando(false);
    }
  };

  return (
    <div
      className="modal-subusuario-fondo"
      role="presentation"
      onMouseDown={(evento) => {
        if (evento.target === evento.currentTarget) onCerrar();
      }}
    >
      <form
        className="modal-subusuario"
        role="dialog"
        aria-modal="true"
        aria-labelledby="titulo-formulario-subusuario"
        onSubmit={guardar}
      >
        <div className="modal-subusuario-cabecera">
          <div>
            <span>Gestión de accesos</span>
            <h2 id="titulo-formulario-subusuario">
              {editando ? "Editar subusuario" : "Añadir subusuario"}
            </h2>
            <p>
              {editando
                ? `Actualiza los datos y permisos de ${subusuario.nombreUsuario}.`
                : "Pertenecerá al mismo negocio o empresa del administrador."}
            </p>
          </div>
          <button type="button" aria-label="Cerrar" onClick={onCerrar}>×</button>
        </div>

        <div className="modal-subusuario-campos">
          <label>
            <span>Nombre</span>
            <input
              name="nombre"
              value={formulario.nombre}
              onChange={actualizarCampo}
              maxLength={100}
              autoComplete="given-name"
              autoFocus
              required
            />
          </label>
          <label>
            <span>Apellido</span>
            <input
              name="apellido"
              value={formulario.apellido}
              onChange={actualizarCampo}
              maxLength={100}
              autoComplete="family-name"
              required
            />
          </label>
          <label>
            <span>Nombre de usuario</span>
            <input
              name="nombreUsuario"
              value={formulario.nombreUsuario}
              onChange={actualizarCampo}
              maxLength={100}
              autoComplete="off"
              required
            />
          </label>
          <label>
            <span>Correo electrónico</span>
            <input
              type="email"
              name="correo"
              value={formulario.correo}
              onChange={actualizarCampo}
              maxLength={250}
              autoComplete="off"
              required
            />
          </label>
          <label>
            <span>Teléfono <small>(opcional)</small></span>
            <input
              type="tel"
              name="telefono"
              value={formulario.telefono}
              onChange={actualizarCampo}
              maxLength={20}
              autoComplete="off"
            />
          </label>
          <div className="modal-subusuario-cuenta">
            <span>Rol asignado</span>
            <strong>Subusuario</strong>
          </div>
          <CampoPassword
            label={editando ? "Nueva contraseña (opcional)" : "Contraseña inicial"}
            name="contrasena"
            value={formulario.contrasena}
            onChange={actualizarCampo}
            required={!editando}
          />
          <CampoPassword
            label={editando ? "Confirmar nueva contraseña" : "Confirmar contraseña"}
            name="confirmarContrasena"
            value={formulario.confirmarContrasena}
            onChange={actualizarCampo}
            required={!editando}
          />
        </div>

        <fieldset className="modal-subusuario-permisos">
          <legend>Permisos disponibles</legend>
          {permisos.length ? (
            <div className="permisos-opciones">
              {permisos.map((permiso) => (
                <label key={permiso.codigo} title={permiso.descripcion || ""}>
                  <input
                    type="checkbox"
                    checked={formulario.permisos.includes(permiso.codigo)}
                    onChange={() => alternarPermiso(permiso.codigo)}
                  />
                  <span>
                    <strong>{permiso.nombre}</strong>
                    {permiso.descripcion && <small>{permiso.descripcion}</small>}
                  </span>
                </label>
              ))}
            </div>
          ) : (
            <p>No hay permisos configurados en la base de datos.</p>
          )}
        </fieldset>

        {error && <div className="modal-subusuario-error" role="alert">{error}</div>}

        <div className="modal-subusuario-acciones">
          <button type="button" onClick={onCerrar}>Cancelar</button>
          <button type="submit" disabled={enviando}>
            {enviando
              ? editando ? "Guardando..." : "Creando..."
              : editando ? "Guardar cambios" : "Crear subusuario"}
          </button>
        </div>
      </form>
    </div>
  );
}

function ModalConfirmacionEstado({
  subusuario,
  activar,
  procesando,
  onCancelar,
  onConfirmar,
}) {
  const accion = activar ? "reactivar" : "desactivar";

  return (
    <div
      className="modal-subusuario-fondo"
      role="presentation"
      onMouseDown={(evento) => {
        if (evento.target === evento.currentTarget && !procesando) onCancelar();
      }}
    >
      <section
        className="modal-confirmacion-estado"
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="titulo-confirmacion-estado"
        aria-describedby="detalle-confirmacion-estado"
      >
        <div className={`modal-confirmacion-icono ${activar ? "reactivar" : "desactivar"}`}>
          {activar ? "↻" : "!"}
        </div>
        <p className="modal-confirmacion-etiqueta">Confirmar acción</p>
        <h2 id="titulo-confirmacion-estado">
          ¿Deseas {accion} este subusuario?
        </h2>
        <p id="detalle-confirmacion-estado">
          El usuario <strong>{subusuario.nombreUsuario}</strong>
          {activar
            ? " podrá volver a iniciar sesión y usar sus permisos asignados."
            : " perderá el acceso inmediatamente, pero sus datos e historial se conservarán."}
        </p>
        <div className="modal-confirmacion-acciones">
          <button type="button" onClick={onCancelar} disabled={procesando} autoFocus>
            No, cancelar
          </button>
          <button
            type="button"
            className={activar ? "confirmar-reactivacion" : "confirmar-desactivacion"}
            onClick={onConfirmar}
            disabled={procesando}
          >
            {procesando
              ? "Procesando..."
              : `Sí, ${activar ? "reactivar" : "desactivar"}`}
          </button>
        </div>
      </section>
    </div>
  );
}

function TablaSubusuarios({ onSubusuariosCambiaron }) {
  const [subusuarios, setSubusuarios] = useState([]);
  const [permisos, setPermisos] = useState([]);
  const [cargando, setCargando] = useState(true);
  const [cargaInicialCompletada, setCargaInicialCompletada] = useState(false);
  const [error, setError] = useState("");
  const [modalAbierto, setModalAbierto] = useState(false);
  const [filtroEstado, setFiltroEstado] = useState("activo");
  const [actualizandoId, setActualizandoId] = useState(null);
  const [subusuarioConfirmacion, setSubusuarioConfirmacion] = useState(null);
  const [subusuarioEdicion, setSubusuarioEdicion] = useState(null);
  const [filtros, setFiltros] = useState(FILTROS_INICIALES);
  const filtrosDiferidos = useDeferredValue(filtros);
  const [pagina, setPagina] = useState(1);
  const [total, setTotal] = useState(0);
  const [versionConsulta, setVersionConsulta] = useState(0);
  const [mostrarFiltrosAvanzados, setMostrarFiltrosAvanzados] = useState(false);
  const limite = 25;
  const totalPaginas = Math.max(1, Math.ceil(total / limite));

  useEffect(() => {
    let activo = true;
    obtenerSubusuarios({
      estado: filtroEstado,
      ...filtrosDiferidos,
      pagina,
      limite,
    })
      .then((datos) => {
        if (activo) {
          setSubusuarios(datos.subusuarios);
          setPermisos(datos.permisos);
          setTotal(datos.total);
          setError("");
        }
      })
      .catch((errorSolicitud) => {
        if (activo) setError(errorSolicitud.message);
      })
      .finally(() => {
        if (activo) {
          setCargando(false);
          setCargaInicialCompletada(true);
        }
      });
    return () => {
      activo = false;
    };
  }, [filtroEstado, filtrosDiferidos, pagina, versionConsulta]);

  const seleccionarFiltro = (estado) => {
    if (estado === filtroEstado) return;
    setCargando(true);
    setError("");
    setPagina(1);
    setFiltroEstado(estado);
  };

  const actualizarFiltro = (evento) => {
    const { name, type, checked, value } = evento.target;
    setCargando(true);
    setError("");
    setPagina(1);
    setFiltros((actuales) => {
      const siguientes = {
        ...actuales,
        [name]: type === "checkbox" ? checked : value,
      };
      if (name === "sinAcceso" && checked) {
        siguientes.accesoDesde = "";
        siguientes.accesoHasta = "";
      }
      if ((name === "accesoDesde" || name === "accesoHasta") && value) {
        siguientes.sinAcceso = false;
      }
      return siguientes;
    });
  };

  const limpiarFiltros = () => {
    setCargando(true);
    setError("");
    setPagina(1);
    setFiltros(FILTROS_INICIALES);
    setMostrarFiltrosAvanzados(false);
    setVersionConsulta((version) => version + 1);
  };

  const quitarFiltro = (clave) => {
    setCargando(true);
    setError("");
    setPagina(1);
    setFiltros((actuales) => {
      if (clave === "registro") {
        return { ...actuales, registroDesde: "", registroHasta: "" };
      }
      if (clave === "acceso") {
        return { ...actuales, accesoDesde: "", accesoHasta: "" };
      }
      return {
        ...actuales,
        [clave]: clave === "sinAcceso" ? false : "",
      };
    });
  };

  const cambiarPagina = (nuevaPagina) => {
    if (nuevaPagina < 1 || nuevaPagina > totalPaginas) return;
    setCargando(true);
    setPagina(nuevaPagina);
  };

  const incorporarSubusuario = () => {
    setCargando(true);
    setPagina(1);
    setFiltroEstado("activo");
    setVersionConsulta((version) => version + 1);
    setModalAbierto(false);
    onSubusuariosCambiaron?.();
  };

  const incorporarEdicion = () => {
    setCargando(true);
    setVersionConsulta((version) => version + 1);
    setSubusuarioEdicion(null);
  };

  const cambiarEstado = async (subusuario) => {
    const activar = subusuario.estado === "Inactivo";
    setActualizandoId(subusuario.id);
    setError("");
    try {
      await actualizarEstadoSubusuario(
        subusuario.id,
        activar ? "activo" : "inactivo",
      );
      setCargando(true);
      setPagina(1);
      setVersionConsulta((version) => version + 1);
      onSubusuariosCambiaron?.();
    } catch (errorSolicitud) {
      setError(errorSolicitud.message);
    } finally {
      setActualizandoId(null);
      setSubusuarioConfirmacion(null);
    }
  };

  const permisoSeleccionado = permisos.find(
    (permiso) => permiso.codigo === filtros.permiso,
  );
  const filtrosAplicados = [
    filtros.usuario && { clave: "usuario", texto: `Usuario: ${filtros.usuario}` },
    filtros.permiso && {
      clave: "permiso",
      texto: `Permiso: ${permisoSeleccionado?.nombre || filtros.permiso}`,
    },
    (filtros.registroDesde || filtros.registroHasta) && {
      clave: "registro",
      texto: `Registro: ${formatearFechaFiltro(filtros.registroDesde) || "inicio"} a ${formatearFechaFiltro(filtros.registroHasta) || "hoy"}`,
    },
    (filtros.accesoDesde || filtros.accesoHasta) && {
      clave: "acceso",
      texto: `Último acceso: ${formatearFechaFiltro(filtros.accesoDesde) || "inicio"} a ${formatearFechaFiltro(filtros.accesoHasta) || "hoy"}`,
    },
    filtros.sinAcceso && {
      clave: "sinAcceso",
      texto: "Nunca se ha conectado",
    },
  ].filter(Boolean);
  const cantidadFiltrosAvanzados = [
    filtros.registroDesde || filtros.registroHasta,
    filtros.accesoDesde || filtros.accesoHasta,
    filtros.sinAcceso,
  ].filter(Boolean).length;

  return (
    <section className="configuracion-tarjeta configuracion-subcuentas">
      <div className="subcuentas-encabezado">
        <div className="subcuentas-titulo">
          <div className="configuracion-icono configuracion-icono-subcuentas">👥</div>
          <div>
            <h2>Subusuarios</h2>
            <p>Administra los subusuarios y asigna los permisos disponibles.</p>
          </div>
        </div>
        <button
          className="boton-anadir-subcuenta"
          type="button"
          onClick={() => setModalAbierto(true)}
          disabled={cargando || Boolean(error)}
        >
          <span>+</span>
          Añadir subusuario
        </button>
      </div>

      <div className="subusuarios-filtros" aria-label="Filtrar subusuarios por estado">
        <button
          type="button"
          className={filtroEstado === "activo" ? "seleccionado" : ""}
          aria-pressed={filtroEstado === "activo"}
          onClick={() => seleccionarFiltro("activo")}
        >
          Activos
        </button>
        <button
          type="button"
          className={filtroEstado === "inactivo" ? "seleccionado" : ""}
          aria-pressed={filtroEstado === "inactivo"}
          onClick={() => seleccionarFiltro("inactivo")}
        >
          Inactivos
        </button>
      </div>

      <div className="subusuarios-filtros-principales">
        <label className="filtro-usuario">
          <span>Buscar usuario</span>
          <input
            type="search"
            name="usuario"
            value={filtros.usuario}
            onChange={actualizarFiltro}
            placeholder="Ejemplo: matias"
            maxLength={100}
          />
        </label>
        <label>
          <span>Permiso</span>
          <select name="permiso" value={filtros.permiso} onChange={actualizarFiltro}>
            <option value="">Cualquier permiso</option>
            {permisos.map((permiso) => (
              <option key={permiso.codigo} value={permiso.codigo}>
                {permiso.nombre}
              </option>
            ))}
          </select>
        </label>
        <div className="filtros-acciones">
          <button
            className={`boton-mas-filtros ${mostrarFiltrosAvanzados ? "abierto" : ""}`}
            type="button"
            aria-expanded={mostrarFiltrosAvanzados}
            onClick={() => setMostrarFiltrosAvanzados((visible) => !visible)}
          >
            Más filtros{cantidadFiltrosAvanzados ? ` (${cantidadFiltrosAvanzados})` : ""}
            <svg viewBox="0 0 20 20" aria-hidden="true">
              <path d="m5 7.5 5 5 5-5" />
            </svg>
          </button>
          <button
            className="boton-limpiar-filtros"
            type="button"
            onClick={limpiarFiltros}
            disabled={!filtrosAplicados.length}
          >
            Limpiar
          </button>
        </div>
      </div>

      {mostrarFiltrosAvanzados && (
        <div className="subusuarios-filtros-avanzados">
          <fieldset>
            <legend>Fecha de registro</legend>
            <input
              type="date"
              name="registroDesde"
              value={filtros.registroDesde}
              max={filtros.registroHasta || undefined}
              onChange={actualizarFiltro}
              aria-label="Registro desde"
            />
            <span>a</span>
            <input
              type="date"
              name="registroHasta"
              value={filtros.registroHasta}
              min={filtros.registroDesde || undefined}
              onChange={actualizarFiltro}
              aria-label="Registro hasta"
            />
          </fieldset>
          <fieldset>
            <legend>Última conexión</legend>
            <input
              type="date"
              name="accesoDesde"
              value={filtros.accesoDesde}
              max={filtros.accesoHasta || undefined}
              disabled={filtros.sinAcceso}
              onChange={actualizarFiltro}
              aria-label="Última conexión desde"
            />
            <span>a</span>
            <input
              type="date"
              name="accesoHasta"
              value={filtros.accesoHasta}
              min={filtros.accesoDesde || undefined}
              disabled={filtros.sinAcceso}
              onChange={actualizarFiltro}
              aria-label="Última conexión hasta"
            />
          </fieldset>
          <label className="filtro-sin-acceso">
            <input
              type="checkbox"
              name="sinAcceso"
              checked={filtros.sinAcceso}
              onChange={actualizarFiltro}
            />
            <span>Nunca se ha conectado</span>
          </label>
        </div>
      )}

      {filtrosAplicados.length > 0 && (
        <div className="subusuarios-filtros-aplicados" aria-label="Filtros aplicados">
          <span>Filtros aplicados</span>
          {filtrosAplicados.map((filtro) => (
            <button
              type="button"
              key={filtro.clave}
              onClick={() => quitarFiltro(filtro.clave)}
              title={`Quitar ${filtro.texto}`}
            >
              {filtro.texto} <span aria-hidden="true">×</span>
            </button>
          ))}
        </div>
      )}

      {error && <div className="subusuarios-error" role="alert">{error}</div>}

      <div className="subcuentas-tabla-contenedor">
        <table
          className="subcuentas-tabla tabla-subusuarios-dinamica"
          aria-busy={cargando}
        >
          <thead>
            <tr>
              <th>Usuario</th>
              <th>Correo electrónico</th>
              <th>Fecha de registro</th>
              <th>Última conexión</th>
              <th>Estado</th>
              {permisos.map((permiso) => (
                <th key={permiso.codigo} title={permiso.descripcion || ""}>
                  {permiso.nombre}
                </th>
              ))}
              <th>Acciones</th>
            </tr>
          </thead>
          <tbody className={cargando && cargaInicialCompletada ? "actualizando" : ""}>
            {!cargaInicialCompletada ? (
              <tr><td colSpan={6 + permisos.length} className="subcuentas-vacia">Cargando subusuarios...</td></tr>
            ) : subusuarios.length === 0 ? (
              <tr>
                <td colSpan={6 + permisos.length} className="subcuentas-vacia">
                  No hay subusuarios {filtroEstado === "activo" ? "activos" : "inactivos"}.
                </td>
              </tr>
            ) : (
              subusuarios.map((subusuario) => (
                <tr key={subusuario.id}>
                  <td>{subusuario.nombreUsuario}</td>
                  <td><span className="subcuenta-texto-recortado" title={subusuario.correo}>{subusuario.correo}</span></td>
                  <td className="subusuario-fecha">
                    {formatearFecha(subusuario.fechaCreacion, "No disponible")}
                  </td>
                  <td className="subusuario-fecha">
                    {formatearFecha(subusuario.ultimoAcceso, "Nunca")}
                  </td>
                  <td><span className={`estado-subusuario ${subusuario.estado === "Activo" ? "activo" : "inactivo"}`}>{subusuario.estado}</span></td>
                  {permisos.map((permiso) => (
                    <td key={permiso.codigo}>
                      <IndicadorPermiso
                        activo={subusuario.permisos.includes(permiso.codigo)}
                        nombre={permiso.nombre}
                      />
                    </td>
                  ))}
                  <td>
                    <div className="subcuenta-acciones">
                      {subusuario.estado === "Activo" && (
                        <button
                          className="boton-accion boton-accion-editar"
                          type="button"
                          onClick={() => setSubusuarioEdicion(subusuario)}
                          aria-label={`Editar al usuario ${subusuario.nombreUsuario}`}
                          title="Editar subusuario"
                        >
                          ✎
                        </button>
                      )}
                      <button
                        className={`boton-accion ${subusuario.estado === "Activo" ? "boton-accion-eliminar" : "boton-accion-reactivar"}`}
                        type="button"
                        disabled={actualizandoId === subusuario.id}
                        onClick={() => setSubusuarioConfirmacion(subusuario)}
                        aria-label={`${subusuario.estado === "Activo" ? "Desactivar" : "Reactivar"} al usuario ${subusuario.nombreUsuario}`}
                        title={subusuario.estado === "Activo" ? "Desactivar subusuario" : "Reactivar subusuario"}
                      >
                        {actualizandoId === subusuario.id
                          ? "…"
                          : subusuario.estado === "Activo" ? <IconoDesactivar /> : "↻"}
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <div className="subusuarios-paginacion">
        <span aria-live="polite">
          {cargando && cargaInicialCompletada
            ? "Actualizando resultados..."
            : `${total} ${total === 1 ? "resultado" : "resultados"}`}
        </span>
        <div>
          <button
            type="button"
            onClick={() => cambiarPagina(pagina - 1)}
            disabled={pagina <= 1 || cargando}
          >
            Anterior
          </button>
          <strong>Página {pagina} de {totalPaginas}</strong>
          <button
            type="button"
            onClick={() => cambiarPagina(pagina + 1)}
            disabled={pagina >= totalPaginas || cargando}
          >
            Siguiente
          </button>
        </div>
      </div>

      {modalAbierto && (
        <ModalSubusuario
          permisos={permisos}
          onCerrar={() => setModalAbierto(false)}
          onGuardado={incorporarSubusuario}
        />
      )}

      {subusuarioEdicion && (
        <ModalSubusuario
          permisos={permisos}
          subusuario={subusuarioEdicion}
          onCerrar={() => setSubusuarioEdicion(null)}
          onGuardado={incorporarEdicion}
        />
      )}

      {subusuarioConfirmacion && (
        <ModalConfirmacionEstado
          subusuario={subusuarioConfirmacion}
          activar={subusuarioConfirmacion.estado === "Inactivo"}
          procesando={actualizandoId === subusuarioConfirmacion.id}
          onCancelar={() => setSubusuarioConfirmacion(null)}
          onConfirmar={() => cambiarEstado(subusuarioConfirmacion)}
        />
      )}
    </section>
  );
}

export default TablaSubusuarios;
