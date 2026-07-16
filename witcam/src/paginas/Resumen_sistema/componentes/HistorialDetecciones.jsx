import "./HistorialDetecciones.css";

import iconoReloj from "../../../assets/iconos/016 icono-reloj.png";

function HistorialDetecciones() {
  const detecciones = [];

  return (
    <section className="panel-tabla">
      <div className="panel-tabla-header">
        <div className="panel-tabla-titulo">
          <img src={iconoReloj} alt="" />
          <h2>Historial de detecciones</h2>
        </div>
        
        <button className="panel-ver-todo">
            Ver todo
        </button>
      </div>

      <table className="tabla-detecciones">
        <thead>
          <tr>
            <th>Hora</th>
            <th>Imagen</th>
            <th>Cámara</th>
            <th>Resultado</th>
          </tr>
        </thead>

        <tbody>
          {detecciones.length === 0 && (
            <tr>
              <td colSpan="4" className="tabla-vacia">
                No hay detecciones registradas
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </section>
  );
}

export default HistorialDetecciones;