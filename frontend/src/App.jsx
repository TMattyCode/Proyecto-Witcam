import { Navigate, Outlet, Route, Routes } from "react-router-dom";
import "./App.css";
import InicioSesion from "./paginas/Inicio_sesion/Inicio_sesion";
import Registro from "./paginas/Registro/Registro";
import ResumenSistema from "./paginas/Resumen_sistema/Resumen_sistema";
import InterfazCamaras from "./paginas/Interfaz_camaras/Interfaz_camaras";
import IngresosIdentificados from "./paginas/Ingresos_identificados/Ingresos_identificados";
import ListaObservacion from "./paginas/Lista_observacion/Lista_observacion";
import Configuracion from "./paginas/Configuracion/Configuracion";
import { useAutenticacion } from "./contextos/AutenticacionContext";
import { PERMISOS, tienePermiso } from "./utilidades/permisos";

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

function RutaPublica({ children }) {
  const { usuario, cargando } = useAutenticacion();
  if (cargando) {
    return <PantallaCarga />;
  }
  return usuario ? <Navigate to="/resumen" replace /> : children;
}

function RutaAutorizada({ permiso, soloAdministrador = false, children }) {
  const { usuario } = useAutenticacion();
  const autorizado = soloAdministrador
    ? usuario?.rol === "Administrador"
    : tienePermiso(usuario, permiso);
  return autorizado ? children : <Navigate to="/resumen" replace />;
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
        <Route path="/camaras" element={<RutaAutorizada permiso={PERMISOS.VER}><InterfazCamaras /></RutaAutorizada>} />
        <Route path="/ingresos" element={<RutaAutorizada permiso={PERMISOS.VER}><IngresosIdentificados /></RutaAutorizada>} />
        <Route path="/observacion" element={<RutaAutorizada permiso={PERMISOS.VER}><ListaObservacion /></RutaAutorizada>} />
        <Route path="/configuracion" element={<RutaAutorizada soloAdministrador><Configuracion /></RutaAutorizada>} />
      </Route>

      <Route path="/" element={<Navigate to="/inicio-sesion" replace />} />
      <Route path="*" element={<Navigate to="/inicio-sesion" replace />} />
    </Routes>
  );
}

export default App;
