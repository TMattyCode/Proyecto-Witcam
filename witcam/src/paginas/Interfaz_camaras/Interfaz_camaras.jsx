import "./Interfaz_camaras.css";
import Layout from "../../componentes/layout/Layout";

export default function InterfazCamaras() {
  return (
    <Layout
      titulo="Interfaz de cámaras"
      subtitulo="Visualiza en tiempo real las cámaras conectadas a tu sistema."
      paginaActiva="camaras"
    >
      <section className="camaras-panel">
        <div className="camaras-barra-superior">
          <button className="camaras-tab activo">
            <span className="camaras-tab-icono">?</span>
            Vista en vivo
          </button>

          <div className="camaras-controles">
            <button className="control-camaras-boton">
              <span className="control-camaras-icono">?</span>
              <span>Cuadrícula</span>
              <span className="control-flecha">?</span>
            </button>

            <button className="control-camaras-boton">
              <span className="control-camaras-icono">?</span>
              <span>Filtrar cámaras</span>
              <span className="control-flecha">?</span>
            </button>

            <button
              className="control-pantalla-completa"
              aria-label="Pantalla completa"
            >
              ?
            </button>
          </div>
        </div>

        <div className="camaras-area">
          <div className="camaras-vista-vacia">
            <div className="camaras-vista-icono">?</div>

            <h2>No hay cámaras conectadas</h2>

            <p>
              Cuando una cámara se conecte al sistema, aparecerá en esta
              sección.
            </p>
          </div>
        </div>

        <div className="camaras-estado">
          <div className="camaras-estado-icono">?</div>
          <strong>0 cámaras conectadas</strong>
        </div>
      </section>
    </Layout>
  );
}