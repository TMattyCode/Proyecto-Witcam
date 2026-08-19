export const EVENTO_SESION_EXPIRADA = "witcam:sesion-expirada";
const ESPERA_REINTENTO_GET_MS = 250;

function obtenerToken() {
  return (
    localStorage.getItem("witcam_token")
    || sessionStorage.getItem("witcam_token")
  );
}

export function obtenerTokenSesion() {
  return obtenerToken();
}

function notificarSesionExpirada(ruta, respuesta) {
  if (respuesta.status !== 401 || ruta === "/api/auth/login") return;
  globalThis.dispatchEvent?.(new Event(EVENTO_SESION_EXPIRADA));
}

function esperar(milisegundos) {
  return new Promise((resolver) => globalThis.setTimeout(resolver, milisegundos));
}

async function obtenerRespuesta(ruta, opciones, token) {
  const metodo = (opciones.method || "GET").toUpperCase();
  const intentos = metodo === "GET" ? 2 : 1;
  let ultimoError;

  for (let intento = 0; intento < intentos; intento += 1) {
    try {
      const respuesta = await fetch(ruta, {
        ...opciones,
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
          ...opciones.headers,
        },
      });
      const tipoContenido = respuesta.headers.get("content-type") || "";
      if (tipoContenido.includes("application/json") || intento === intentos - 1) {
        return respuesta;
      }
    } catch (error) {
      ultimoError = error;
      if (intento === intentos - 1) throw error;
    }
    await esperar(ESPERA_REINTENTO_GET_MS);
  }

  throw ultimoError;
}

async function solicitar(ruta, opciones = {}) {
  const token = obtenerToken();
  let respuesta;
  try {
    respuesta = await obtenerRespuesta(ruta, opciones, token);
  } catch {
    throw new Error(
      "No se pudo conectar con Witcam. Verifica que el servidor de Python esté funcionando.",
    );
  }
  notificarSesionExpirada(ruta, respuesta);
  const tipoContenido = respuesta.headers.get("content-type") || "";
  if (!tipoContenido.includes("application/json")) {
    throw new Error(
      "El backend no devolvió una respuesta válida. Reinicia el servidor de Python.",
    );
  }
  let datos;
  try {
    datos = await respuesta.json();
  } catch {
    throw new Error(
      "El backend devolvió una respuesta incompleta. Inténtalo nuevamente.",
    );
  }
  if (!respuesta.ok) {
    throw new Error(datos.error || "No se pudo completar la solicitud");
  }
  return datos;
}

export function registrarCuenta(datos) {
  return solicitar("/api/auth/register", {
    method: "POST",
    body: JSON.stringify(datos),
  });
}

export function iniciarSesion(datos) {
  return solicitar("/api/auth/login", {
    method: "POST",
    body: JSON.stringify(datos),
  });
}

export function obtenerSesion() {
  return solicitar("/api/auth/session");
}

export function actualizarPerfil(datos) {
  return solicitar("/api/perfil", {
    method: "POST",
    body: JSON.stringify(datos),
  });
}

export function obtenerResumenCuenta() {
  return solicitar("/api/cuenta/resumen");
}

export function obtenerSubusuarios(filtros = {}) {
  const parametros = new URLSearchParams();
  Object.entries(filtros).forEach(([clave, valor]) => {
    if (valor !== "" && valor !== null && valor !== undefined) {
      parametros.set(clave, String(valor));
    }
  });
  return solicitar(`/api/subusuarios?${parametros.toString()}`);
}

export function obtenerSubusuariosEliminados() {
  return solicitar("/api/subusuarios/historial");
}

export function obtenerIngresos(pagina = 1, limite = 25, filtros = {}) {
  const parametros = new URLSearchParams({
    pagina: String(pagina),
    limite: String(limite),
  });
  Object.entries(filtros).forEach(([clave, valor]) => {
    if (valor !== "" && valor !== null && valor !== undefined) {
      parametros.set(clave, String(valor));
    }
  });
  return solicitar(`/api/ingresos?${parametros.toString()}`);
}

export function obtenerCamarasIngresos() {
  return solicitar("/api/ingresos/camaras");
}

export function obtenerAlertas(limite = 50) {
  return solicitar(`/api/alertas?limite=${encodeURIComponent(limite)}`);
}

export function obtenerUltimosIngresos(limite = 5) {
  return solicitar(`/api/ingresos/ultimos?limite=${encodeURIComponent(limite)}`);
}

export function obtenerHistorialIngresos(idPersona) {
  const parametros = new URLSearchParams({ idPersona: String(idPersona) });
  return solicitar(`/api/ingresos/historial?${parametros.toString()}`);
}

