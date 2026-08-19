import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import "./Header.css";
import iconoCalendario from "../../assets/iconos/015 icono-calendario.png";
import iconoReloj from "../../assets/iconos/016 icono-reloj.png";
import logoUsuario from "../../assets/logos/021 logo-usuario-default.png";
import iconoFlecha from "../../assets/iconos/024 icono-flecha-desplegable.png";
import iconoCampana from "../../assets/iconos/032 icono-campana-azul.png";
import { obtenerAlertas } from "../../servicios/api";

const FORMATEADOR_ALERTA = new Intl.DateTimeFormat("es-CL", {
  day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit",
});

function Header({ titulo = "Resumen del sistema", subtitulo = "Bienvenido, Administrador", compacto = false }) {
  const [fechaHora, setFechaHora] = useState(new Date());
  const [alertas, setAlertas] = useState([]);
  const [alertasAbiertas, setAlertasAbiertas] = useState(false);
  const [errorAlertas, setErrorAlertas] = useState("");
  const [menuUsuarioAbierto, setMenuUsuarioAbierto] = useState(false);
  const contenedorAlertas = useRef(null);
  const contenedorUsuario = useRef(null);
  const navegar = useNavigate();

  useEffect(() => {
    const intervalo = setInterval(() => setFechaHora(new Date()), 1000);
    return () => clearInterval(intervalo);
  }, []);
  useEffect(() => {
    let activo = true;
    let cargaExitosa = false;
    const cargar = async () => {
      try {
        const datos = await obtenerAlertas();
        if (activo) {
          cargaExitosa = true;
          setAlertas(datos.alertas || []);
          setErrorAlertas("");
        }
      } catch (error) {
        if (activo && !cargaExitosa) setErrorAlertas(error.message);
      }
    };
    cargar();
    const intervalo = setInterval(cargar, 30000);
    return () => { activo = false; clearInterval(intervalo); };
  }, []);
  useEffect(() => {
    const cerrar = (evento) => {
      if (!contenedorAlertas.current?.contains(evento.target)) setAlertasAbiertas(false);
      if (!contenedorUsuario.current?.contains(evento.target)) setMenuUsuarioAbierto(false);
    };
    const cerrarConEscape = (evento) => {
      if (evento.key === "Escape") {
        setAlertasAbiertas(false);
        setMenuUsuarioAbierto(false);
      }
    };
    document.addEventListener("mousedown", cerrar);
    document.addEventListener("keydown", cerrarConEscape);
    return () => {
      document.removeEventListener("mousedown", cerrar);
      document.removeEventListener("keydown", cerrarConEscape);
    };
  }, []);

  const fecha = fechaHora.toLocaleDateString("es-CL", { day: "2-digit", month: "2-digit", year: "numeric" }).replace(/-/g, "/");
  const hora = fechaHora.toLocaleTimeString("es-CL", { hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false });

  return (
    <header className={`header${compacto ? " header-compacto" : ""}`}>
      <div className="header-title"><h1>{titulo}</h1><p>{subtitulo}</p></div>
      <div className="header-info">
        <div className="header-date"><img src={iconoCalendario} alt="" /><span>{fecha}</span></div>
        <div className="header-separator" />
        <div className="header-time"><img src={iconoReloj} alt="" /><span>{hora}</span></div>
        <div className="header-separator" />
        <div className="header-notifications" ref={contenedorAlertas}>
          <button type="button" className="header-notifications-button" aria-label="Abrir historial de alertas"
            aria-expanded={alertasAbiertas} onClick={() => setAlertasAbiertas((valor) => !valor)}>
            <img src={iconoCampana} alt="" />
            {alertas.length > 0 && <span className="header-notifications-count">{alertas.length > 99 ? "99+" : alertas.length}</span>}
          </button>
          {alertasAbiertas && <section className="header-alerts-panel" aria-label="Historial de alertas">
            <div className="header-alerts-title"><strong>Historial de alertas</strong><span>{alertas.length}</span></div>
            <div className="header-alerts-list">
              {errorAlertas ? <p className="header-alerts-message">{errorAlertas}</p>
                : alertas.length === 0 ? <p className="header-alerts-message">No existen alertas.</p>
                : alertas.map((alerta) => <article className="header-alert-item" key={alerta.idAlerta}>
                  <span className="header-alert-dot" aria-hidden="true" /><div><strong>{alerta.nombrePersona}</strong>
                    <p>Identificado en {alerta.nombreCamara}</p><small>{FORMATEADOR_ALERTA.format(new Date(alerta.fechaHora))}
                      {alerta.similitud != null ? ` · ${Math.round(alerta.similitud * 100)}% coincidencia` : ""}</small></div>
                </article>)}
            </div>
          </section>}
        </div>
        <div className="header-separator" />
        <div className="header-user-menu" ref={contenedorUsuario}>
          <button
            type="button"
            className="header-user"
            aria-label="Abrir menú de usuario"
            aria-haspopup="menu"
            aria-expanded={menuUsuarioAbierto}
            onClick={() => setMenuUsuarioAbierto((abierto) => !abierto)}
          >
            <img className="header-avatar" src={logoUsuario} alt="" />
            <img
              className={`header-arrow${menuUsuarioAbierto ? " abierta" : ""}`}
              src={iconoFlecha}
              alt=""
            />
          </button>
          {menuUsuarioAbierto && (
            <div className="header-user-dropdown" role="menu">
              <button
                type="button"
                role="menuitem"
                onClick={() => {
                  setMenuUsuarioAbierto(false);
                  navegar("/perfil");
                }}
              >
                <img src={logoUsuario} alt="" />
                <span>
                  <strong>Ver perfil</strong>
                  <small>Administra tus datos personales</small>
                </span>
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
export default Header;
