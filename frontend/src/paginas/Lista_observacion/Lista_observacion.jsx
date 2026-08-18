import "./Lista_observacion.css";

import { useEffect, useState } from "react";
import Layout from "../../componentes/layout/Layout";
import {
  obtenerHistorialIngresos,
  obtenerListaObservacion,
  quitarPersonaListaObservacion,
  renombrarPersona,
} from "../../servicios/api";
import TablaListaObservacion from "./componentes/TablaListaObservacion";
import { useAutenticacion } from "../../contextos/AutenticacionContext";
import { PERMISOS, tienePermiso } from "../../utilidades/permisos";

const LIMITE_PAGINA = 25;

export default function ListaObservacion() {
  const { usuario } = useAutenticacion();
  const puedeEditar = tienePermiso(usuario, PERMISOS.EDITAR);
  const [registros, setRegistros] = useState([]);
  const [pagina, setPagina] = useState(1);
  const [total, setTotal] = useState(0);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState("");
  const [personaQuitar, setPersonaQuitar] = useState(null);
  const [personaQuitando, setPersonaQuitando] = useState(null);
  const [historial, setHistorial] = useState(null);
  const [cargandoHistorial, setCargandoHistorial] = useState(false);
  const [errorHistorial, setErrorHistorial] = useState("");

  useEffect(() => {
    let activo = true;
    obtenerListaObservacion(pagina, LIMITE_PAGINA)
      .then((respuesta) => {
        if (!activo) return;
        setRegistros(respuesta.registros || []);
        setTotal(respuesta.total || 0);
        setError("");
      })
      .catch((errorSolicitud) => {
        if (activo) setError(errorSolicitud.message);
      })
      .finally(() => {
        if (activo) setCargando(false);
      });
    return () => { activo = false; };
  }, [pagina]);

  const cambiarPagina = (nuevaPagina) => {
    setCargando(true);
    setError("");
    setPagina(nuevaPagina);
  };

  const confirmarQuitar = async () => {
    if (!personaQuitar || personaQuitando !== null) return;
    const idPersona = personaQuitar.idPersona ?? personaQuitar.idCliente;
    setPersonaQuitando(idPersona);
    setError("");
    try {
      await quitarPersonaListaObservacion(idPersona);
      setTotal((actual) => Math.max(0, actual - 1));
      if (registros.length === 1 && pagina > 1) {
        setCargando(true);
        setPagina((actual) => actual - 1);
      } else {
        setRegistros((actuales) => actuales.filter(
          (registro) => (
            registro.idPersona ?? registro.idCliente
          ) !== idPersona,
        ));
      }
      if (historial?.persona?.id === idPersona) setHistorial(null);
      setPersonaQuitar(null);
    } catch (errorSolicitud) {
      setError(errorSolicitud.message);
    } finally {
      setPersonaQuitando(null);
    }
  };

  const confirmarRenombrado = async (idPersona, nombre) => {
    const respuesta = await renombrarPersona(idPersona, nombre);
    const nombrePersona = respuesta.nombrePersona;
    setRegistros((actuales) => actuales.map((registro) => (
      (registro.idPersona ?? registro.idCliente) === idPersona
        ? { ...registro, nombrePersona }
        : registro
    )));
    setHistorial((actual) => (
      actual?.persona?.id === idPersona
        ? {
            ...actual,
            persona: { ...actual.persona, nombre: nombrePersona },
          }
        : actual
    ));
    setPersonaQuitar((actual) => (
      (actual?.idPersona ?? actual?.idCliente) === idPersona
        ? { ...actual, nombrePersona }
        : actual
    ));
    return nombrePersona;
  };

  const abrirHistorial = async (registro) => {
    const idPersona = registro.idPersona ?? registro.idCliente;
    setHistorial({
      persona: { id: idPersona, nombre: registro.nombrePersona },
      detecciones: [],
    });
    setCargandoHistorial(true);
    setErrorHistorial("");
    try {
      setHistorial(await obtenerHistorialIngresos(idPersona));
    } catch (errorSolicitud) {
      setErrorHistorial(errorSolicitud.message);
    } finally {
      setCargandoHistorial(false);
    }
  };

  return (
    <Layout
      titulo="Lista de observación"
      subtitulo="Consulta y gestiona las personas agregadas a la lista de observación."
    >
      <section className="lista-observacion">
        <TablaListaObservacion
          registros={registros}
          total={total}
          pagina={pagina}
          limite={LIMITE_PAGINA}
          cargando={cargando}
          error={error}
          onQuitar={setPersonaQuitar}
          onCambiarPagina={cambiarPagina}
          onRenombrar={confirmarRenombrado}
          onVerHistorial={abrirHistorial}
          personaQuitando={personaQuitando}
          historial={historial}
          cargandoHistorial={cargandoHistorial}
          errorHistorial={errorHistorial}
          onCerrarHistorial={() => setHistorial(null)}
          puedeEditar={puedeEditar}
        />

        {personaQuitar && (
          <div
            className="modal-quitar-observacion-fondo"
            role="presentation"
            onMouseDown={(evento) => {
              if (
                evento.target === evento.currentTarget
                && personaQuitando === null
              ) {
                setPersonaQuitar(null);
              }
            }}
          >
            <section
              className="modal-quitar-observacion"
              role="alertdialog"
              aria-modal="true"
              aria-labelledby="titulo-quitar-observacion"
              aria-describedby="detalle-quitar-observacion"
            >
              <div className="modal-quitar-observacion-icono">↩</div>
              <p className="modal-quitar-observacion-etiqueta">
                Cambiar estado
              </p>
              <h2 id="titulo-quitar-observacion">
                ¿Quitar a {personaQuitar.nombrePersona} de observación?
              </h2>
              <p id="detalle-quitar-observacion">
                La persona volverá a ingresos identificados. Su identidad,
                muestras y detecciones se conservarán.
              </p>
              <div className="modal-quitar-observacion-acciones">
                <button
                  type="button"
                  onClick={() => setPersonaQuitar(null)}
                  disabled={personaQuitando !== null}
                  autoFocus
                >
                  No, cancelar
                </button>
                <button
                  type="button"
                  className="confirmar"
                  onClick={confirmarQuitar}
                  disabled={personaQuitando !== null}
                >
                  {personaQuitando !== null ? "Quitando..." : "Sí, quitar"}
                </button>
              </div>
            </section>
          </div>
        )}
      </section>
    </Layout>
  );
}
