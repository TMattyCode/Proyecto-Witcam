import { useState } from "react";
import "./App.css";
import InicioSesion from "./paginas/Inicio_sesion/Inicio_sesion";
import Registro from "./paginas/Registro/Registro";
import ResumenSistema from "./paginas/Resumen_sistema/Resumen_sistema";
import InterfazCamaras from "./paginas/Interfaz_camaras/Interfaz_camaras";
import IngresosIdentificados from "./paginas/Ingresos_identificados/Ingresos_identificados";
import ListaObservacion from "./paginas/Lista_observacion/Lista_observacion";
import Configuracion from "./paginas/Configuracion/Configuracion";
import { NavegacionContext } from "./contextos/NavegacionContext";

const paginas = {
  registro: Registro,
  inicioSesion: InicioSesion,
  resumen: ResumenSistema,
  camaras: InterfazCamaras,
  ingresos: IngresosIdentificados,
  observacion: ListaObservacion,
  configuracion: Configuracion,
};

function App() {
  const [paginaActual, setPaginaActual] = useState("inicioSesion");
  const PaginaActual = paginas[paginaActual];

  return (
    <NavegacionContext.Provider
      value={{
        paginaActual,
        cambiarPagina: setPaginaActual,
      }}
    >
      <PaginaActual />
    </NavegacionContext.Provider>
  );
}

export default App;