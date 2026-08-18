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

function RutaConPermiso({ permiso, soloAdministrador = false, children }) {
  const { usuario } = useAutenticacion();
  const autorizado = usuario?.rol === "Administrador" || (
    !soloAdministrador && usuario?.permisos?.includes(permiso)
  );
  if (autorizado) return children;
  const destinos = [
    ["ver_resumen", "/resumen"], ["ver_camaras", "/camaras"],
    ["ver_ingresos", "/ingresos"], ["ver_observacion", "/observacion"],
  ];
  const destino = destinos.find(([codigo]) => usuario?.permisos?.includes(codigo))?.[1];
  return <Navigate to={destino || "/inicio-sesion"} replace />;
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
<<<<<<< HEAD
        <Route path="/resumen" element={<ResumenSistema />} />
        <Route path="/camaras" element={<RutaAutorizada permiso={PERMISOS.VER}><InterfazCamaras /></RutaAutorizada>} />
        <Route path="/ingresos" element={<RutaAutorizada permiso={PERMISOS.VER}><IngresosIdentificados /></RutaAutorizada>} />
        <Route path="/observacion" element={<RutaAutorizada permiso={PERMISOS.VER}><ListaObservacion /></RutaAutorizada>} />
        <Route path="/configuracion" element={<RutaAutorizada soloAdministrador><Configuracion /></RutaAutorizada>} />
=======
        <Route path="/resumen" element={<RutaConPermiso permiso="ver_resumen"><ResumenSistema /></RutaConPermiso>} />
        <Route path="/camaras" element={<RutaConPermiso permiso="ver_camaras"><InterfazCamaras /></RutaConPermiso>} />
        <Route path="/ingresos" element={<RutaConPermiso permiso="ver_ingresos"><IngresosIdentificados /></RutaConPermiso>} />
        <Route path="/observacion" element={<RutaConPermiso permiso="ver_observacion"><ListaObservacion /></RutaConPermiso>} />
        <Route path="/configuracion" element={<RutaConPermiso soloAdministrador><Configuracion /></RutaConPermiso>} />
>>>>>>> 10d0c3dcda1141aa5c15e11ed78790cc56564e68
      </Route>

      <Route path="/" element={<Navigate to="/inicio-sesion" replace />} />
      <Route path="*" element={<Navigate to="/inicio-sesion" replace />} />
    </Routes>
  );
}

export default App;
