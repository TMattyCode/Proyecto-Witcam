import "./Layout.css";

import Sidebar from "./Sidebar";
import Header from "./Header";

export default function Layout({ titulo, subtitulo, compacto = false, children }) {
  return (
    <div className="layout">
      <Sidebar />

      <main className={`layout-main${compacto ? " compacto" : ""}`}>
        <Header titulo={titulo} subtitulo={subtitulo} compacto={compacto} />

        <div className="layout-contenido">{children}</div>
      </main>
    </div>
  );
}
