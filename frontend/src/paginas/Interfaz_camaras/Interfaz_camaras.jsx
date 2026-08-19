import { useEffect, useState } from "react";
import "./Interfaz_camaras.css";
import Layout from "../../componentes/layout/Layout";
import TarjetaCamara from "./componentes/TarjetaCamara";
import EditorGruposCamara from "./componentes/EditorGruposCamara";
import FiltroSeleccionMultiple from "./componentes/FiltroSeleccionMultiple";
import imagenSimulacion from "../../assets/images/001 witcam inicio imagen.png";
import iconoCamaraAzul from "../../assets/iconos/025 icono-camara-azul.png";
import { useAutenticacion } from "../../contextos/AutenticacionContext";
import { PERMISOS, tienePermiso } from "../../utilidades/permisos";
import {
  crearCamara,
  detenerTransmision,
  editarCamara,
  eliminarCamara,
  guardarGruposCamara,
  iniciarTransmision,
  obtenerCamarasConfiguradas,
  obtenerEstadoMonitoreo,
} from "../../servicios/api";

const LIMITE_CAMARAS = 9;
const ESCENAS_SIMULADAS = [
  { valor: "entrada", nombre: "Entrada principal" },
  { valor: "pasillo", nombre: "Pasillo interior" },
  { valor: "caja", nombre: "Sector de cajas" },
  { valor: "bodega", nombre: "Bodega" },
];
const ESTADO_DETENIDO = {
  running: false,
  streaming: false,
  camera_id: null,
  last_error: null,
  last_event: "Detenido",
};

function IconoVista() {
  return <img src={iconoCamaraAzul} alt="" aria-hidden="true" />;
}

function IconoCamaraVacia() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M4 6.5h10a2 2 0 0 1 2 2v7a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2Z" />
      <path d="m16 10 5-2.5v9L16 14Z" />
    </svg>
  );
}

function IconoFlechaFiltro() {
  return (
    <span className="control-flecha" aria-hidden="true">
      <svg viewBox="0 0 12 8">
        <path d="m1 1.5 5 5 5-5" />
      </svg>
    </span>
  );
}

