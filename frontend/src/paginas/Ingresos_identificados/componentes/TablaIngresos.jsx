import "./TablaIngresos.css";
import iconoObservacion from "../../../assets/iconos/013 icono-ojo-blanco.png";
import iconoBasurero from "../../../assets/iconos/028 icono-basurero.png";
import iconoHistorial from "../../../assets/iconos/031 icono-historial.png";

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
  return Number.isNaN(valor.getTime())
    ? "Fecha no disponible"
    : FORMATEADOR_FECHA.format(valor);
}

export default function TablaIngresos({
  ingresos = [],
  total = 0,
  pagina = 1,
  limite = 25,
  cargando = false,
  error = "",
  onCambiarPagina,
  onVerHistorial,
  onAgregarObservacion,
  onEliminarPersona,
  personaAgregando = null,
  personaEliminando = null,
}) {
  const totalPaginas = Math.max(1, Math.ceil(total / limite));
  const inicio = total === 0 ? 0 : (pagina - 1) * limite + 1;
  const fin = Math.min(pagina * limite, total);

  return (
    <section className="tabla-ingresos-panel">
      <div className="tabla-ingresos-header">
        <div className="tabla-ingresos-titulo">
          <div className="tabla-ingresos-icono">▤</div>
          <div>
            <h2>Registros de ingresos identificados</h2>
            <p>Consulta las detecciones registradas en SQL Server.</p>
          </div>
        </div>

        <div className="tabla-ingresos-acciones">
          <span className="tabla-ingresos-contador">
            {total} {total === 1 ? "registro encontrado" : "registros encontrados"}
          </span>
        </div>
      </div>

      {error && (
        <div className="tabla-ingresos-error" role="alert">
          {error}
        </div>
      )}

      <div className="tabla-ingresos-contenedor">
        <table className="tabla-ingresos" aria-busy={cargando}>
          <thead>
            <tr>
              <th>ID detección</th>
              <th>Persona</th>
              <th>Cámara</th>
              <th>Fecha y hora</th>
              <th>Resultado</th>
              <th>Similitud</th>
              <th>Ruta de imagen</th>
              <th>Acciones</th>
            </tr>
          </thead>

          <tbody>
            {cargando ? (
              <tr>
                <td colSpan="8" className="tabla-sin-registros">
                  Cargando ingresos identificados...
                </td>
              </tr>
            ) : ingresos.length === 0 ? (
              <tr>
                <td colSpan="8" className="tabla-sin-registros">
                  No existen ingresos identificados registrados.
                </td>
              </tr>
            ) : (
              ingresos.map((ingreso) => (
                <tr key={ingreso.idDeteccion}>
                  <td>#{ingreso.idDeteccion}</td>
                  <td className="tabla-ingresos-persona">
                    <strong title={ingreso.nombrePersona}>
                      {ingreso.nombrePersona || "Persona sin nombre"}
                    </strong>
                    <small>ID {ingreso.idPersona}</small>
                  </td>
                  <td>
                    <strong>{ingreso.nombreCamara}</strong>
                    <small>ID {ingreso.idCamara}</small>
                  </td>
                  <td className="tabla-ingresos-fecha">
                    {formatearFecha(ingreso.fechaHora)}
                  </td>
                  <td>{ingreso.resultado}</td>
                  <td title={ingreso.similitud ?? undefined}>
                    {ingreso.similitud === null
                      ? "Sin dato"
                      : `${(ingreso.similitud * 100).toFixed(1)}%`}
                  </td>
                  <td>
                    <span
                      className="tabla-ingresos-ruta"
                      title={ingreso.rutaImagen || "Sin imagen"}
                    >
                      {ingreso.rutaImagen || "Sin imagen"}
                    </span>
                  </td>
                  <td>
                    <div className="tabla-ingresos-celda-acciones">
                      <button
                        className="tabla-ingresos-accion historial"
                        type="button"
                        onClick={() => onVerHistorial?.(ingreso)}
                        aria-label={`Ver historial de ${ingreso.nombrePersona}`}
                        title="Ver historial de ingresos"
                      >
                        <img src={iconoHistorial} alt="" aria-hidden="true" />
                      </button>
                      <button
                        className={`tabla-ingresos-accion observar${ingreso.enListaObservacion ? " agregado" : ""}`}
                        type="button"
                        disabled={ingreso.enListaObservacion || personaAgregando === ingreso.idPersona}
                        onClick={() => onAgregarObservacion?.(ingreso)}
                        aria-label={`Añadir ${ingreso.nombrePersona} a la lista de observación`}
                        title="Añadir a lista de observación (próximamente)"
                      >
                        <img src={iconoObservacion} alt="" aria-hidden="true" />
                      </button>
                      <button
                        className="tabla-ingresos-accion eliminar"
                        type="button"
                        disabled={
                          ingreso.enListaObservacion
                          || personaEliminando === ingreso.idPersona
                        }
                        onClick={() => onEliminarPersona?.(ingreso)}
                        aria-label={`Eliminar registro de ${ingreso.nombrePersona}`}
                        title={
                          ingreso.enListaObservacion
                            ? "La persona esta en la lista de observacion"
                            : "Eliminar persona"
                        }
                      >
                        <img src={iconoBasurero} alt="" aria-hidden="true" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <div className="tabla-ingresos-paginacion">
        <p>
          {total === 0
            ? "No hay registros para mostrar"
            : `Mostrando ${inicio}-${fin} de ${total}`}
        </p>

        <div className="paginacion-botones">
          <button
            type="button"
            disabled={pagina <= 1 || cargando}
            onClick={() => onCambiarPagina?.(pagina - 1)}
            aria-label="Página anterior"
          >
            ‹
          </button>
          <span className="paginacion-indicador" aria-current="page">
            {pagina} de {totalPaginas}
          </span>
          <button
            type="button"
            disabled={pagina >= totalPaginas || cargando}
            onClick={() => onCambiarPagina?.(pagina + 1)}
            aria-label="Página siguiente"
          >
            ›
          </button>
        </div>
      </div>
    </section>
  );
}
