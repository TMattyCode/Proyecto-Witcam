import { useEffect, useState } from "react";
import "./Interfaz_camaras.css";
import Layout from "../../componentes/layout/Layout";
import TarjetaCamara from "./componentes/TarjetaCamara";
import EditorGruposCamara from "./componentes/EditorGruposCamara";
import FiltroSeleccionMultiple from "./componentes/FiltroSeleccionMultiple";
import imagenSimulacion from "../../assets/images/001 witcam inicio imagen.png";
import iconoCamaraAzul from "../../assets/iconos/025 icono-camara-azul.png";
import {
  detenerTransmision,
  iniciarTransmision,
  obtenerEstadoMonitoreo,
} from "../../servicios/api";

const CLAVE_CAMARAS = "witcam_camaras_prueba";
const CLAVE_CAMARA_ANTIGUA = "witcam_camara_prueba";
const CLAVE_GRUPOS_CAMARAS = "witcam_grupos_camaras_prueba";
const GRUPO_INICIAL = { id: 1, nombre: "Grupo 1" };
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
  last_error: null,
  last_event: "Detenido",
};

function leerCamarasGuardadas() {
  try {
    const coleccion = JSON.parse(localStorage.getItem(CLAVE_CAMARAS));
    if (Array.isArray(coleccion)) return coleccion;

    const anterior = JSON.parse(localStorage.getItem(CLAVE_CAMARA_ANTIGUA));
    if (anterior && typeof anterior === "object") {
      const migradas = [anterior];
      localStorage.setItem(CLAVE_CAMARAS, JSON.stringify(migradas));
      localStorage.removeItem(CLAVE_CAMARA_ANTIGUA);
      return migradas;
    }
  } catch {
    localStorage.removeItem(CLAVE_CAMARAS);
  }
  return [];
}

function normalizarNombreGrupoInicial(grupo) {
  return grupo.nombre?.trim().toLocaleLowerCase() === "grupo 1"
    ? { ...grupo, nombre: "Grupo 1" }
    : grupo;
}

