import "./Sidebar.css";

import logoWitcam from "../../assets/logos/004 logo-witcam.png";

import iconoCasa from "../../assets/iconos/010 icono-casa.png";
import iconoCamara from "../../assets/iconos/011 icono-camara.png";
import iconoPersonas from "../../assets/iconos/012 icono-personas.png";
import iconoOjo from "../../assets/iconos/013 icono-ojo-blanco.png";
import iconoConfiguracion from "../../assets/iconos/014 icono-configuracion.png";
import iconoSalir from "../../assets/iconos/023 icono-salir.png";

const itemsSidebar = [
  {
    pagina: "resumen",
    icono: iconoCasa,
    alt: "Resumen del sistema",
    className: "icono-casa",
  },
  {
    pagina: "camaras",
    icono: iconoCamara,
    alt: "Interfaz de cámaras",
  },
  {
    pagina: "ingresos",
    icono: iconoPersonas,
    alt: "Ingresos identificados",
  },
  {
    pagina: "observacion",
    icono: iconoOjo,
    alt: "Lista de observación",
  },
  {
    pagina: "configuracion",
    icono: iconoConfiguracion,
    alt: "Configuración",
  },
];

function Sidebar({ paginaActiva, onCambiarPagina }) {
  return (
    <aside className="sidebar">
      <div className="sidebar-logo">
        <img src={logoWitcam} alt="Witcam" />
        <h2>WITCAM</h2>
      </div>

      <nav className="sidebar-menu">
        {itemsSidebar.map((item) => (
          <button
            key={item.pagina}
            type="button"
            className={`sidebar-item ${
              paginaActiva === item.pagina ? "active" : ""
            }`}
            onClick={() => onCambiarPagina?.(item.pagina)}
            aria-label={item.alt}
            aria-current={paginaActiva === item.pagina ? "page" : undefined}
          >
            <img
              className={item.className}
              src={item.icono}
              alt=""
            />
          </button>
        ))}
      </nav>

      <button
        className="sidebar-salir"
        type="button"
        onClick={() => onCambiarPagina?.("inicioSesion")}
        aria-label="Cerrar sesión"
      >
        <img src={iconoSalir} alt="" />
      </button>
    </aside>
  );
}

export default Sidebar;