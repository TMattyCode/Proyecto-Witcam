import "./TablaIngresos.css";

export default function TablaIngresos({ ingresos = [] }) {
  const totalRegistros = ingresos.length;

  return (
    <section className="tabla-ingresos-panel">
      <div className="tabla-ingresos-header">
        <div className="tabla-ingresos-titulo">
          <div className="tabla-ingresos-icono">▤</div>

          <div>
            <h2>Registros de ingresos detectados</h2>
            <p>Consulta el detalle de cada persona identificada.</p>
          </div>
        </div>

        <div className="tabla-ingresos-acciones">
          <span className="tabla-ingresos-contador">
            {totalRegistros}{" "}
            {totalRegistros === 1
              ? "registro encontrado"
              : "registros encontrados"}
          </span>

          <button
            className="tabla-ingresos-exportar"
            type="button"
            disabled={totalRegistros === 0}
          >
            Exportar
          </button>
        </div>
      </div>

      <div className="tabla-ingresos-contenedor">
        <table className="tabla-ingresos">
          <thead>
            <tr>
              <th>ID ingreso</th>
              <th>ID cliente</th>
              <th>Fecha</th>
              <th>Hora</th>
              <th>Cámara</th>
              <th>Imagen</th>
              <th>Acción</th>
            </tr>
          </thead>

          <tbody>
            {totalRegistros === 0 ? (
              <tr>
                <td colSpan="7" className="tabla-sin-registros">
                  No existen ingresos registrados.
                </td>
              </tr>
            ) : (
              ingresos.map((ingreso) => (
                <tr key={ingreso.idIngreso}>
                  <td>{ingreso.idIngreso}</td>
                  <td>{ingreso.idCliente}</td>
                  <td>{ingreso.fecha}</td>
                  <td>{ingreso.hora}</td>
                  <td>{ingreso.camara}</td>

                  <td>
                    {ingreso.imagen ? (
                      <img
                        className="tabla-ingresos-rostro"
                        src={ingreso.imagen}
                        alt={`Rostro de ${ingreso.idCliente}`}
                      />
                    ) : (
                      <span className="tabla-sin-imagen">Sin imagen</span>
                    )}
                  </td>

                  <td>
                    <button
                      className={`tabla-ingresos-observacion ${
                        ingreso.enObservacion ? "activo" : ""
                      }`}
                      type="button"
                      aria-label="Marcar en lista de observación"
                      title="Marcar en lista de observación"
                    >
                      ◉
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <div className="tabla-ingresos-paginacion">
        <p>
          {totalRegistros === 0
            ? "No hay registros para mostrar"
            : `Mostrando ${totalRegistros} ${
                totalRegistros === 1 ? "registro" : "registros"
              }`}
        </p>

        <div className="paginacion-botones">
          <button type="button" disabled>
            ‹
          </button>

          <button
            className="pagina-activa"
            type="button"
            disabled={totalRegistros === 0}
          >
            1
          </button>

          <button type="button" disabled>
            ›
          </button>
        </div>
      </div>
    </section>
  );
}