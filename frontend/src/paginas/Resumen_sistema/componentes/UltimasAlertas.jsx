import { useEffect, useState } from "react";
import "./UltimasAlertas.css";

import iconoCampana from "../../../assets/iconos/020 icono-campana.png";
import { obtenerAlertas, obtenerRostroDeteccion } from "../../../servicios/api";

const FORMATEADOR_FECHA = new Intl.DateTimeFormat("es-CL", {
  day: "2-digit", month: "2-digit", year: "numeric",
  hour: "2-digit", minute: "2-digit",
});

function RostroAlerta({ alerta }) {
  const [url, setUrl] = useState("");
  useEffect(() => {
    if (!alerta.tieneRostro) return undefined;
    let activo = true;
    let urlCreada = "";
    obtenerRostroDeteccion(alerta.idDeteccion).then((imagen) => {
      if (!activo) return;
      urlCreada = URL.createObjectURL(imagen);
      setUrl(urlCreada);
    }).catch(() => { if (activo) setUrl(""); });
    return () => { activo = false; if (urlCreada) URL.revokeObjectURL(urlCreada); };
  }, [alerta.idDeteccion, alerta.tieneRostro]);
  return url
    ? <img className="ultima-alerta-rostro" src={url} alt={`Rostro de ${alerta.nombrePersona}`} />
    : <span className="ultima-alerta-sin-rostro">Sin rostro</span>;
}

export default function UltimasAlertas() {
  const [alertas, setAlertas] = useState([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let activo = true;
    const cargar = async () => {
      try {
        const datos = await obtenerAlertas(5);
        if (activo) { setAlertas(datos.alertas || []); setError(""); }
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
        <div className="panel-tabla-titulo"><img src={iconoCampana} alt="" /><h2>Últimas alertas</h2></div>
      </div>
      <table className="tabla-alertas">
        <thead><tr><th>Persona</th><th>Motivo</th><th>Fecha de ingreso</th><th>Rostro</th></tr></thead>
        <tbody>
          {(cargando || error || alertas.length === 0) && <tr><td colSpan="4" className="tabla-vacia">
            {cargando ? "Cargando alertas..." : error || "No existen alertas"}
          </td></tr>}
          {!cargando && !error && alertas.map((alerta) => <tr key={alerta.idAlerta}>
            <td className="ultima-alerta-persona">{alerta.nombrePersona}</td>
            <td className="ultima-alerta-motivo">{alerta.motivo || "Sin motivo"}</td>
            <td>{FORMATEADOR_FECHA.format(new Date(alerta.fechaHora))}</td>
            <td><RostroAlerta alerta={alerta} /></td>
          </tr>)}
        </tbody>
      </table>
    </section>
  );
}
