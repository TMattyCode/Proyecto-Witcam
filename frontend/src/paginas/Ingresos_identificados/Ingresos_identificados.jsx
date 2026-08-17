import "./Ingresos_identificados.css";

import { useEffect, useState } from "react";
import Layout from "../../componentes/layout/Layout";
import {
  agregarPersonaListaObservacion,
  eliminarPersona,
  obtenerCamarasIngresos,
  obtenerHistorialIngresos,
  obtenerIngresos,
  renombrarPersona,
} from "../../servicios/api";
import FiltrosIngresos from "./componentes/FiltrosIngresos";
import HistorialIngresos from "./componentes/HistorialIngresos";
import TablaIngresos from "./componentes/TablaIngresos";
import { useAutenticacion } from "../../contextos/AutenticacionContext";

const LIMITE_PAGINA = 25;
const INTERVALO_ACTUALIZACION = 7000;

export default function IngresosIdentificados() {
  const { usuario } = useAutenticacion();
  const esAdministrador = usuario?.rol === "Administrador";
  const puedeGestionar = esAdministrador || usuario?.permisos?.includes("gestionar_identidades");
  const puedeEliminar = esAdministrador || usuario?.permisos?.includes("eliminar_identidades");
  const [ingresos, setIngresos] = useState([]);
  const [pagina, setPagina] = useState(1);
  const [total, setTotal] = useState(0);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState("");
  const [camaras, setCamaras] = useState([]);
  const [filtrosAplicados, setFiltrosAplicados] = useState({});
  const [historial, setHistorial] = useState(null);
  const [cargandoHistorial, setCargandoHistorial] = useState(false);
  const [errorHistorial, setErrorHistorial] = useState("");
  const [personaAgregando, setPersonaAgregando] = useState(null);
  const [personaObservacion, setPersonaObservacion] = useState(null);
  const [motivoObservacion, setMotivoObservacion] = useState("");
  const [errorObservacion, setErrorObservacion] = useState("");
  const [personaEliminar, setPersonaEliminar] = useState(null);
  const [personaEliminando, setPersonaEliminando] = useState(null);

  useEffect(() => {
    let activo = true;
    let solicitudEnCurso = false;
    let conexionConfirmada = false;
    let fallosConsecutivos = 0;

    const actualizarIngresos = async (esCargaInicial = false) => {
      if (solicitudEnCurso) return;
      solicitudEnCurso = true;
      try {
        const respuesta = await obtenerIngresos(
          pagina,
          LIMITE_PAGINA,
          filtrosAplicados,
        );
        if (!activo) return;
        conexionConfirmada = true;
        fallosConsecutivos = 0;
        setIngresos(respuesta.ingresos);
        setTotal(respuesta.total);
        setError("");
      } catch (errorSolicitud) {
        if (!activo) return;
        fallosConsecutivos += 1;
        if (esCargaInicial) {
          setIngresos([]);
          setTotal(0);
        }
        if (!conexionConfirmada || fallosConsecutivos >= 2) {
          setError(errorSolicitud.message);
        }
      } finally {
        solicitudEnCurso = false;
        if (activo && esCargaInicial) setCargando(false);
      }
    };

    actualizarIngresos(true);
    const intervalo = window.setInterval(
      () => actualizarIngresos(false),
      INTERVALO_ACTUALIZACION,
    );
    return () => {
      activo = false;
      window.clearInterval(intervalo);
    };
  }, [pagina, filtrosAplicados]);

  useEffect(() => {
    let activo = true;
    obtenerCamarasIngresos()
      .then((respuesta) => {
        if (activo) setCamaras(respuesta.camaras);
      })
      .catch((errorSolicitud) => {
        if (activo) setError(errorSolicitud.message);
      });
    return () => {
      activo = false;
    };
  }, []);

  const cambiarPagina = (nuevaPagina) => {
    setCargando(true);
    setError("");
    setPagina(nuevaPagina);
  };

  const aplicarFiltros = (nuevosFiltros) => {
    setCargando(true);
    setError("");
    setPagina(1);
    setFiltrosAplicados(nuevosFiltros);
  };

  const abrirHistorial = async (ingreso) => {
    setHistorial({ persona: { id: ingreso.idPersona, nombre: ingreso.nombrePersona }, detecciones: [] });
    setCargandoHistorial(true);
    setErrorHistorial("");
    try {
      setHistorial(await obtenerHistorialIngresos(ingreso.idPersona));
    } catch (errorSolicitud) {
      setErrorHistorial(errorSolicitud.message);
    } finally {
      setCargandoHistorial(false);
    }
  };

  const abrirMotivoObservacion = (ingreso) => {
    if (ingreso.enListaObservacion) return;
    setPersonaObservacion(ingreso);
    setMotivoObservacion("");
    setErrorObservacion("");
  };

  const cerrarMotivoObservacion = () => {
    if (personaAgregando !== null) return;
    setPersonaObservacion(null);
    setMotivoObservacion("");
    setErrorObservacion("");
  };

  const agregarAObservacion = async (evento) => {
    evento.preventDefault();
    if (!personaObservacion || personaAgregando !== null) return;
    const ingreso = personaObservacion;
    setPersonaAgregando(ingreso.idPersona);
    setError("");
    setErrorObservacion("");
    try {
      await agregarPersonaListaObservacion(
        ingreso.idPersona,
        motivoObservacion.trim(),
      );
      setIngresos((actuales) => actuales.map((actual) => (
        actual.idPersona === ingreso.idPersona
          ? { ...actual, enListaObservacion: true }
          : actual
      )));
      setPersonaObservacion(null);
      setMotivoObservacion("");
    } catch (errorSolicitud) {
      setError(errorSolicitud.message);
      setErrorObservacion(errorSolicitud.message);
    } finally {
      setPersonaAgregando(null);
    }
  };

  const confirmarEliminacion = async () => {
    if (!personaEliminar || personaEliminando !== null) return;
    const idPersona = personaEliminar.idPersona;
    setPersonaEliminando(idPersona);
    setError("");
    try {
      await eliminarPersona(idPersona);
      setIngresos((actuales) => actuales.filter(
        (ingreso) => ingreso.idPersona !== idPersona,
      ));
      setTotal((actual) => Math.max(0, actual - 1));
      if (historial?.persona?.id === idPersona) setHistorial(null);
      setPersonaEliminar(null);
    } catch (errorSolicitud) {
      setError(errorSolicitud.message);
      setPersonaEliminar(null);
    } finally {
      setPersonaEliminando(null);
    }
  };

  const confirmarRenombrado = async (idPersona, nombre) => {
    const respuesta = await renombrarPersona(idPersona, nombre);
    const nombrePersona = respuesta.nombrePersona;
    setIngresos((actuales) => actuales.map((ingreso) => (
      ingreso.idPersona === idPersona
        ? { ...ingreso, nombrePersona }
        : ingreso
    )));
    setHistorial((actual) => (
      actual?.persona?.id === idPersona
        ? {
            ...actual,
            persona: { ...actual.persona, nombre: nombrePersona },
          }
        : actual
    ));
    setPersonaObservacion((actual) => (
      actual?.idPersona === idPersona
        ? { ...actual, nombrePersona }
        : actual
    ));
    setPersonaEliminar((actual) => (
      actual?.idPersona === idPersona
        ? { ...actual, nombrePersona }
        : actual
    ));
    return nombrePersona;
  };

  return (
    <Layout
      titulo="Ingresos identificados"
      subtitulo="Consulta y revisa todos los ingresos detectados por el sistema."
    >
      <section className="ingresos-identificados">
        <FiltrosIngresos
          camaras={camaras}
          cargando={cargando}
          onAplicar={aplicarFiltros}
        />

        <TablaIngresos
          ingresos={ingresos}
          total={total}
          pagina={pagina}
          limite={LIMITE_PAGINA}
          cargando={cargando}
          error={error}
          onCambiarPagina={cambiarPagina}
          onVerHistorial={abrirHistorial}
          onAgregarObservacion={puedeGestionar ? abrirMotivoObservacion : null}
          onEliminarPersona={puedeEliminar ? setPersonaEliminar : null}
          onRenombrarPersona={puedeGestionar ? confirmarRenombrado : null}
          personaAgregando={personaAgregando}
          personaEliminando={personaEliminando}
        />

        {personaObservacion && (
          <div
            className="modal-motivo-observacion-fondo"
            role="presentation"
            onMouseDown={(evento) => {
              if (evento.target === evento.currentTarget) {
                cerrarMotivoObservacion();
              }
            }}
          >
            <form
              className="modal-motivo-observacion"
              role="dialog"
              aria-modal="true"
              aria-labelledby="titulo-motivo-observacion"
              onSubmit={agregarAObservacion}
            >
              <div className="modal-motivo-observacion-icono">◎</div>
              <p className="modal-motivo-observacion-etiqueta">
                Lista de observación
              </p>
              <h2 id="titulo-motivo-observacion">
                Añadir a {personaObservacion.nombrePersona}
              </h2>
              <label htmlFor="motivo-observacion">
                Motivo <span>(opcional)</span>
              </label>
              <textarea
                id="motivo-observacion"
                value={motivoObservacion}
                onChange={(evento) => setMotivoObservacion(evento.target.value)}
                maxLength={500}
                rows={4}
                placeholder="Describe por qué esta persona requiere observación"
                autoFocus
              />
              <div className="modal-motivo-observacion-contador">
                {motivoObservacion.length}/500
              </div>
              {errorObservacion && (
                <p className="modal-motivo-observacion-error" role="alert">
                  {errorObservacion}
                </p>
              )}
              <div className="modal-motivo-observacion-acciones">
                <button
                  type="button"
                  onClick={cerrarMotivoObservacion}
                  disabled={personaAgregando !== null}
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="confirmar"
                  disabled={personaAgregando !== null}
                >
                  {personaAgregando !== null
                    ? "Añadiendo..."
                    : motivoObservacion.trim()
                      ? "Aceptar"
                      : "Omitir"}
                </button>
              </div>
            </form>
          </div>
        )}

        {personaEliminar && (
          <div
            className="modal-eliminar-persona-fondo"
            role="presentation"
            onMouseDown={(evento) => {
              if (
                evento.target === evento.currentTarget
                && personaEliminando === null
              ) {
                setPersonaEliminar(null);
              }
            }}
          >
            <section
              className="modal-eliminar-persona"
              role="alertdialog"
              aria-modal="true"
              aria-labelledby="titulo-eliminar-persona"
              aria-describedby="detalle-eliminar-persona"
            >
              <div className="modal-eliminar-persona-icono">!</div>
              <p className="modal-eliminar-persona-etiqueta">
                Accion irreversible
              </p>
              <h2 id="titulo-eliminar-persona">
                ¿Eliminar a {personaEliminar.nombrePersona}?
              </h2>
              <p id="detalle-eliminar-persona">
                Se eliminaran su identidad, galeria e imagenes. Sus ingresos
                permaneceran en el historial sin datos personales.
              </p>
              <div className="modal-eliminar-persona-acciones">
                <button
                  type="button"
                  onClick={() => setPersonaEliminar(null)}
                  disabled={personaEliminando !== null}
                  autoFocus
                >
                  No, cancelar
                </button>
                <button
                  type="button"
                  className="confirmar"
                  onClick={confirmarEliminacion}
                  disabled={personaEliminando !== null}
                >
                  {personaEliminando !== null
                    ? "Eliminando..."
                    : "Si, eliminar"}
                </button>
              </div>
            </section>
          </div>
        )}

        {historial && (
          <HistorialIngresos
            historial={historial}
            cargando={cargandoHistorial}
            error={errorHistorial}
            onCerrar={() => setHistorial(null)}
          />
        )}
      </section>
    </Layout>
  );
}
