import "./EstadoSistema.css";
import { useState } from "react";
import { useNavigate } from "react-router-dom";

import iconoEscudo from "../../../assets/iconos/022 icono-escudo.png";
import iconoCamaraAzul from "../../../assets/iconos/025 icono-camara-azul.png";
import iconoCamaraBlanca from "../../../assets/iconos/011 icono-camara.png";
import { useAutenticacion } from "../../../contextos/AutenticacionContext";
import { PERMISOS, tienePermiso } from "../../../utilidades/permisos";

export default function EstadoSistema() {
    
    const [hover, setHover] = useState(false);
    const navegar = useNavigate();
    const { usuario } = useAutenticacion();
    const puedeVerCamaras = tienePermiso(
      usuario,
      PERMISOS.GESTIONAR_CAMARAS,
    );

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
        type="button"
        className="estado-boton"
        disabled={!puedeVerCamaras}
        onClick={() => navegar("/camaras")}
        onMouseEnter={() => setHover(true)}
        onMouseLeave={() => setHover(false)}
        title={puedeVerCamaras ? "Abrir cámaras en vivo" : "Sin permiso para ver cámaras"}
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