function leerGruposGuardados() {
  try {
    const grupos = JSON.parse(localStorage.getItem(CLAVE_GRUPOS_CAMARAS));
    if (Array.isArray(grupos) && grupos.length) {
      const gruposNormalizados = grupos.map(normalizarNombreGrupoInicial);
      localStorage.setItem(CLAVE_GRUPOS_CAMARAS, JSON.stringify(gruposNormalizados));
      return gruposNormalizados;
    }
  } catch {
    // Si el contenido no es válido se reemplaza por el grupo inicial.
  }
  const gruposIniciales = [GRUPO_INICIAL];
  localStorage.setItem(CLAVE_GRUPOS_CAMARAS, JSON.stringify(gruposIniciales));
  return gruposIniciales;
}

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
  const [camaras, setCamaras] = useState(leerCamarasGuardadas);
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
  const [grupoCamaraId, setGrupoCamaraId] = useState("");
  const [gruposCamaras, setGruposCamaras] = useState(leerGruposGuardados);
  const [filtroAbierto, setFiltroAbierto] = useState(null);
  const [camarasSeleccionadas, setCamarasSeleccionadas] = useState(null);
  const [gruposSeleccionados, setGruposSeleccionados] = useState(null);
  const [columnasCuadricula, setColumnasCuadricula] = useState("auto");
  const [operandoId, setOperandoId] = useState(null);
  const [errorInterfaz, setErrorInterfaz] = useState("");
  const [versionStream, setVersionStream] = useState(1);
  const tieneWebcam = camaras.some((camara) => camara.tipo === "webcam");

  useEffect(() => {
    let activo = true;

    async function actualizar() {
      try {
        let siguienteEstado = await obtenerEstadoMonitoreo();
        if (!tieneWebcam && siguienteEstado.running) {
          await detenerTransmision();
          siguienteEstado = ESTADO_DETENIDO;
        }
        if (activo) {
          setEstado(siguienteEstado);
          setErrorInterfaz("");
        }
      } catch (error) {
        if (activo && tieneWebcam) setErrorInterfaz(error.message);
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

  const guardarColeccion = (siguientes) => {
    localStorage.setItem(CLAVE_CAMARAS, JSON.stringify(siguientes));
    setCamaras(siguientes);
  };

  const abrirFormulario = () => {
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
    setGrupoCamaraId("");
    setModalAbierto(true);
  };

  const abrirEdicion = (camara) => {
    setCamaraEditando(camara);
    setNombreCamara(camara.nombre);
    setGrupoCamaraId(String(camara.grupoCamaraId ?? ""));
    setModalAbierto(true);
  };

  const cerrarFormulario = () => {
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
          : `Cámara simulada ${camaras.length + 1}`,
    );
  };

  const abrirEditorGrupos = () => {
    if (!gruposCamaras.length) {
      const gruposIniciales = [GRUPO_INICIAL];
      localStorage.setItem(CLAVE_GRUPOS_CAMARAS, JSON.stringify(gruposIniciales));
      setGruposCamaras(gruposIniciales);
    } else {
      const gruposNormalizados = gruposCamaras.map(normalizarNombreGrupoInicial);
      localStorage.setItem(CLAVE_GRUPOS_CAMARAS, JSON.stringify(gruposNormalizados));
      setGruposCamaras(gruposNormalizados);
    }
    setEditorGruposAbierto(true);
  };

  const guardarCamara = (evento) => {
    evento.preventDefault();
    const nombre = nombreCamara.trim();
    if (!nombre || !grupoCamaraId) return;

    if (camaraEditando) {
      guardarColeccion(camaras.map((camara) =>
        camara.id === camaraEditando.id
          ? { ...camara, nombre, grupoCamaraId: Number(grupoCamaraId) }
          : camara
      ));
      cerrarFormulario();
      setErrorInterfaz("");
      return;
    }

    if (camaras.length >= LIMITE_CAMARAS) return;
    if (tipoCamara === "webcam" && tieneWebcam) return;
    if (
      tipoCamara === "onvif" &&
      (!direccionIp.trim() || !puertoOnvif || !usuarioConexion.trim() ||
        !passwordConexion)
    ) return;

    const nuevaCamara = {
      id: `${tipoCamara}-${Date.now()}`,
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
          }
        : {}),
    };
    guardarColeccion([...camaras, nuevaCamara]);
    cerrarFormulario();
    setErrorInterfaz("");
  };

  const iniciar = async (camara) => {
    setOperandoId(camara.id);
    setErrorInterfaz("");
    try {
      await iniciarTransmision(camara.fuente);
      setEstado((actual) => ({
        ...actual,
        running: true,
        streaming: false,
        last_error: null,
        last_event: "Iniciando camara",
      }));
      setVersionStream((version) => version + 1);
    } catch (error) {
      setErrorInterfaz(error.message);
    } finally {
      setOperandoId(null);
    }
  };

  const detener = async (camara) => {
    setOperandoId(camara.id);
    setErrorInterfaz("");
    try {
      await detenerTransmision();
      setEstado(ESTADO_DETENIDO);
      setVersionStream((version) => version + 1);
    } catch (error) {
      setErrorInterfaz(error.message);
    } finally {
      setOperandoId(null);
    }
  };

  const eliminar = async (camara) => {
    if (camara.tipo === "webcam" && estado.running) {
      await detener(camara);
    }
    guardarColeccion(camaras.filter((actual) => actual.id !== camara.id));
    setErrorInterfaz("");
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
            <button
              className="boton-anadir-camara"
              type="button"
              onClick={abrirEditorGrupos}
            >
              Editor de grupos
            </button>
            <button
              className="boton-anadir-camara"
              type="button"
              disabled={camaras.length >= LIMITE_CAMARAS}
              title={camaras.length >= LIMITE_CAMARAS ? "Máximo de nueve cámaras" : undefined}
              onClick={abrirFormulario}
            >
              <span className="boton-anadir-camara-icono">+</span>
              Añadir cámara
            </button>
          </div>
        </div>

        <div className={`camaras-area${camarasFiltradas.length ? " con-camaras" : ""}${claseCuadricula}`}>
          {camarasFiltradas.length ? (
            camarasFiltradas.map((camara) => (
              <TarjetaCamara
                key={camara.id}
                camara={camara}
                estado={camara.tipo === "webcam" ? estado : ESTADO_DETENIDO}
                errorInterfaz={camara.tipo === "webcam" ? errorInterfaz : ""}
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
              />
            ))
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

            {!camaraEditando && (tipoCamara === "webcam" ? (
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
            ))}

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
                  : "La cámara simulada no abre dispositivos ni consume el backend de video."}
            </p>}

            <div className="modal-camara-acciones">
              <button type="button" onClick={cerrarFormulario}>Cancelar</button>
              <button
                type="submit"
                disabled={
                  !nombreCamara.trim() || !grupoCamaraId ||
                  (!camaraEditando && tipoCamara === "onvif" && (
                    !direccionIp.trim() || !puertoOnvif ||
                    !usuarioConexion.trim() || !passwordConexion
                  ))
                }
              >
                {camaraEditando ? "Guardar cambios" : "Guardar cámara"}
              </button>
            </div>
          </form>
        </div>
      )}

      {editorGruposAbierto && (
        <EditorGruposCamara
          grupos={gruposCamaras}
          camaras={camaras}
          claveAlmacenamiento={CLAVE_GRUPOS_CAMARAS}
          onCambiar={setGruposCamaras}
          onCerrar={() => setEditorGruposAbierto(false)}
        />
      )}
    </Layout>
  );
}
