async function solicitar(ruta, opciones = {}) {
  const token =
    localStorage.getItem("witcam_token") ||
    sessionStorage.getItem("witcam_token");
  const respuesta = await fetch(ruta, {
    ...opciones,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...opciones.headers,
    },
  });
  const tipoContenido = respuesta.headers.get("content-type") || "";
  if (!tipoContenido.includes("application/json")) {
    throw new Error(
      "El backend no devolvió una respuesta válida. Reinicia el servidor de Python.",
    );
  }
  const datos = await respuesta.json();
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

export function editarSubusuario(datos) {
  return solicitar("/api/subusuarios/editar", {
    method: "POST",
    body: JSON.stringify(datos),
  });
}

export function cerrarSesion() {
  return solicitar("/api/auth/logout", { method: "POST" });
}

export function obtenerEstadoMonitoreo() {
  return solicitar("/api/status");
}

export function iniciarTransmision(fuente) {
  return solicitar("/api/start", {
    method: "POST",
    body: JSON.stringify({ source: fuente, analysis: false }),
  });
}

export function detenerTransmision() {
  return solicitar("/api/stop", { method: "POST" });
}
