import { Navigate, Outlet, Route, Routes } from "react-router-dom";
import "./App.css";
import InicioSesion from "./paginas/Inicio_sesion/Inicio_sesion";
import Registro from "./paginas/Registro/Registro";
import ResumenSistema from "./paginas/Resumen_sistema/Resumen_sistema";
import InterfazCamaras from "./paginas/Interfaz_camaras/Interfaz_camaras";
import IngresosIdentificados from "./paginas/Ingresos_identificados/Ingresos_identificados";
import ListaObservacion from "./paginas/Lista_observacion/Lista_observacion";
import Configuracion from "./paginas/Configuracion/Configuracion";
import Perfil from "./paginas/Perfil/Perfil";
import { useAutenticacion } from "./contextos/AutenticacionContext";
import { PERMISOS } from "./utilidades/permisos";

function PantallaCarga() {
  return (
    <main className="pantalla-carga" aria-live="polite">
      <div className="pantalla-carga-indicador" />
      <p>Abriendo Witcam...</p>
    </main>
  );
}

function RutaProtegida() {
  const { usuario, cargando } = useAutenticacion();
  if (cargando) {
    return <PantallaCarga />;
  }
  return usuario ? <Outlet /> : <Navigate to="/inicio-sesion" replace />;
}

function RutaConPermiso({ permiso, soloAdministrador = false, children }) {
  const { usuario } = useAutenticacion();
  const autorizado = usuario?.rol === "Administrador" || (
    !soloAdministrador && usuario?.permisos?.includes(permiso)
  );
  if (autorizado) return children;
  return <Navigate to="/resumen" replace />;
}

function RutaPublica({ children }) {
  const { usuario, cargando } = useAutenticacion();
  if (cargando) {
    return <PantallaCarga />;
  }
  return usuario ? <Navigate to="/resumen" replace /> : children;
}

function App() {
  return (
    <Routes>
      <Route
        path="/inicio-sesion"
        element={
          <RutaPublica>
            <InicioSesion />
          </RutaPublica>
        }
      />
      <Route
        path="/registro"
        element={
          <RutaPublica>
            <Registro />
          </RutaPublica>
        }
      />

      <Route element={<RutaProtegida />}>
        <Route path="/resumen" element={<ResumenSistema />} />
        <Route path="/perfil" element={<Perfil />} />
        <Route path="/camaras" element={<RutaConPermiso permiso={PERMISOS.GESTIONAR_CAMARAS}><InterfazCamaras /></RutaConPermiso>} />
        <Route path="/ingresos" element={<RutaConPermiso permiso={PERMISOS.GESTIONAR_IDENTIDADES}><IngresosIdentificados /></RutaConPermiso>} />
        <Route path="/observacion" element={<RutaConPermiso permiso={PERMISOS.GESTIONAR_IDENTIDADES}><ListaObservacion /></RutaConPermiso>} />
        <Route path="/configuracion" element={<RutaConPermiso soloAdministrador><Configuracion /></RutaConPermiso>} />
      </Route>

      <Route path="/" element={<Navigate to="/inicio-sesion" replace />} />
      <Route path="*" element={<Navigate to="/inicio-sesion" replace />} />
    </Routes>
  );
}

export default App;
