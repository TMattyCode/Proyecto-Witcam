import "./TarjetaCamara.css";

function IconoCamara() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M4 6.5h10a2 2 0 0 1 2 2v7a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2Z" />
      <path d="m16 10 5-2.5v9L16 14Z" />
    </svg>
  );
}

export default function TarjetaCamara({
  camara,
  estado,
  errorInterfaz,
  operando,
  versionStream,
  imagenSimulacion,
  nombreGrupo,
  onIniciar,
  onDetener,
  onEliminar,
}) {
  const simulada = camara.tipo === "simulada";
  const onvif = camara.tipo === "onvif";
  const enVivo = simulada || (!onvif && estado.streaming && !estado.last_error);
  const iniciando = !simulada && !onvif && estado.running && !enVivo;
  const error = simulada || onvif ? "" : errorInterfaz || estado.last_error;
  const etiquetaEstado = simulada
    ? "Simulada"
    : onvif
      ? "Sin configurar"
    : error
      ? "Error de conexión"
      : enVivo
        ? "En vivo"
        : iniciando
          ? "Iniciando"
          : "Detenida";
  const descripcionFuente = simulada
    ? `Imagen de prueba · ${camara.escena}`
    : onvif
      ? "Cámara de red · ONVIF"
      : `Webcam local · Dispositivo ${camara.fuente}`;
  const descripcion = `${descripcionFuente} · ${nombreGrupo}`;

  return (
    <article className={`tarjeta-camara${simulada ? ` simulada escena-${camara.escena}` : ""}`}>
      <header className="tarjeta-camara-encabezado">
        <div className="tarjeta-camara-identidad">
          <span className="tarjeta-camara-icono"><IconoCamara /></span>
          <div>
            <h2>{camara.nombre}</h2>
            <p>{descripcion}</p>
          </div>
        </div>

        <span className={`tarjeta-camara-estado ${error ? "error" : enVivo ? "activo" : ""}`}>
          <span aria-hidden="true" />
          {etiquetaEstado}
        </span>
      </header>

      <div className="tarjeta-camara-video">
        <img
          src={simulada ? imagenSimulacion : onvif ? imagenSimulacion : `/video_feed?v=${versionStream}`}
          alt={simulada ? `Vista simulada de ${camara.nombre}` : onvif ? `Cámara ONVIF ${camara.nombre}` : `Transmisión de ${camara.nombre}`}
        />

        {simulada && (
          <span className="tarjeta-camara-marca">SIMULACIÓN · {camara.escena}</span>
        )}

        {!simulada && !enVivo && !iniciando && (
          <div className="tarjeta-camara-video-estado">
            <IconoCamara />
            <strong>{onvif ? "Cámara ONVIF sin configurar" : "Cámara detenida"}</strong>
            <span>{onvif ? "Completa los datos de conexión para utilizarla." : "Inicia la transmisión para ver la webcam."}</span>
          </div>
        )}
      </div>

      {error && <p className="tarjeta-camara-error">{error}</p>}

      <footer className="tarjeta-camara-acciones">
        {!simulada && !onvif && (
          estado.running ? (
            <button className="boton-camara detener" type="button" disabled={operando} onClick={onDetener}>
              Detener transmisión
            </button>
          ) : (
            <button className="boton-camara iniciar" type="button" disabled={operando} onClick={onIniciar}>
              {operando ? "Abriendo webcam..." : "Iniciar transmisión"}
            </button>
          )
        )}

        <button className="boton-camara secundario" type="button" disabled={operando} onClick={onEliminar}>
          Eliminar cámara
        </button>
      </footer>
    </article>
  );
}
