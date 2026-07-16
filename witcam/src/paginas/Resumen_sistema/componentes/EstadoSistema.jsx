import "./EstadoSistema.css";
import { useState } from "react";

import iconoEscudo from "../../../assets/iconos/022 icono-escudo.png";
import iconoCamaraAzul from "../../../assets/iconos/025 icono-camara-azul.png";
import iconoCamaraBlanca from "../../../assets/iconos/011 icono-camara.png";

export default function EstadoSistema() {
    
    const [hover, setHover] = useState(false);

  return (
    <div className="estado-sistema">

      <div className="estado-info">

        <div className="estado-icono">
          <img src={iconoEscudo} alt="" />
        </div>

        <div className="estado-texto">
          <h3>Sistema activo y funcionando correctamente</h3>
          <p>WITCAM está monitoreando los accesos en tiempo real.</p>
        </div>

      </div>

      <button
        className="estado-boton"
        onMouseEnter={() => setHover(true)}
        onMouseLeave={() => setHover(false)}
      >
        <img
            src={hover ? iconoCamaraBlanca : iconoCamaraAzul}
            alt=""
        />
        Ir a cámaras en vivo
      </button>

    </div>
  );
}