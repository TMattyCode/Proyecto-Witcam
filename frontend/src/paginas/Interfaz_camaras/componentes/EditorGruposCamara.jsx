import { useState } from "react";
import "./EditorGruposCamara.css";

export default function EditorGruposCamara({
  grupos,
  camaras,
  claveAlmacenamiento,
  onCambiar,
  onCerrar,
}) {
  const [gruposBorrador, setGruposBorrador] = useState(() =>
    grupos.map((grupo) => ({ ...grupo })),
  );
  const [nombreGrupo, setNombreGrupo] = useState("");
  const [error, setError] = useState("");

  const crearGrupo = (evento) => {
    evento.preventDefault();
    const nombre = nombreGrupo.trim();
    if (!nombre) return;

    const repetido = gruposBorrador.some(
      (grupo) => grupo.nombre.toLocaleLowerCase() === nombre.toLocaleLowerCase(),
    );
    if (repetido) {
      setError("Ya existe un grupo con ese nombre.");
      return;
    }

    setGruposBorrador([
      ...gruposBorrador,
      { id: Date.now(), nombre },
    ]);
    setNombreGrupo("");
    setError("");
  };

  const cambiarNombreGrupo = (id, nombre) => {
    setGruposBorrador((actuales) =>
      actuales.map((grupo) => grupo.id === id ? { ...grupo, nombre } : grupo),
    );
    setError("");
  };

  const eliminarGrupo = (grupo) => {
    if (gruposBorrador.length === 1) {
      setError("Debe existir al menos un grupo de cámaras.");
      return;
    }

    const estaEnUso = camaras.some(
      (camara) => Number(camara.grupoCamaraId) === Number(grupo.id),
    );
    if (estaEnUso) {
      setError("No se puede eliminar un grupo asignado a una cámara.");
      return;
    }

    setGruposBorrador(
      gruposBorrador.filter((actual) => actual.id !== grupo.id),
    );
    setError("");
  };

  const guardarCambios = () => {
    const normalizados = gruposBorrador.map((grupo) => ({
      ...grupo,
      nombre: grupo.nombre.trim(),
    }));
    if (normalizados.some((grupo) => !grupo.nombre)) {
      setError("Todos los grupos deben tener un nombre.");
      return;
    }

    const nombres = normalizados.map((grupo) => grupo.nombre.toLocaleLowerCase());
    if (new Set(nombres).size !== nombres.length) {
      setError("No puede haber grupos con el mismo nombre.");
      return;
    }

    localStorage.setItem(claveAlmacenamiento, JSON.stringify(normalizados));
    onCambiar(normalizados);
    onCerrar();
  };

  return (
    <div className="modal-camara-fondo" role="presentation">
      <section
        className="modal-camara editor-grupos"
        role="dialog"
        aria-modal="true"
        aria-labelledby="titulo-editor-grupos"
      >
        <div className="modal-camara-cabecera">
          <div>
            <span>Organización de cámaras</span>
            <h2 id="titulo-editor-grupos">Editor de grupos</h2>
          </div>
          <div className="editor-grupos-cabecera-acciones">
            <button
              className="editor-grupos-guardar"
              type="button"
              onClick={guardarCambios}
            >
              Guardar cambios
            </button>
            <button type="button" aria-label="Cerrar sin guardar" onClick={onCerrar}>×</button>
          </div>
        </div>

        <form className="editor-grupos-formulario" onSubmit={crearGrupo}>
          <label htmlFor="nombre-grupo">Nombre del grupo</label>
          <div className="editor-grupos-nuevo">
            <input
              id="nombre-grupo"
              value={nombreGrupo}
              maxLength={150}
              autoFocus
              placeholder="Ej.: Entrada principal"
              onChange={(evento) => {
                setNombreGrupo(evento.target.value);
                setError("");
              }}
            />
            <button type="submit" disabled={!nombreGrupo.trim()}>Crear grupo</button>
          </div>
        </form>

        <div className="editor-grupos-listado">
          <h3>Grupos actuales</h3>
          {gruposBorrador.length ? (
            <ul>
              {gruposBorrador.map((grupo) => {
                const cantidadCamaras = camaras.filter(
                  (camara) => Number(camara.grupoCamaraId) === Number(grupo.id),
                ).length;
                return (
                  <li key={grupo.id}>
                    <div>
                      <input
                        aria-label={`Nombre del grupo ${grupo.nombre}`}
                        value={grupo.nombre}
                        maxLength={150}
                        onChange={(evento) => cambiarNombreGrupo(grupo.id, evento.target.value)}
                      />
                      <span>{cantidadCamaras} {cantidadCamaras === 1 ? "cámara" : "cámaras"}</span>
                    </div>
                    <button
                      type="button"
                      title={
                        gruposBorrador.length === 1
                          ? "Debe existir al menos un grupo"
                          : cantidadCamaras
                            ? "El grupo tiene cámaras asignadas"
                            : "Eliminar grupo"
                      }
                      onClick={() => eliminarGrupo(grupo)}
                    >
                      Eliminar
                    </button>
                  </li>
                );
              })}
            </ul>
          ) : (
            <p className="editor-grupos-vacio">Todavía no hay grupos creados.</p>
          )}
        </div>

        {error && <p className="editor-grupos-error" role="alert">{error}</p>}

      </section>
    </div>
  );
}
