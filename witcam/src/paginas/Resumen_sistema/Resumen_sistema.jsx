import "./Resumen_sistema.css";

import Layout from "../../componentes/layout/Layout";
import TarjetasResumen from "./componentes/TarjetasResumen";
import HistorialDetecciones from "./componentes/HistorialDetecciones";
import UltimasAlertas from "./componentes/UltimasAlertas";
import EstadoSistema from "./componentes/EstadoSistema";

export default function ResumenSistema() {
  return (
    <Layout
      titulo="Resumen del sistema"
      subtitulo="Bienvenido, Administrador"
      paginaActiva="resumen"
    >
      <div className="resumen-contenido">
        <TarjetasResumen />

        <div className="resumen-tablas">
          <HistorialDetecciones />
          <UltimasAlertas />
        </div>

        <EstadoSistema />
      </div>
    </Layout>
  );
}