import "./InformacionCuenta.css";
import { useEffect, useState } from "react";
import { useAutenticacion } from "../../../contextos/AutenticacionContext";
import { obtenerResumenCuenta } from "../../../servicios/api";

function InformacionCuenta({ versionSubusuarios = 0 }) {
  const { usuario } = useAutenticacion();
  const [resumen, setResumen] = useState({
    nombreCuenta: usuario?.nombreCuenta || "Cargando...",
    subusuariosActivos: 0,
  });
  const [error, setError] = useState("");

  useEffect(() => {
    let activo = true;

    obtenerResumenCuenta()
      .then((datos) => {
        if (activo) {
          setResumen(datos);
          setError("");
        }
      })
      .catch((errorSolicitud) => {
        if (activo) setError(errorSolicitud.message);
      });

    return () => {
      activo = false;
    };
  }, [versionSubusuarios]);

  return (
    <section className="configuracion-tarjeta configuracion-cuenta">
      <div className="configuracion-tarjeta-titulo">
        <div className="configuracion-icono configuracion-icono-cuenta">
          ●
        </div>

        <h2>Información de la cuenta</h2>
      </div>

      <div className="cuenta-tabla">
        <div className="cuenta-fila">
          <span>Negocio o empresa</span>
          <strong>{resumen.nombreCuenta}</strong>
        </div>

        <div className="cuenta-fila">
          <span>Subusuarios activos</span>
          <strong>{resumen.subusuariosActivos}</strong>
        </div>
      </div>

      {error && (
        <p className="cuenta-error" role="alert">
          No se pudo actualizar el resumen: {error}
        </p>
      )}
    </section>
  );
}

export default InformacionCuenta;
