import "./TarjetaCamara.css";
import iconoBasurero from "../../../assets/iconos/028 icono-basurero.png";
import iconoEditar from "../../../assets/iconos/029 icono-editar.blanco.png";
import { obtenerTokenSesion } from "../../../servicios/api";

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
  onEditar,
  onEliminar,
  gestionHabilitada = true,
  controlHabilitado = true,
}) {
  const simulada = camara.tipo === "simulada";
  const onvif = camara.tipo === "onvif";
  const rtsp = camara.tipo === "rtsp";
  const fuenteRed = onvif || rtsp;
  const transmitiendo = estado.running;
  const enVivo = simulada || (!fuenteRed && estado.streaming && !estado.last_error);
  const iniciando = !simulada && !fuenteRed && estado.running && !enVivo;
  const error = simulada || fuenteRed ? "" : errorInterfaz || estado.last_error;
  const etiquetaEstado = simulada
    ? "Simulada"
    : fuenteRed
      ? "Registrada"
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
      : rtsp
        ? "Stream de red · RTSP"
      : `Webcam local · Dispositivo ${camara.fuente}`;
  const descripcion = `${descripcionFuente} · ${nombreGrupo}`;
  const token = obtenerTokenSesion();
  const rutaStream = `/video_feed?token=${encodeURIComponent(token || "")}&v=${versionStream}`;

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
          src={simulada || fuenteRed ? imagenSimulacion : rutaStream}
          alt={simulada ? `Vista simulada de ${camara.nombre}` : fuenteRed ? `Fuente de red ${camara.nombre}` : `Transmisión de ${camara.nombre}`}
        />

        {simulada && (
          <span className="tarjeta-camara-marca">SIMULACIÓN · {camara.escena}</span>
        )}

        {!simulada && !enVivo && !iniciando && (
          <div className="tarjeta-camara-video-estado">
            <IconoCamara />
            <strong>{fuenteRed ? "Fuente de red registrada" : "Cámara detenida"}</strong>
            <span>{fuenteRed ? "La conexión al motor de video se habilitará en el siguiente paso." : "Inicia la transmisión para ver la webcam."}</span>
          </div>
        )}
      </div>

      {error && <p className="tarjeta-camara-error">{error}</p>}

      <footer className="tarjeta-camara-acciones">
        {controlHabilitado && !simulada && !fuenteRed && (
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

        {gestionHabilitada && <div className="tarjeta-camara-acciones-iconos">
          <button
            className="boton-camara editar"
            type="button"
            disabled={operando || transmitiendo}
            onClick={onEditar}
            aria-label={`Editar cámara ${camara.nombre}`}
            title="Editar cámara"
          >
            <img src={iconoEditar} alt="" aria-hidden="true" />
          </button>
          <button
            className="boton-camara eliminar"
            type="button"
            disabled={operando || transmitiendo}
            onClick={onEliminar}
            aria-label={`Eliminar cámara ${camara.nombre}`}
            title="Eliminar cámara"
          >
            <img src={iconoBasurero} alt="" aria-hidden="true" />
          </button>
        </div>}
      </footer>
    </article>
  );
}