export default function InterfazCamaras() {
  const { usuario } = useAutenticacion();
  const esAdministrador = usuario?.rol === "Administrador";
  const puedeControlar = tienePermiso(
    usuario,
    PERMISOS.GESTIONAR_CAMARAS,
  );
  const [camaras, setCamaras] = useState([]);
  const [estado, setEstado] = useState(ESTADO_DETENIDO);
  const [modalAbierto, setModalAbierto] = useState(false);
  const [camaraEditando, setCamaraEditando] = useState(null);
  const [editorGruposAbierto, setEditorGruposAbierto] = useState(false);
  const [tipoCamara, setTipoCamara] = useState("webcam");
  const [nombreCamara, setNombreCamara] = useState("Webcam integrada");
  const [escena, setEscena] = useState(ESCENAS_SIMULADAS[0].valor);
  const [direccionIp, setDireccionIp] = useState("");
  const [puertoOnvif, setPuertoOnvif] = useState("80");
  const [usuarioConexion, setUsuarioConexion] = useState("");
  const [passwordConexion, setPasswordConexion] = useState("");
  const [fuenteVideo, setFuenteVideo] = useState("");
  const [grupoCamaraId, setGrupoCamaraId] = useState("");
  const [gruposCamaras, setGruposCamaras] = useState([]);
  const [filtroAbierto, setFiltroAbierto] = useState(null);
  const [camarasSeleccionadas, setCamarasSeleccionadas] = useState(null);
  const [gruposSeleccionados, setGruposSeleccionados] = useState(null);
  const [columnasCuadricula, setColumnasCuadricula] = useState("auto");
  const [operandoId, setOperandoId] = useState(null);
  const [errorOperacion, setErrorOperacion] = useState("");
  const [errorMonitoreo, setErrorMonitoreo] = useState("");
  const [versionStream, setVersionStream] = useState(1);
  const [cargandoConfiguracion, setCargandoConfiguracion] = useState(true);
  const tieneWebcam = camaras.some((camara) => camara.tipo === "webcam");

  const aplicarConfiguracion = (respuesta) => {
    setCamaras(respuesta.camaras || []);
    setGruposCamaras(respuesta.grupos || []);
  };

  useEffect(() => {
    let activo = true;
    obtenerCamarasConfiguradas()
      .then((respuesta) => {
        if (activo) {
          aplicarConfiguracion(respuesta);
          setErrorOperacion("");
        }
      })
      .catch((error) => {
        if (activo) setErrorOperacion(error.message);
      })
      .finally(() => {
        if (activo) setCargandoConfiguracion(false);
      });
    return () => {
      activo = false;
    };
  }, []);

  useEffect(() => {
    let activo = true;
    let solicitudEnCurso = false;
    let conexionConfirmada = false;

    async function actualizar() {
      if (solicitudEnCurso) return;
      solicitudEnCurso = true;
      try {
        const siguienteEstado = await obtenerEstadoMonitoreo();
        if (activo) {
          conexionConfirmada = true;
          setEstado(siguienteEstado);
          setErrorMonitoreo("");
        }
      } catch (error) {
        if (activo && tieneWebcam) {
          if (!conexionConfirmada) {
            setErrorMonitoreo(error.message);
          }
        }
      } finally {
        solicitudEnCurso = false;
      }
    }

    actualizar();
    if (!tieneWebcam) {
      return () => {
        activo = false;
      };
    }
    const intervalo = window.setInterval(actualizar, 1000);
    return () => {
      activo = false;
      window.clearInterval(intervalo);
    };
  }, [tieneWebcam]);

  const abrirFormulario = () => {
    setErrorOperacion("");
    setCamaraEditando(null);
    const tipoInicial = tieneWebcam ? "simulada" : "webcam";
    setTipoCamara(tipoInicial);
    setNombreCamara(
      tipoInicial === "webcam"
        ? "Webcam integrada"
        : `Cámara simulada ${camaras.length + 1}`,
    );
    setEscena(ESCENAS_SIMULADAS[camaras.length % ESCENAS_SIMULADAS.length].valor);
    setDireccionIp("");
    setPuertoOnvif("80");
    setUsuarioConexion("");
    setPasswordConexion("");
    setFuenteVideo("");
    setGrupoCamaraId("");
    setModalAbierto(true);
  };

  const abrirEdicion = (camara) => {
    if (estado.running && Number(estado.camera_id) === Number(camara.id)) {
      setErrorOperacion(
        "Deten la transmision antes de editar la camara.",
      );
      return;
    }
    setErrorOperacion("");
    setCamaraEditando(camara);
    setTipoCamara(camara.tipo);
    setNombreCamara(camara.nombre);
    setGrupoCamaraId(String(camara.grupoCamaraId ?? ""));
    setEscena(camara.escena || ESCENAS_SIMULADAS[0].valor);
    setDireccionIp(camara.direccionIp || "");
    setPuertoOnvif(String(camara.puertoOnvif || 80));
    setUsuarioConexion(camara.usuarioConexion || "");
    setPasswordConexion("");
    setFuenteVideo(camara.fuenteVideo || "");
    setModalAbierto(true);
  };

  const cerrarFormulario = () => {
    setErrorOperacion("");
    setModalAbierto(false);
    setCamaraEditando(null);
  };

  const cambiarTipo = (evento) => {
    const tipo = evento.target.value;
    setTipoCamara(tipo);
    setNombreCamara(
      tipo === "webcam"
        ? "Webcam integrada"
        : tipo === "onvif"
          ? `Cámara ONVIF ${camaras.length + 1}`
          : tipo === "rtsp"
            ? `Stream RTSP ${camaras.length + 1}`
            : `Cámara simulada ${camaras.length + 1}`,
    );
  };

  const abrirEditorGrupos = () => {
    setEditorGruposAbierto(true);
  };

  const guardarCamara = async (evento) => {
    evento.preventDefault();
    const nombre = nombreCamara.trim();
    if (!nombre || !grupoCamaraId) return;

    if (!camaraEditando && camaras.length >= LIMITE_CAMARAS) return;
    if (!camaraEditando && tipoCamara === "webcam" && tieneWebcam) return;
    if (
      tipoCamara === "onvif" &&
      (!direccionIp.trim() || !puertoOnvif || !usuarioConexion.trim() ||
        (!camaraEditando && !passwordConexion))
    ) return;
    if (tipoCamara === "rtsp" && !fuenteVideo.trim()) return;

    const datosCamara = {
      ...(camaraEditando ? { id: camaraEditando.id } : {}),
      nombre,
      tipo: tipoCamara,
      fuente: tipoCamara === "webcam" ? 0 : null,
      escena: tipoCamara === "simulada" ? escena : null,
      grupoCamaraId: Number(grupoCamaraId),
      ...(tipoCamara === "onvif"
        ? {
            direccionIp: direccionIp.trim(),
            puertoOnvif: Number(puertoOnvif),
            usuarioConexion: usuarioConexion.trim(),
            passwordConexion,
          }
        : {}),
      ...(tipoCamara === "rtsp"
        ? { fuenteVideo: fuenteVideo.trim() }
        : {}),
    };
    setOperandoId(camaraEditando?.id || "creando");
    try {
      const respuesta = camaraEditando
        ? await editarCamara(datosCamara)
        : await crearCamara(datosCamara);
      aplicarConfiguracion(respuesta);
      cerrarFormulario();
      setErrorOperacion("");
    } catch (error) {
      setErrorOperacion(error.message);
    } finally {
      setOperandoId(null);
    }
  };

  const guardarGrupos = async (grupos) => {
    const respuesta = await guardarGruposCamara(grupos);
    aplicarConfiguracion(respuesta);
  };

  const iniciar = async (camara) => {
    setOperandoId(camara.id);
    setErrorMonitoreo("");
    try {
      await iniciarTransmision(camara.fuente, true, camara.id);
      setEstado((actual) => ({
        ...actual,
        running: true,
        streaming: false,
        camera_id: camara.id,
        last_error: null,
        last_event: "Iniciando camara y modelos de IA",
      }));
      setVersionStream((version) => version + 1);
    } catch (error) {
      setErrorMonitoreo(error.message);
    } finally {
      setOperandoId(null);
    }
  };

  const detener = async (camara) => {
    setOperandoId(camara.id);
    setErrorMonitoreo("");
    try {
      await detenerTransmision();
      setEstado(ESTADO_DETENIDO);
      setVersionStream((version) => version + 1);
    } catch (error) {
      setErrorMonitoreo(error.message);
    } finally {
      setOperandoId(null);
    }
  };

  const eliminar = async (camara) => {
    if (
      estado.running
      && Number(estado.camera_id) === Number(camara.id)
    ) {
      setErrorOperacion(
        "Deten la transmision antes de eliminar la camara.",
      );
      return;
    }
    setOperandoId(camara.id);
    try {
      const respuesta = await eliminarCamara(camara.id);
      aplicarConfiguracion(respuesta);
      setErrorOperacion("");
    } catch (error) {
      setErrorOperacion(error.message);
    } finally {
      setOperandoId(null);
    }
  };

  const camarasFiltradas = camaras.filter((camara) => {
    const incluidaPorNombre = camarasSeleccionadas === null ||
      camarasSeleccionadas.includes(String(camara.id));
    const incluidaPorGrupo = gruposSeleccionados === null ||
      gruposSeleccionados.includes(String(camara.grupoCamaraId));
    return incluidaPorNombre && incluidaPorGrupo;
  });
  const claseCantidad = ` cantidad-${Math.min(camarasFiltradas.length, 5)}`;
  const opcionesCamaras = camaras
    .filter((camara) =>
      gruposSeleccionados === null ||
      gruposSeleccionados.includes(String(camara.grupoCamaraId)),
    )
    .map((camara) => ({
      id: String(camara.id),
      nombre: camara.nombre,
    }));
  const opcionesGrupos = gruposCamaras.map((grupo) => ({
    id: String(grupo.id),
    nombre: grupo.nombre,
  }));
  const claseCuadricula = columnasCuadricula === "auto"
    ? claseCantidad
    : ` cuadricula-columnas-${columnasCuadricula}`;

  return (
    <Layout
      titulo="Interfaz de cámaras"
      subtitulo="Visualiza en tiempo real las cámaras conectadas a tu sistema."
      compacto
    >
      <section className="camaras-panel">
        <div className="camaras-barra-superior">
          <div className="camaras-barra-resumen">
            <div className="camaras-tab activo">
              <span className="camaras-tab-icono"><IconoVista /></span>
              Vista en vivo
            </div>
            <span className="camaras-contador">
              {camarasFiltradas.length === camaras.length
                ? `${camaras.length} ${camaras.length === 1 ? "cámara" : "cámaras"}`
                : `${camarasFiltradas.length} de ${camaras.length} cámaras`}
            </span>
          </div>

          <div className="camaras-controles">
            <div className="filtro-camaras-contenedor">
              <button
                className={`control-camaras-boton${columnasCuadricula !== "auto" ? " filtro-activo" : ""}`}
                type="button"
                aria-expanded={filtroAbierto === "cuadricula"}
                onClick={() => setFiltroAbierto(
                  filtroAbierto === "cuadricula" ? null : "cuadricula",
                )}
              >
                {columnasCuadricula === "auto"
                  ? "Cuadrícula automática"
                  : `${columnasCuadricula} por fila`}
                <IconoFlechaFiltro />
              </button>
              {filtroAbierto === "cuadricula" && (
                <section className="selector-cuadricula" aria-label="Opciones de cuadrícula">
                  <strong>Cámaras por fila</strong>
                  {[
                    { valor: "auto", etiqueta: "Automática" },
                    { valor: "1", etiqueta: "1 cámara por fila" },
                    { valor: "2", etiqueta: "2 cámaras por fila" },
                    { valor: "3", etiqueta: "3 cámaras por fila" },
                  ].map((opcion) => (
                    <label key={opcion.valor}>
                      <input
                        type="radio"
                        name="columnas-cuadricula"
                        value={opcion.valor}
                        checked={columnasCuadricula === opcion.valor}
                        onChange={() => {
                          setColumnasCuadricula(opcion.valor);
                          setFiltroAbierto(null);
                        }}
                      />
                      <span className={`vista-columnas columnas-${opcion.valor}`} aria-hidden="true">
                        <i /><i /><i />
                      </span>
                      {opcion.etiqueta}
                    </label>
                  ))}
                </section>
              )}
            </div>
            <div className="filtro-camaras-contenedor">
              <button
                className={`control-camaras-boton${gruposSeleccionados !== null ? " filtro-activo" : ""}`}
                type="button"
                aria-expanded={filtroAbierto === "grupos"}
                onClick={() => setFiltroAbierto(
                  filtroAbierto === "grupos" ? null : "grupos",
                )}
              >
                Grupo cámaras
                <IconoFlechaFiltro />
              </button>
              {filtroAbierto === "grupos" && (
                <FiltroSeleccionMultiple
                  titulo="Filtrar por grupo"
                  placeholder="Buscar grupo..."
                  opciones={opcionesGrupos}
                  seleccion={gruposSeleccionados}
                  onAplicar={setGruposSeleccionados}
                  onCerrar={() => setFiltroAbierto(null)}
                />
              )}
            </div>
            <div className="filtro-camaras-contenedor">
              <button
                className={`control-camaras-boton${camarasSeleccionadas !== null ? " filtro-activo" : ""}`}
                type="button"
                aria-expanded={filtroAbierto === "camaras"}
                onClick={() => setFiltroAbierto(
                  filtroAbierto === "camaras" ? null : "camaras",
                )}
              >
                Filtrar cámaras
                <IconoFlechaFiltro />
              </button>
              {filtroAbierto === "camaras" && (
                <FiltroSeleccionMultiple
                  titulo="Filtrar cámaras"
                  placeholder="Buscar cámara..."
                  opciones={opcionesCamaras}
                  seleccion={camarasSeleccionadas}
                  onAplicar={setCamarasSeleccionadas}
                  onCerrar={() => setFiltroAbierto(null)}
                />
              )}
            </div>
            {esAdministrador && <button
              className="boton-anadir-camara"
              type="button"
              onClick={abrirEditorGrupos}
            >
              Editor de grupos
            </button>}
            {esAdministrador && <button
              className="boton-anadir-camara"
              type="button"
              disabled={camaras.length >= LIMITE_CAMARAS}
              title={camaras.length >= LIMITE_CAMARAS ? "Máximo de nueve cámaras" : undefined}
              onClick={abrirFormulario}
            >
              <span className="boton-anadir-camara-icono">+</span>
              Añadir cámara
            </button>}
          </div>
        </div>

        {!modalAbierto && errorOperacion && (
          <div className="camaras-error-operacion" role="alert">
            {errorOperacion}
          </div>
        )}

        <div className={`camaras-area${camarasFiltradas.length ? " con-camaras" : ""}${claseCuadricula}`}>
          {camarasFiltradas.length ? (
            camarasFiltradas.map((camara) => (
              <TarjetaCamara
                key={camara.id}
                camara={camara}
                estado={camara.tipo === "webcam" ? estado : ESTADO_DETENIDO}
                errorInterfaz={camara.tipo === "webcam" ? errorMonitoreo : ""}
                operando={operandoId === camara.id}
                versionStream={versionStream}
                imagenSimulacion={imagenSimulacion}
                nombreGrupo={
                  gruposCamaras.find(
                    (grupo) => Number(grupo.id) === Number(camara.grupoCamaraId),
                  )?.nombre || "Sin grupo"
                }
                onIniciar={() => iniciar(camara)}
                onDetener={() => detener(camara)}
                onEditar={() => abrirEdicion(camara)}
                onEliminar={() => eliminar(camara)}
                gestionHabilitada={esAdministrador}
                controlHabilitado={puedeControlar}
              />
            ))
          ) : cargandoConfiguracion ? (
            <div className="camaras-vista-vacia">
              <h2>Cargando cámaras...</h2>
            </div>
          ) : camaras.length ? (
            <div className="camaras-vista-vacia">
              <div className="camaras-vista-icono"><IconoCamaraVacia /></div>
              <h2>No hay cámaras que coincidan</h2>
              <p>Cambia la selección de los filtros para volver a mostrar cámaras.</p>
            </div>
          ) : (
            <div className="camaras-vista-vacia">
              <div className="camaras-vista-icono"><IconoCamaraVacia /></div>
              <h2>No hay cámaras añadidas</h2>
              <p>
                Añade una webcam o cámaras simuladas para comprobar cómo se
                adapta la cuadrícula antes de conectar múltiples streams reales.
              </p>
            </div>
          )}
        </div>
      </section>

      {modalAbierto && (
        <div className="modal-camara-fondo" role="presentation">
          <form
            className="modal-camara"
            role="dialog"
            aria-modal="true"
            aria-labelledby="titulo-formulario-camara"
            onSubmit={guardarCamara}
          >
            <div className="modal-camara-cabecera">
              <div>
                <span>{camaraEditando ? "Configuración de cámara" : "Configuración de prueba"}</span>
                <h2 id="titulo-formulario-camara">
                  {camaraEditando ? "Editar cámara" : "Añadir cámara"}
                </h2>
              </div>
              <button type="button" aria-label="Cerrar" onClick={cerrarFormulario}>
                ×
              </button>
            </div>

            {!camaraEditando && (
              <>
                <label htmlFor="tipo-camara">Tipo de fuente</label>
                <select id="tipo-camara" value={tipoCamara} onChange={cambiarTipo}>
                  <option value="webcam" disabled={tieneWebcam}>Webcam local</option>
                  <option value="onvif">Cámara ONVIF</option>
                  <option value="rtsp">Stream RTSP o canal NVR</option>
                  <option value="simulada">Cámara simulada con imagen</option>
                </select>
              </>
            )}

            <label htmlFor="nombre-camara">Nombre de la cámara</label>
            <input
              id="nombre-camara"
              value={nombreCamara}
              maxLength={80}
              autoFocus
              onChange={(evento) => setNombreCamara(evento.target.value)}
            />

            {tipoCamara === "webcam" ? (
              <>
                <label htmlFor="dispositivo-camara">Dispositivo</label>
                <select id="dispositivo-camara" value="0" disabled>
                  <option value="0">Webcam 0</option>
                </select>
              </>
            ) : tipoCamara === "simulada" ? (
              <>
                <label htmlFor="escena-camara">Imagen de prueba</label>
                <select id="escena-camara" value={escena} onChange={(evento) => setEscena(evento.target.value)}>
                  {ESCENAS_SIMULADAS.map((opcion) => (
                    <option key={opcion.valor} value={opcion.valor}>{opcion.nombre}</option>
                  ))}
                </select>
              </>
            ) : tipoCamara === "rtsp" ? (
              <>
                <label htmlFor="fuente-video-camara">URL del stream RTSP</label>
                <input
                  id="fuente-video-camara"
                  type="url"
                  maxLength={1000}
                  spellCheck="false"
                  placeholder="rtsp://127.0.0.1:8554/camara1"
                  value={fuenteVideo}
                  onChange={(evento) => setFuenteVideo(evento.target.value)}
                />
              </>
            ) : (
              <>
                <label htmlFor="direccion-ip-camara">Dirección IP</label>
                <input
                  id="direccion-ip-camara"
                  type="text"
                  inputMode="decimal"
                  placeholder="192.168.1.50"
                  value={direccionIp}
                  onChange={(evento) => setDireccionIp(evento.target.value)}
                />

                <label htmlFor="puerto-onvif-camara">Puerto ONVIF</label>
                <input
                  id="puerto-onvif-camara"
                  type="number"
                  min="1"
                  max="65535"
                  value={puertoOnvif}
                  onChange={(evento) => setPuertoOnvif(evento.target.value)}
                />

                <label htmlFor="usuario-onvif-camara">Usuario</label>
                <input
                  id="usuario-onvif-camara"
                  type="text"
                  autoComplete="username"
                  value={usuarioConexion}
                  onChange={(evento) => setUsuarioConexion(evento.target.value)}
                />

                <label htmlFor="password-onvif-camara">Contraseña</label>
                <input
                  id="password-onvif-camara"
                  type="password"
                  autoComplete="current-password"
                  value={passwordConexion}
                  onChange={(evento) => setPasswordConexion(evento.target.value)}
                />

              </>
            )}

            <label htmlFor="grupo-camara">Grupo</label>
            <select
              id="grupo-camara"
              value={grupoCamaraId}
              onChange={(evento) => setGrupoCamaraId(evento.target.value)}
            >
              <option value="" disabled>
                {gruposCamaras.length ? "Selecciona un grupo" : "No hay grupos disponibles"}
              </option>
              {gruposCamaras.map((grupo) => (
                <option key={grupo.id} value={grupo.id}>{grupo.nombre}</option>
              ))}
            </select>

            {!camaraEditando && <p>
              {tipoCamara === "webcam"
                ? "La webcam transmitirá sin activar todavía el análisis de IA."
                : tipoCamara === "onvif"
                  ? "La fuente ONVIF quedará registrada, pero no se conectará todavía."
                  : tipoCamara === "rtsp"
                    ? "El stream RTSP quedará registrado para conectarlo al motor de video en el siguiente paso."
                    : "La cámara simulada no abre dispositivos ni consume el backend de video."}
            </p>}

            {errorOperacion && (
              <p className="modal-camara-error" role="alert">
                {errorOperacion}
              </p>
            )}

            <div className="modal-camara-acciones">
              <button type="button" onClick={cerrarFormulario}>Cancelar</button>
              <button
                type="submit"
                disabled={
                  !nombreCamara.trim() || !grupoCamaraId ||
                  (!camaraEditando && tipoCamara === "onvif" && (
                    !direccionIp.trim() || !puertoOnvif ||
                    !usuarioConexion.trim() || !passwordConexion
                  )) ||
                  (tipoCamara === "rtsp" && !fuenteVideo.trim())
                }
              >
                {camaraEditando ? "Guardar cambios" : "Guardar cámara"}
              </button>
            </div>
          </form>
        </div>
      )}

      {editorGruposAbierto && esAdministrador && (
        <EditorGruposCamara
          grupos={gruposCamaras}
          camaras={camaras}
          onGuardar={guardarGrupos}
          onCerrar={() => setEditorGruposAbierto(false)}
        />
      )}
    </Layout>
  );
}
