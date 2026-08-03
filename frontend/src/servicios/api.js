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
