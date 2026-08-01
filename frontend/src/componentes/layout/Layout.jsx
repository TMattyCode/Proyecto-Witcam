import "./Layout.css";

import Sidebar from "./Sidebar";
import Header from "./Header";

export default function Layout({ titulo, subtitulo, children }) {
  return (
    <div className="layout">
      <Sidebar />

      <main className="layout-main">
        <Header titulo={titulo} subtitulo={subtitulo} />

        <div className="layout-contenido">{children}</div>
      </main>
    </div>
  );
}
