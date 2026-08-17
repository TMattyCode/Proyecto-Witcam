import { NavLink, useNavigate } from "react-router-dom";
import "./Sidebar.css";
import { useAutenticacion } from "../../contextos/AutenticacionContext";

import logoWitcam from "../../assets/logos/004 logo-witcam.png";
import iconoCasa from "../../assets/iconos/010 icono-casa.png";
import iconoCamara from "../../assets/iconos/011 icono-camara.png";
import iconoPersonas from "../../assets/iconos/012 icono-personas.png";
import iconoOjo from "../../assets/iconos/013 icono-ojo-blanco.png";
import iconoConfiguracion from "../../assets/iconos/014 icono-configuracion.png";
import iconoSalir from "../../assets/iconos/023 icono-salir.png";

const itemsSidebar = [
  {
    ruta: "/resumen",
    icono: iconoCasa,
    alt: "Resumen del sistema",
    className: "icono-casa",
    permiso: "ver_resumen",
  },
  { ruta: "/camaras", icono: iconoCamara, alt: "Interfaz de cámaras", permiso: "ver_camaras" },
  {
    ruta: "/ingresos",
    icono: iconoPersonas,
    alt: "Ingresos identificados",
    permiso: "ver_ingresos",
  },
  { ruta: "/observacion", icono: iconoOjo, alt: "Lista de observación", permiso: "ver_observacion" },
  {
    ruta: "/configuracion",
    icono: iconoConfiguracion,
    alt: "Configuración",
    soloAdministrador: true,
  },
];

function Sidebar() {
  const navigate = useNavigate();
  const { usuario, cerrarSesion } = useAutenticacion();
  const itemsVisibles = itemsSidebar.filter((item) => (
    usuario?.rol === "Administrador"
    || (!item.soloAdministrador && usuario?.permisos?.includes(item.permiso))
  ));

  const salir = async () => {
    await cerrarSesion();
    navigate("/inicio-sesion", { replace: true });
  };

  return (
    <aside className="sidebar">
      <div className="sidebar-logo">
        <img src={logoWitcam} alt="Witcam" />
        <h2>WITCAM</h2>
      </div>

      <nav className="sidebar-menu" aria-label="Navegación principal">
        {itemsVisibles.map((item) => (
          <NavLink
            key={item.ruta}
            to={item.ruta}
            className={({ isActive }) =>
              `sidebar-item${isActive ? " active" : ""}`
            }
            aria-label={item.alt}
          >
            <img className={item.className} src={item.icono} alt="" />
          </NavLink>
        ))}
      </nav>

      <button
        className="sidebar-salir"
        type="button"
        onClick={salir}
        aria-label="Cerrar sesión"
      >
        <img src={iconoSalir} alt="" />
      </button>
    </aside>
  );
}

export default Sidebar;
