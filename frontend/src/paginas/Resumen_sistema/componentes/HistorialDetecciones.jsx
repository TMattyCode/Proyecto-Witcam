import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import "./HistorialDetecciones.css";

import iconoReloj from "../../../assets/iconos/016 icono-reloj.png";
import { obtenerRostroDeteccion, obtenerUltimosIngresos } from "../../../servicios/api";

const FORMATEADOR_FECHA = new Intl.DateTimeFormat("es-CL", {
  day: "2-digit", month: "2-digit", year: "numeric",
  hour: "2-digit", minute: "2-digit",
});

function RostroIngreso({ ingreso }) {
  const [url, setUrl] = useState("");
  useEffect(() => {
    if (!ingreso.tieneRostro) return undefined;
    let activo = true;
    let urlCreada = "";
    obtenerRostroDeteccion(ingreso.idDeteccion).then((imagen) => {
      if (!activo) return;
      urlCreada = URL.createObjectURL(imagen);
      setUrl(urlCreada);
    }).catch(() => { if (activo) setUrl(""); });
    return () => { activo = false; if (urlCreada) URL.revokeObjectURL(urlCreada); };
  }, [ingreso.idDeteccion, ingreso.tieneRostro]);
  return url
    ? <img className="ultimo-ingreso-rostro" src={url} alt={`Rostro de ${ingreso.nombrePersona}`} />
    : <span className="ultimo-ingreso-sin-rostro">Sin rostro</span>;
}

function HistorialDetecciones() {
  const [ingresos, setIngresos] = useState([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState("");
  const navegar = useNavigate();

  useEffect(() => {
    let activo = true;
    const cargar = async () => {
      try {
        const datos = await obtenerUltimosIngresos(5);
        if (activo) { setIngresos(datos.ingresos || []); setError(""); }
      } catch (errorCarga) {
        if (activo) setError(errorCarga.message);
      } finally { if (activo) setCargando(false); }
    };
    cargar();
    const intervalo = setInterval(cargar, 30000);
    return () => { activo = false; clearInterval(intervalo); };
  }, []);

  return (
    <section className="panel-tabla">
      <div className="panel-tabla-header">
        <div className="panel-tabla-titulo"><img src={iconoReloj} alt="" /><h2>Últimos ingresos</h2></div>
        <button type="button" className="panel-ver-todo" onClick={() => navegar("/ingresos")}>Ver todo</button>
      </div>
      <table className="tabla-detecciones">
        <thead><tr><th>Persona</th><th>Cámara</th><th>Fecha y hora</th><th>Rostro</th></tr></thead>
        <tbody>
          {(cargando || error || ingresos.length === 0) && <tr><td colSpan="4" className="tabla-vacia">
            {cargando ? "Cargando ingresos..." : error || "No hay ingresos registrados"}
          </td></tr>}
          {!cargando && !error && ingresos.map((ingreso) => <tr key={ingreso.idDeteccion}>
            <td className="ultimo-ingreso-persona">{ingreso.nombrePersona}</td>
            <td>{ingreso.nombreCamara}</td>
            <td>{FORMATEADOR_FECHA.format(new Date(ingreso.fechaHora))}</td>
            <td><RostroIngreso ingreso={ingreso} /></td>
          </tr>)}
        </tbody>
      </table>
    </section>
  );
}

export default HistorialDetecciones;
