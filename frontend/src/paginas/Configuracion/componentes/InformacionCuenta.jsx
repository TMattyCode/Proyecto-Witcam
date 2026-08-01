import "./InformacionCuenta.css";
function InformacionCuenta() {
  return (
    <section className="configuracion-tarjeta configuracion-cuenta">
      <div className="configuracion-tarjeta-titulo">
        <div className="configuracion-icono configuracion-icono-cuenta">
          ●
        </div>

        <h2>Información de la cuenta</h2>
      </div>

      <div className="cuenta-tabla">
        <div className="cuenta-fila">
          <span>Nombre de la cuenta</span>
          <strong>Administrador</strong>
        </div>

        <div className="cuenta-fila">
          <span>Correo electrónico</span>
          <strong>admin@mail.com</strong>
        </div>

        <div className="cuenta-fila">
          <span>Miembros activos</span>
          <strong>3</strong>
        </div>
      </div>
    </section>
  );
}

export default InformacionCuenta;