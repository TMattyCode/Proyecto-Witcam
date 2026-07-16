import "./Configuracion.css";

import Layout from "../../componentes/layout/Layout";
import TarjetaSuscripcion from "./componentes/TarjetaSuscripcion";
import InformacionCuenta from "./componentes/InformacionCuenta";
import TablaSubcuentas from "./componentes/TablaSubcuentas";

function Configuracion() {
  return (
    <Layout
      titulo="Configuración"
      subtitulo="Gestiona subcuentas, permisos y tu suscripción."
      paginaActiva="configuracion"
    >
      <main className="configuracion-contenido">
        <section className="configuracion-paneles-superiores">
          <TarjetaSuscripcion />
          <InformacionCuenta />
        </section>

        <TablaSubcuentas />
      </main>
    </Layout>
  );
}

export default Configuracion;