export async function obtenerRostroDeteccion(idDeteccion) {
  const ruta = (
    `/api/ingresos/deteccion-rostro?idDeteccion=${encodeURIComponent(idDeteccion)}`
  );
  let respuesta;
  try {
    respuesta = await fetch(ruta, {
      headers: {
        ...(obtenerToken()
          ? { Authorization: `Bearer ${obtenerToken()}` }
          : {}),
      },
    });
  } catch {
    throw new Error("No se pudo cargar el rostro de la detección.");
  }
  notificarSesionExpirada(ruta, respuesta);
  if (!respuesta.ok) {
    throw new Error("La detección no tiene un rostro disponible.");
  }
  return respuesta.blob();
}

export function agregarPersonaListaObservacion(idPersona, motivo = "") {
  return solicitar("/api/ingresos/lista-observacion", {
    method: "POST",
    body: JSON.stringify({ idPersona, motivo }),
  });
}

export function quitarPersonaListaObservacion(idPersona) {
  return solicitar("/api/ingresos/quitar-lista-observacion", {
    method: "POST",
    body: JSON.stringify({ idPersona }),
  });
}

export async function obtenerRostroPersona(idPersona) {
  const ruta = `/api/ingresos/rostro?idPersona=${encodeURIComponent(idPersona)}`;
  let respuesta;
  try {
    respuesta = await fetch(ruta, {
      headers: {
        ...(obtenerToken()
          ? { Authorization: `Bearer ${obtenerToken()}` }
          : {}),
      },
    });
  } catch {
    throw new Error("No se pudo cargar el rostro de la persona.");
  }
  notificarSesionExpirada(ruta, respuesta);
  if (!respuesta.ok) {
    let mensaje = "La persona no tiene una muestra facial disponible.";
    try {
      const datos = await respuesta.json();
      mensaje = datos.error || mensaje;
    } catch {
      // La imagen es complementaria; basta con mostrar el marcador vacío.
    }
    throw new Error(mensaje);
  }
  return respuesta.blob();
}

export function eliminarPersona(idPersona) {
  return solicitar("/api/ingresos/eliminar-persona", {
    method: "POST",
    body: JSON.stringify({ idPersona }),
  });
}

export function renombrarPersona(idPersona, nombre) {
  return solicitar("/api/ingresos/renombrar-persona", {
    method: "POST",
    body: JSON.stringify({ idPersona, nombre }),
  });
}

export function obtenerListaObservacion(pagina = 1, limite = 25) {
  const parametros = new URLSearchParams({
    pagina: String(pagina),
    limite: String(limite),
  });
  return solicitar(`/api/lista-observacion?${parametros.toString()}`);
}

export function obtenerCamarasConfiguradas() {
  return solicitar("/api/camaras");
}

export function guardarGruposCamara(grupos) {
  return solicitar("/api/grupos-camara/guardar", {
    method: "POST",
    body: JSON.stringify({ grupos }),
  });
}

export function crearCamara(datos) {
  return solicitar("/api/camaras/crear", {
    method: "POST",
    body: JSON.stringify(datos),
  });
}

export function editarCamara(datos) {
  return solicitar("/api/camaras/editar", {
    method: "POST",
    body: JSON.stringify(datos),
  });
}

export function eliminarCamara(id) {
  return solicitar("/api/camaras/eliminar", {
    method: "POST",
    body: JSON.stringify({ id }),
  });
}

export function crearSubusuario(datos) {
  return solicitar("/api/subusuarios", {
    method: "POST",
    body: JSON.stringify(datos),
  });
}

export function actualizarEstadoSubusuario(id, estado) {
  return solicitar("/api/subusuarios/estado", {
    method: "POST",
    body: JSON.stringify({ id, estado }),
  });
}

export function actualizarPermisosSubusuario(id, permisos) {
  return solicitar("/api/subusuarios/editar", {
    method: "POST",
    body: JSON.stringify({ id, permisos }),
  });
}

export function cerrarSesion() {
  return solicitar("/api/auth/logout", { method: "POST" });
}

export function obtenerEstadoMonitoreo() {
  return solicitar("/api/status");
}

export function iniciarTransmision(fuente, analizar = true, idCamara = null) {
  return solicitar("/api/start", {
    method: "POST",
    body: JSON.stringify({
      source: fuente,
      analysis: analizar,
      cameraId: idCamara,
    }),
  });
}

export function detenerTransmision() {
  return solicitar("/api/stop", { method: "POST" });
}
