import "./TablaListaObservacion.css";
import "../../Ingresos_identificados/componentes/TablaIngresos.css";

import iconoHistorial from "../../../assets/iconos/031 icono-historial.png";
import HistorialIngresos from "../../Ingresos_identificados/componentes/HistorialIngresos";
import NombrePersonaEditable from "../../Ingresos_identificados/componentes/NombrePersonaEditable";
import RostroPersona from "../../Ingresos_identificados/componentes/RostroPersona";

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

function idPersonaDe(registro) {
  return registro.idPersona ?? registro.idCliente;
}

export default function TablaListaObservacion({
  registros = [],
  total = 0,
  pagina = 1,
  limite = 25,
  cargando = false,
  error = "",
  onQuitar,
  onCambiarPagina,
  onRenombrar,
  onVerHistorial,
  personaQuitando = null,
  historial = null,
  cargandoHistorial = false,
  errorHistorial = "",
  onCerrarHistorial,
}) {
  const totalRegistros = registros.length;
  const totalPaginas = Math.max(1, Math.ceil(total / limite));
  const inicio = total === 0 ? 0 : (pagina - 1) * limite + 1;
  const fin = Math.min(pagina * limite, total);

  return (
    <section className="tabla-observacion-panel">
      <div className="tabla-observacion-header">
        <div className="tabla-observacion-titulo">
          <div className="tabla-observacion-icono">◎</div>
          <div>
            <h2>Personas en lista de observación</h2>
            <p>Consulta las personas que requieren seguimiento.</p>
          </div>
        </div>

        <span className="tabla-observacion-contador">
          {total}{" "}
          {total === 1 ? "registro encontrado" : "registros encontrados"}
        </span>
      </div>

      {error && (
        <div className="tabla-observacion-error" role="alert">
          {error}
        </div>
      )}

      <div className="tabla-observacion-contenedor">
        <table className="tabla-observacion" aria-busy={cargando}>
          <thead>
            <tr>
              <th>Persona</th>
              <th>Motivo</th>
              <th>Fecha de ingreso</th>
              <th>Registrado por</th>
              <th>Rostro</th>
              <th>Acciones</th>
            </tr>
          </thead>

          <tbody>
            {cargando ? (
              <tr>
                <td colSpan="6" className="tabla-sin-registros">
                  Cargando lista de observación...
                </td>
              </tr>
            ) : totalRegistros === 0 ? (
              <tr>
                <td colSpan="6" className="tabla-sin-registros">
                  No existen personas en la lista de observación.
                </td>
              </tr>
            ) : (
              registros.map((registro) => {
                const idPersona = idPersonaDe(registro);
                return (
                  <tr key={registro.idLista}>
                    <td className="tabla-observacion-persona">
                      <NombrePersonaEditable
                        idPersona={idPersona}
                        nombre={registro.nombrePersona}
                        onConfirmar={onRenombrar}
                      />
                    </td>
                    <td>
                      <span className="tabla-observacion-motivo">
                        {registro.motivo || "Sin motivo especificado"}
                      </span>
                    </td>
                    <td className="tabla-observacion-fecha">
                      {formatearFecha(registro.fechaIngreso)}
                    </td>
                    <td>{registro.registradoPor || "No disponible"}</td>
                    <td>
                      <RostroPersona
                        idPersona={idPersona}
                        nombre={registro.nombrePersona}
                      />
                    </td>
                    <td>
                      <div className="tabla-observacion-acciones">
                        <button
                          className="tabla-ingresos-accion historial"
                          type="button"
                          onClick={() => onVerHistorial?.(registro)}
                          aria-label={`Ver historial de ${registro.nombrePersona}`}
                          title="Ver historial de ingresos"
                        >
                          <img src={iconoHistorial} alt="" aria-hidden="true" />
                        </button>
                        <button
                          className="tabla-observacion-quitar"
                          type="button"
                          onClick={() => onQuitar?.(registro)}
                          disabled={personaQuitando === idPersona}
                          aria-label={`Quitar a ${registro.nombrePersona} de la lista de observación`}
                          title="Quitar de la lista de observación"
                        >
                          ↩
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      <div className="tabla-observacion-pie">
        <p>
          {total === 0
            ? "No hay registros para mostrar"
            : `Mostrando ${inicio}-${fin} de ${total}`}
        </p>
        <div className="tabla-observacion-paginacion">
          <button
            type="button"
            disabled={pagina <= 1 || cargando}
            onClick={() => onCambiarPagina?.(pagina - 1)}
            aria-label="Página anterior"
          >
            ‹
          </button>
          <span aria-current="page">
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

      {historial && (
        <HistorialIngresos
          historial={historial}
          cargando={cargandoHistorial}
          error={errorHistorial}
          onCerrar={onCerrarHistorial}
        />
      )}
    </section>
  );
}
