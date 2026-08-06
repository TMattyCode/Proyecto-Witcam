import { useMemo, useState } from "react";
import "./FiltroSeleccionMultiple.css";

export default function FiltroSeleccionMultiple({
  titulo,
  placeholder,
  opciones,
  seleccion,
  onAplicar,
  onCerrar,
}) {
  const [busqueda, setBusqueda] = useState("");
  const [borrador, setBorrador] = useState(() =>
    seleccion === null
      ? opciones.map((opcion) => opcion.id)
      : seleccion.filter((id) => opciones.some((opcion) => opcion.id === id)),
  );
  const opcionesVisibles = useMemo(() => {
    const texto = busqueda.trim().toLocaleLowerCase();
    return texto
      ? opciones.filter((opcion) => opcion.nombre.toLocaleLowerCase().includes(texto))
      : opciones;
  }, [busqueda, opciones]);
  const visiblesSeleccionadas = opcionesVisibles.length > 0 && opcionesVisibles.every(
    (opcion) => borrador.includes(opcion.id),
  );

  const alternarTodos = () => {
    const idsVisibles = opcionesVisibles.map((opcion) => opcion.id);
    setBorrador((actual) => visiblesSeleccionadas
      ? actual.filter((id) => !idsVisibles.includes(id))
      : [...new Set([...actual, ...idsVisibles])]);
  };

  const alternarOpcion = (id) => {
    setBorrador((actual) => actual.includes(id)
      ? actual.filter((actualId) => actualId !== id)
      : [...actual, id]);
  };

  const aplicar = () => {
    onAplicar(borrador.length === opciones.length ? null : borrador);
    onCerrar();
  };

  return (
    <section className="filtro-multiple" aria-label={titulo}>
      <div className="filtro-multiple-cabecera">
        <strong>{titulo}</strong>
        <button type="button" aria-label="Cerrar filtro" onClick={onCerrar}>×</button>
      </div>

      <input
        className="filtro-multiple-buscador"
        type="search"
        value={busqueda}
        placeholder={placeholder}
        autoFocus
        onChange={(evento) => setBusqueda(evento.target.value)}
      />

      <div className="filtro-multiple-opciones">
        <label>
          <input
            type="checkbox"
            checked={visiblesSeleccionadas}
            disabled={!opcionesVisibles.length}
            onChange={alternarTodos}
          />
          <strong>Seleccionar todo</strong>
        </label>

        {opcionesVisibles.map((opcion) => (
          <label key={opcion.id}>
            <input
              type="checkbox"
              checked={borrador.includes(opcion.id)}
              onChange={() => alternarOpcion(opcion.id)}
            />
            <span title={opcion.nombre}>{opcion.nombre}</span>
          </label>
        ))}

        {!opcionesVisibles.length && (
          <p>No se encontraron resultados.</p>
        )}
      </div>

      <div className="filtro-multiple-acciones">
        <button type="button" onClick={onCerrar}>Cancelar</button>
        <button type="button" onClick={aplicar}>Aplicar</button>
      </div>
    </section>
  );
}
