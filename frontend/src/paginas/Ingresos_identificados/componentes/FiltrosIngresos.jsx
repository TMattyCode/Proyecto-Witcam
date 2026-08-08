import { useState } from "react";

import "./FiltrosIngresos.css";

const VALORES_INICIALES = {
  fechaDesde: "",
  horaDesde: "00:00",
  fechaHasta: "",
  horaHasta: "00:00",
  idCamara: "",
};

function prepararFiltros(valores) {
  return {
    fechaDesde: valores.fechaDesde
      ? `${valores.fechaDesde}T${valores.horaDesde || "00:00"}:00`
      : "",
    fechaHasta: valores.fechaHasta
      ? `${valores.fechaHasta}T${valores.horaHasta || "00:00"}:59`
      : "",
    idCamara: valores.idCamara,
  };
}

export default function FiltrosIngresos({
  camaras = [],
  cargando = false,
  onAplicar,
}) {
  const [valores, setValores] = useState(VALORES_INICIALES);

  const actualizar = (evento) => {
    const { name, value } = evento.target;
    setValores((actuales) => ({ ...actuales, [name]: value }));
  };

  const buscar = (evento) => {
    evento.preventDefault();
    onAplicar?.(prepararFiltros(valores));
  };

  const limpiar = () => {
    setValores(VALORES_INICIALES);
    onAplicar?.({});
  };

  return (
    <section className="filtros-ingresos">
      <h2>Filtrar por fecha, hora y cámara</h2>

      <form className="filtros-ingresos-contenido" onSubmit={buscar}>
        <div className="filtro-grupo">
          <label htmlFor="fecha-desde">Desde</label>

          <div className="filtro-fecha-hora">
            <input
              id="fecha-desde"
              name="fechaDesde"
              className="filtro-fecha"
              type="date"
              value={valores.fechaDesde}
              onChange={actualizar}
            />

            <input
              name="horaDesde"
              aria-label="Hora inicial"
              className="filtro-hora"
              type="time"
              value={valores.horaDesde}
              onChange={actualizar}
              disabled={!valores.fechaDesde}
            />
          </div>
        </div>

        <div className="filtro-grupo">
          <label htmlFor="fecha-hasta">Hasta</label>

          <div className="filtro-fecha-hora">
            <input
              id="fecha-hasta"
              name="fechaHasta"
              className="filtro-fecha"
              type="date"
              value={valores.fechaHasta}
              onChange={actualizar}
            />

            <input
              name="horaHasta"
              aria-label="Hora final"
              className="filtro-hora"
              type="time"
              value={valores.horaHasta}
              onChange={actualizar}
              disabled={!valores.fechaHasta}
            />
          </div>
        </div>

        <div className="filtro-grupo filtro-camara">
          <label htmlFor="camara">Cámara</label>

          <select
            id="camara"
            name="idCamara"
            value={valores.idCamara}
            onChange={actualizar}
          >
            <option value="">Todas las cámaras</option>
            {camaras.map((camara) => (
              <option key={camara.id} value={camara.id}>
                {camara.nombre}
              </option>
            ))}
          </select>
        </div>

        <div className="filtros-botones">
          <button
            className="boton-limpiar"
            type="button"
            onClick={limpiar}
            disabled={cargando}
          >
            Limpiar filtros
          </button>

          <button
            className="boton-buscar"
            type="submit"
            disabled={cargando}
          >
            {cargando ? "Buscando..." : "Buscar"}
          </button>
        </div>
      </form>
    </section>
  );
}
