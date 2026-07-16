import "./Layout.css";

import Sidebar from "./Sidebar";
import Header from "./Header";
import { useNavegacion } from "../../contextos/NavegacionContext";

export default function Layout({
  titulo,
  subtitulo,
  paginaActiva,
  children,
}) {
  const navegacion = useNavegacion();

  return (
    <div className="layout">
      <Sidebar
        paginaActiva={paginaActiva}
        onCambiarPagina={navegacion?.cambiarPagina}
      />

      <main className="layout-main">
        <Header
          titulo={titulo}
          subtitulo={subtitulo}
        />

        <div className="layout-contenido">
          {children}
        </div>
      </main>
    </div>
  );
}