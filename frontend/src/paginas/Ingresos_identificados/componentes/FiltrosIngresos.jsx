import "./FiltrosIngresos.css";

export default function FiltrosIngresos() {
  return (
    <section className="filtros-ingresos">
      <h2>Filtrar por fecha y hora</h2>

      <div className="filtros-ingresos-contenido">
        <div className="filtro-grupo">
          <label>Desde</label>

          <div className="filtro-fecha-hora">
            <input
              className="filtro-fecha"
              type="date"
              defaultValue="2026-06-05"
            />

            <input
              className="filtro-hora"
              type="time"
              defaultValue="00:00"
            />
          </div>
        </div>

        <div className="filtro-grupo">
          <label>Hasta</label>

          <div className="filtro-fecha-hora">
            <input
              className="filtro-fecha"
              type="date"
              defaultValue="2026-06-05"
            />

            <input
              className="filtro-hora"
              type="time"
              defaultValue="23:59"
            />
          </div>
        </div>

        <div className="filtro-grupo filtro-camara">
          <label htmlFor="camara">Cámara</label>

          <select id="camara" defaultValue="todas">
            <option value="todas">Todas las cámaras</option>
            <option value="acceso-principal">Acceso Principal</option>
            <option value="caja-1">Caja 1</option>
            <option value="bodega">Bodega</option>
          </select>
        </div>

        <div className="filtros-botones">
          <button className="boton-limpiar" type="button">
            Limpiar filtros
          </button>

          <button className="boton-buscar" type="button">
            Buscar
          </button>
        </div>
      </div>
    </section>
  );
}