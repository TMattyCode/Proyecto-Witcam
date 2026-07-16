import "./Lista_observacion.css";

import Layout from "../../componentes/layout/Layout";
import TablaListaObservacion from "./componentes/TablaListaObservacion";

export default function ListaObservacion() {
  const registros = [];

  return (
    <Layout
      titulo="Lista de observación"
      subtitulo="Consulta y gestiona todos los clientes agregados a la lista de observación."
      paginaActiva="observacion"
    >
      <section className="lista-observacion">
        <TablaListaObservacion registros={registros} />
      </section>
    </Layout>
  );
}