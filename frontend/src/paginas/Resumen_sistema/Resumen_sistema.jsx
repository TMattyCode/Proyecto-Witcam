import "./Resumen_sistema.css";

import Layout from "../../componentes/layout/Layout";
import TarjetasResumen from "./componentes/TarjetasResumen";
import HistorialDetecciones from "./componentes/HistorialDetecciones";
import UltimasAlertas from "./componentes/UltimasAlertas";
import EstadoSistema from "./componentes/EstadoSistema";
import { useAutenticacion } from "../../contextos/AutenticacionContext";

export default function ResumenSistema() {
  const { usuario } = useAutenticacion();
  const nombreUsuario = usuario?.nombreUsuario || "usuario";

  return (
    <Layout
      titulo="Resumen del sistema"
      subtitulo={`Bienvenido, ${nombreUsuario}`}
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
