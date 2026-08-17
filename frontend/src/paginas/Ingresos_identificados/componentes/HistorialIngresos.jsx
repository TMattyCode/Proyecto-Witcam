import "./HistorialIngresos.css";
import RostroDeteccion from "./RostroDeteccion";

const FORMATEADOR_FECHA = new Intl.DateTimeFormat("es-CL", {
  day: "2-digit",
  month: "2-digit",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
  second: "2-digit",
  hour12: false,
});

function formatearFecha(fecha) {
  const valor = new Date(fecha);
  return Number.isNaN(valor.getTime()) ? "Fecha no disponible" : FORMATEADOR_FECHA.format(valor);
}

export default function HistorialIngresos({ historial, cargando, error, onCerrar }) {
  const persona = historial.persona || {};
  const detecciones = historial.detecciones || [];

  return (
    <div className="historial-ingresos-fondo" role="presentation" onMouseDown={onCerrar}>
      <section
        className="historial-ingresos-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="titulo-historial-ingresos"
        onMouseDown={(evento) => evento.stopPropagation()}
      >
        <header>
          <div>
            <span>Historial de identificaciones</span>
            <h2 id="titulo-historial-ingresos">{persona.nombre}</h2>
          </div>
          <button type="button" onClick={onCerrar} aria-label="Cerrar historial">×</button>
        </header>

        {error && <p className="historial-ingresos-error" role="alert">{error}</p>}
        <div className="historial-ingresos-tabla-contenedor">
          <table>
            <thead>
              <tr>
                <th>Camara</th>
                <th>Fecha y hora</th>
                <th>Rostro detectado</th>
              </tr>
            </thead>
            <tbody>
              {cargando ? (
                <tr><td colSpan="3">Cargando historial...</td></tr>
              ) : detecciones.length ? detecciones.map((deteccion) => (
                <tr key={deteccion.idDeteccion}>
                  <td>{deteccion.nombreCamara}</td>
                  <td>{formatearFecha(deteccion.fechaHora)}</td>
                  <td>
                    <RostroDeteccion
                      idDeteccion={deteccion.idDeteccion}
                      nombrePersona={persona.nombre}
                      disponible={deteccion.tieneRostro}
                    />
                  </td>
                </tr>
              )) : (
                <tr><td colSpan="3">No hay detecciones para esta persona.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
