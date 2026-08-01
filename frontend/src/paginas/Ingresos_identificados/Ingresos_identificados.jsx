import "./Ingresos_identificados.css";

import Layout from "../../componentes/layout/Layout";
import FiltrosIngresos from "./componentes/FiltrosIngresos";
import TablaIngresos from "./componentes/TablaIngresos";

export default function IngresosIdentificados() {
  const ingresos = [];

  return (
    <Layout
      titulo="Ingresos identificados"
      subtitulo="Consulta y revisa todos los ingresos detectados por el sistema."
    >
      <section className="ingresos-identificados">
        <FiltrosIngresos />

        <TablaIngresos ingresos={ingresos} />
      </section>
    </Layout>
  );
}
