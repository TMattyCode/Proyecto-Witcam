import "./Configuracion.css";

import { useState } from "react";
import Layout from "../../componentes/layout/Layout";
import TarjetaSuscripcion from "./componentes/TarjetaSuscripcion";
import InformacionCuenta from "./componentes/InformacionCuenta";
import TablaSubusuarios from "./componentes/TablaSubcuentas";

function Configuracion() {
  const [versionSubusuarios, setVersionSubusuarios] = useState(0);

  return (
    <Layout
      titulo="Configuración"
      subtitulo="Gestiona subusuarios, permisos y tu suscripción."
    >
      <main className="configuracion-contenido">
        <section className="configuracion-paneles-superiores">
          <TarjetaSuscripcion />
          <InformacionCuenta versionSubusuarios={versionSubusuarios} />
        </section>

        <TablaSubusuarios
          onSubusuariosCambiaron={() =>
            setVersionSubusuarios((version) => version + 1)
          }
        />
      </main>
    </Layout>
  );
}

export default Configuracion;
