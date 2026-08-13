import "./HistorialIngresos.css";

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
            <p>ID persona {persona.id}</p>
          </div>
          <button type="button" onClick={onCerrar} aria-label="Cerrar historial">×</button>
        </header>

        {error && <p className="historial-ingresos-error" role="alert">{error}</p>}
        <div className="historial-ingresos-tabla-contenedor">
          <table>
            <thead>
              <tr>
                <th>ID deteccion</th>
                <th>Fecha y hora</th>
                <th>Camara</th>
                <th>Resultado</th>
                <th>Similitud</th>
              </tr>
            </thead>
            <tbody>
              {cargando ? (
                <tr><td colSpan="5">Cargando historial...</td></tr>
              ) : detecciones.length ? detecciones.map((deteccion) => (
                <tr key={deteccion.idDeteccion}>
                  <td>#{deteccion.idDeteccion}</td>
                  <td>{formatearFecha(deteccion.fechaHora)}</td>
                  <td>{deteccion.nombreCamara}</td>
                  <td>{deteccion.resultado}</td>
                  <td>{deteccion.similitud == null ? "Sin dato" : `${(deteccion.similitud * 100).toFixed(1)}%`}</td>
                </tr>
              )) : (
                <tr><td colSpan="5">No hay detecciones para esta persona.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
