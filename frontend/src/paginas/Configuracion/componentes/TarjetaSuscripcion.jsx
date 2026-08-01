import "./TarjetaSuscripcion.css";
function TarjetaSuscripcion() {
  return (
    <section className="configuracion-tarjeta configuracion-suscripcion">
      <div className="configuracion-tarjeta-titulo">
        <div className="configuracion-icono configuracion-icono-suscripcion">
          ▣
        </div>

        <h2>Suscripción</h2>
      </div>

      <div className="suscripcion-informacion">
        <div className="suscripcion-fila">
          <span>Plan actual</span>
          <strong className="suscripcion-plan">Plan Profesional</strong>
        </div>

        <div className="suscripcion-fila">
          <span>Vencimiento</span>
          <strong>05/07/2026</strong>
        </div>

        <div className="suscripcion-fila">
          <span>Días restantes</span>
          <strong className="suscripcion-dias">30 días</strong>
        </div>
      </div>

      <div className="suscripcion-pie">
        <div className="suscripcion-renovacion">
          <span className="suscripcion-estado" />

          <span>
            Renovación automática:{" "}
            <strong className="suscripcion-activada">Activada</strong>
          </span>
        </div>

        <button className="boton-editar-suscripcion" type="button">
          <span>✎</span>
          Editar
        </button>
      </div>
    </section>
  );
}

export default TarjetaSuscripcion;