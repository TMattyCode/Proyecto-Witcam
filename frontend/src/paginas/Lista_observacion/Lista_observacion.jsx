import "./Lista_observacion.css";

import { useEffect, useState } from "react";
import Layout from "../../componentes/layout/Layout";
import {
  obtenerListaObservacion,
  quitarPersonaListaObservacion,
} from "../../servicios/api";
import TablaListaObservacion from "./componentes/TablaListaObservacion";

export default function ListaObservacion() {
  const [registros, setRegistros] = useState([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState("");
  const [personaQuitar, setPersonaQuitar] = useState(null);
  const [personaQuitando, setPersonaQuitando] = useState(null);

  useEffect(() => {
    let activo = true;
    obtenerListaObservacion()
      .then((respuesta) => {
        if (activo) setRegistros(respuesta.registros || []);
      })
      .catch((errorSolicitud) => {
        if (activo) setError(errorSolicitud.message);
      })
      .finally(() => {
        if (activo) setCargando(false);
      });
    return () => { activo = false; };
  }, []);

  const confirmarQuitar = async () => {
    if (!personaQuitar || personaQuitando !== null) return;
    const idPersona = personaQuitar.idCliente;
    setPersonaQuitando(idPersona);
    setError("");
    try {
      await quitarPersonaListaObservacion(idPersona);
      setRegistros((actuales) => actuales.filter(
        (registro) => registro.idCliente !== idPersona,
      ));
      setPersonaQuitar(null);
    } catch (errorSolicitud) {
      setError(errorSolicitud.message);
    } finally {
      setPersonaQuitando(null);
    }
  };

  return (
    <Layout
      titulo="Lista de observación"
      subtitulo="Consulta y gestiona todos los clientes agregados a la lista de observación."
    >
      <section className="lista-observacion">
        <TablaListaObservacion
          registros={registros}
          cargando={cargando}
          error={error}
          onQuitar={setPersonaQuitar}
          personaQuitando={personaQuitando}
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
