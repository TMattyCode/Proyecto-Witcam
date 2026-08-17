import { useState } from "react";

export default function NombrePersonaEditable({
  idPersona,
  nombre,
  onConfirmar,
}) {
  const [editando, setEditando] = useState(false);
  const [valor, setValor] = useState("");
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState("");

  const comenzar = () => {
    setValor(nombre || "");
    setError("");
    setEditando(true);
  };

  const cancelar = () => {
    if (guardando) return;
    setEditando(false);
    setError("");
  };

  const confirmar = async () => {
    const nombreNuevo = valor.trim();
    if (!nombreNuevo) {
      setError("El nombre no puede estar vacío.");
      return;
    }
    if (nombreNuevo === nombre) {
      cancelar();
      return;
    }
    setGuardando(true);
    setError("");
    try {
      await onConfirmar?.(idPersona, nombreNuevo);
      setEditando(false);
    } catch (errorSolicitud) {
      setError(errorSolicitud.message);
    } finally {
      setGuardando(false);
    }
  };

  if (!editando) {
    return (
      <button
        type="button"
        className="tabla-ingresos-nombre-boton"
        title={`${nombre || "Persona sin nombre"}. Haz clic para editar`}
        onClick={comenzar}
      >
        {nombre || "Persona sin nombre"}
      </button>
    );
  }

  return (
    <div className="tabla-ingresos-nombre-edicion">
      <input
        type="text"
        value={valor}
        maxLength={150}
        disabled={guardando}
        autoFocus
        aria-label="Nuevo nombre de la persona"
        aria-invalid={Boolean(error)}
        onFocus={(evento) => evento.target.select()}
        onChange={(evento) => setValor(evento.target.value)}
        onBlur={cancelar}
        onKeyDown={(evento) => {
          if (evento.key === "Enter") {
            evento.preventDefault();
            confirmar();
          } else if (evento.key === "Escape") {
            evento.preventDefault();
            cancelar();
          }
        }}
      />
      {error && <small role="alert">{error}</small>}
    </div>
  );
}
