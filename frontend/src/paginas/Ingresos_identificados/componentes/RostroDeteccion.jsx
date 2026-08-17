import { useEffect, useState } from "react";
import { obtenerRostroDeteccion } from "../../../servicios/api";

export default function RostroDeteccion({
  idDeteccion,
  nombrePersona,
  disponible,
}) {
  const [urlRostro, setUrlRostro] = useState("");
  const [ampliado, setAmpliado] = useState(false);

  useEffect(() => {
    if (!disponible) {
      return undefined;
    }
    let activo = true;
    let urlActual = "";

    obtenerRostroDeteccion(idDeteccion)
      .then((imagen) => {
        if (!activo) return;
        urlActual = URL.createObjectURL(imagen);
        setUrlRostro(urlActual);
      })
      .catch(() => {
        if (activo) setUrlRostro("");
      });

    return () => {
      activo = false;
      if (urlActual) URL.revokeObjectURL(urlActual);
    };
  }, [disponible, idDeteccion]);

  useEffect(() => {
    if (!ampliado) return undefined;
    const cerrarConEscape = (evento) => {
      if (evento.key === "Escape") setAmpliado(false);
    };
    window.addEventListener("keydown", cerrarConEscape);
    return () => window.removeEventListener("keydown", cerrarConEscape);
  }, [ampliado]);

  if (!disponible || !urlRostro) {
    return <span className="historial-sin-rostro">Sin rostro</span>;
  }

  return (
    <>
      <button
        className="historial-rostro-boton"
        type="button"
        onClick={() => setAmpliado(true)}
        aria-label={`Ampliar rostro detectado de ${nombrePersona}`}
        title="Ver rostro detectado"
      >
        <img src={urlRostro} alt={`Detección de ${nombrePersona}`} />
      </button>

      {ampliado && (
        <div
          className="historial-rostro-ampliado-fondo"
          role="presentation"
          onMouseDown={(evento) => {
            if (evento.target === evento.currentTarget) setAmpliado(false);
          }}
        >
          <section
            className="historial-rostro-ampliado"
            role="dialog"
            aria-modal="true"
            aria-labelledby={`titulo-deteccion-${idDeteccion}`}
          >
            <header>
              <h2 id={`titulo-deteccion-${idDeteccion}`}>
                Rostro detectado de {nombrePersona}
              </h2>
              <button
                type="button"
                onClick={() => setAmpliado(false)}
                aria-label="Cerrar rostro ampliado"
              >
                ×
              </button>
            </header>
            <img src={urlRostro} alt={`Rostro detectado de ${nombrePersona}`} />
          </section>
        </div>
      )}
    </>
  );
}
