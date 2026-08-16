import "./Ingresos_identificados.css";

import { useEffect, useState } from "react";
import Layout from "../../componentes/layout/Layout";
import {
  agregarPersonaListaObservacion,
  eliminarPersona,
  obtenerCamarasIngresos,
  obtenerHistorialIngresos,
  obtenerIngresos,
} from "../../servicios/api";
import FiltrosIngresos from "./componentes/FiltrosIngresos";
import HistorialIngresos from "./componentes/HistorialIngresos";
import TablaIngresos from "./componentes/TablaIngresos";

const LIMITE_PAGINA = 25;
const INTERVALO_ACTUALIZACION = 7000;

export default function IngresosIdentificados() {
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

  const agregarAObservacion = async (ingreso) => {
    if (ingreso.enListaObservacion) return;
    setPersonaAgregando(ingreso.idPersona);
    setError("");
    try {
      await agregarPersonaListaObservacion(ingreso.idPersona);
      setIngresos((actuales) => actuales.map((actual) => (
        actual.idPersona === ingreso.idPersona
          ? { ...actual, enListaObservacion: true }
          : actual
      )));
    } catch (errorSolicitud) {
      setError(errorSolicitud.message);
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
          onAgregarObservacion={agregarAObservacion}
          onEliminarPersona={setPersonaEliminar}
          personaAgregando={personaAgregando}
          personaEliminando={personaEliminando}
        />

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
