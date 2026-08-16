import { useEffect, useState } from "react";
import { obtenerRostroPersona } from "../../../servicios/api";

const INTERVALO_ACTUALIZACION_ROSTRO = 30000;

export default function RostroPersona({ idPersona, nombre }) {
  const [urlRostro, setUrlRostro] = useState("");
  const [ampliado, setAmpliado] = useState(false);

  useEffect(() => {
    let activo = true;
    let urlActual = "";
    let solicitudEnCurso = false;

    const cargar = async () => {
      if (solicitudEnCurso) return;
      solicitudEnCurso = true;
      try {
        const imagen = await obtenerRostroPersona(idPersona);
        if (!activo) return;
        const nuevaUrl = URL.createObjectURL(imagen);
        if (urlActual) URL.revokeObjectURL(urlActual);
        urlActual = nuevaUrl;
        setUrlRostro(nuevaUrl);
      } catch {
        if (activo && !urlActual) setUrlRostro("");
      } finally {
        solicitudEnCurso = false;
      }
    };

    cargar();
    const intervalo = window.setInterval(
      cargar,
      INTERVALO_ACTUALIZACION_ROSTRO,
    );
    return () => {
      activo = false;
      window.clearInterval(intervalo);
      if (urlActual) URL.revokeObjectURL(urlActual);
    };
  }, [idPersona]);

  useEffect(() => {
    if (!ampliado) return undefined;
    const cerrarConEscape = (evento) => {
      if (evento.key === "Escape") setAmpliado(false);
    };
    window.addEventListener("keydown", cerrarConEscape);
    return () => window.removeEventListener("keydown", cerrarConEscape);
  }, [ampliado]);

  return urlRostro ? (
    <>
      <button
        className="tabla-ingresos-rostro-boton"
        type="button"
        onClick={() => setAmpliado(true)}
        aria-label={`Ampliar rostro de ${nombre}`}
        title="Ver rostro ampliado"
      >
        <img
          className="tabla-ingresos-rostro"
          src={urlRostro}
          alt={`Rostro de ${nombre}`}
        />
      </button>

      {ampliado && (
        <div
          className="rostro-ampliado-fondo"
          role="presentation"
          onMouseDown={(evento) => {
            if (evento.target === evento.currentTarget) setAmpliado(false);
          }}
        >
          <section
            className="rostro-ampliado-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby={`titulo-rostro-${idPersona}`}
          >
            <header>
              <h2 id={`titulo-rostro-${idPersona}`}>{nombre}</h2>
              <button
                type="button"
                onClick={() => setAmpliado(false)}
                aria-label="Cerrar imagen ampliada"
              >
                ×
              </button>
            </header>
            <img src={urlRostro} alt={`Rostro ampliado de ${nombre}`} />
          </section>
        </div>
      )}
    </>
  ) : (
    <span className="tabla-sin-imagen">Sin imagen</span>
  );
}
