import "./TablaListaObservacion.css";

const FORMATEADOR_FECHA = new Intl.DateTimeFormat("es-CL", {
  day: "2-digit", month: "2-digit", year: "numeric",
  hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false,
});

export default function TablaListaObservacion({
  registros = [], cargando = false, error = "",
}) {
  const totalRegistros = registros.length;

  return (
    <section className="tabla-observacion-panel">

      <div className="tabla-observacion-header">

        <div className="tabla-observacion-titulo">

          <div className="tabla-observacion-icono">
            ◎
          </div>

          <div>
            <h2>Clientes en lista de observación</h2>
          </div>

        </div>

        <span className="tabla-observacion-contador">
          {totalRegistros} registros
        </span>

      </div>

      <div className="tabla-observacion-contenedor">

        {error && <p className="tabla-sin-registros" role="alert">{error}</p>}

        <table className="tabla-observacion">

          <thead>

            <tr>
              <th>ID. lista</th>
              <th>ID. cliente</th>
              <th>Motivo</th>
              <th>Fecha del incidente</th>
              <th>Registrado por</th>
              <th>Rostro</th>
              <th>Acción</th>
            </tr>

          </thead>

          <tbody>

            {cargando ? (

              <tr><td colSpan="7" className="tabla-sin-registros">Cargando lista de observaciÃ³n...</td></tr>

            ) : totalRegistros === 0 ? (

              <tr>

                <td colSpan="7" className="tabla-sin-registros">
                  No existen clientes en la lista de observación.
                </td>

              </tr>

            ) : (

              registros.map((registro) => (

                <tr key={registro.idLista}>

                  <td>{registro.idLista}</td>

                  <td>
                    <strong>{registro.nombrePersona}</strong>
                    <br />ID {registro.idCliente}
                  </td>

                  <td>{registro.motivo}</td>

                  <td>
                    {FORMATEADOR_FECHA.format(new Date(registro.fechaIngreso))}
                  </td>

                  <td>{registro.registradoPor}</td>

                  <td>

                    {registro.imagen ? (

                      <img
                        className="tabla-observacion-rostro"
                        src={registro.imagen}
                        alt=""
                      />

                    ) : (

                      <span>Sin imagen</span>

                    )}

                  </td>

                  <td>

                    <button
                      className="tabla-observacion-eliminar"
                      type="button"
                    >
                      ×
                    </button>

                  </td>

                </tr>

              ))

            )}

          </tbody>

        </table>

      </div>

      <div className="tabla-observacion-paginacion">

        <p>

          {totalRegistros === 0
            ? "No hay registros para mostrar"
            : `Mostrando ${totalRegistros} registros`}

        </p>

        <div className="paginacion-botones">

          <button disabled>

            ‹

          </button>

          <button className="pagina-activa">

            1

          </button>

          <button disabled>

            ›

          </button>

        </div>

      </div>

    </section>
  );
}
