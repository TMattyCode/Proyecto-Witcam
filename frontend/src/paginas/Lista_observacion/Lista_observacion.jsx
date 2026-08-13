import "./Lista_observacion.css";

import { useEffect, useState } from "react";
import Layout from "../../componentes/layout/Layout";
import { obtenerListaObservacion } from "../../servicios/api";
import TablaListaObservacion from "./componentes/TablaListaObservacion";

export default function ListaObservacion() {
  const [registros, setRegistros] = useState([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState("");

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
        />
      </section>
    </Layout>
  );
}
