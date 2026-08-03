import { useEffect, useState } from "react";
import "./Header.css";

import iconoCalendario from "../../assets/iconos/015 icono-calendario.png";
import iconoReloj from "../../assets/iconos/016 icono-reloj.png";
import logoUsuario from "../../assets/logos/021 logo-usuario-default.png";
import iconoFlecha from "../../assets/iconos/024 icono-flecha-desplegable.png";

function Header({
  titulo = "Resumen del sistema",
  subtitulo = "Bienvenido, Administrador",
  compacto = false,
}) {
  const [fechaHora, setFechaHora] = useState(new Date());

  useEffect(() => {
    const intervalo = setInterval(() => {
      setFechaHora(new Date());
    }, 1000);

    return () => clearInterval(intervalo);
  }, []);

  const fecha = fechaHora.toLocaleDateString("es-CL", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  })
  .replace(/-/g, "/");

  const hora = fechaHora.toLocaleTimeString("es-CL", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });

  return (
    <header className={`header${compacto ? " header-compacto" : ""}`}>
      <div className="header-title">
        <h1>{titulo}</h1>
        <p>{subtitulo}</p>
      </div>
      <div className="header-info">
        <div className="header-date">
          <img src={iconoCalendario} alt="" />
          <span>{fecha}</span>
        </div>

        <div className="header-separator"></div>

        <div className="header-time">
          <img src={iconoReloj} alt="" />
          <span>{hora}</span>
        </div>

        <div className="header-separator"></div>

        <div className="header-user">
          <img className="header-avatar" src={logoUsuario} alt="Usuario" />
          <img className="header-arrow" src={iconoFlecha} alt="" />
        </div>
      </div>
    </header>
  );
}

export default Header;
