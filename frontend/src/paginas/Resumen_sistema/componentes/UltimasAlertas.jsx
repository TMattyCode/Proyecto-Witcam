import "./UltimasAlertas.css";

import iconoCampana from "../../../assets/iconos/020 icono-campana.png";

export default function UltimasAlertas() {
  return (
    <section className="panel-tabla">

      <div className="panel-tabla-header">

        <div className="panel-tabla-titulo">
          <img src={iconoCampana} alt="" />
          <h2>Últimas alertas</h2>
        </div>

        <button className="panel-ver-todo">
          Ver todas
        </button>

      </div>

      <table className="tabla-alertas">

        <thead>

          <tr>
            <th>Img. actual</th>
            <th>Img. referencia</th>
            <th>Hora</th>
            <th>Coincidencia</th>
            <th>Cámara</th>
          </tr>

        </thead>

        <tbody>

          <tr>
            <td colSpan="5" className="tabla-vacia">
              No existen alertas
            </td>
          </tr>

        </tbody>

      </table>

    </section>
  );
}