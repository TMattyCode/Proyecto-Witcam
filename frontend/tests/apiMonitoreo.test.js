import test from "node:test";
import assert from "node:assert/strict";

import {
  actualizarPermisosSubusuario,
  iniciarTransmision,
  obtenerResumenCuenta,
} from "../src/servicios/api.js";

test("la webcam inicia con el analisis de IA habilitado", async () => {
  const fetchAnterior = globalThis.fetch;
  const localStorageAnterior = globalThis.localStorage;
  const sessionStorageAnterior = globalThis.sessionStorage;
  let solicitud;
  const almacenamientoVacio = { getItem: () => null };
  globalThis.localStorage = almacenamientoVacio;
  globalThis.sessionStorage = almacenamientoVacio;
  globalThis.fetch = async (ruta, opciones) => {
    solicitud = { ruta, opciones };
    return {
      ok: true,
      headers: { get: () => "application/json" },
      json: async () => ({ ok: true }),
    };
  };

  try {
    await iniciarTransmision(0, true, 17);
  } finally {
    globalThis.fetch = fetchAnterior;
    globalThis.localStorage = localStorageAnterior;
    globalThis.sessionStorage = sessionStorageAnterior;
  }

  assert.equal(solicitud.ruta, "/api/start");
  assert.equal(solicitud.opciones.method, "POST");
  assert.deepEqual(JSON.parse(solicitud.opciones.body), {
    source: 0,
    analysis: true,
    cameraId: 17,
  });
});

test("la administracion solo envia el ID y los permisos del subusuario", async () => {
  const fetchAnterior = globalThis.fetch;
  const localStorageAnterior = globalThis.localStorage;
  const sessionStorageAnterior = globalThis.sessionStorage;
  let solicitud;
  const almacenamientoVacio = { getItem: () => null };
  globalThis.localStorage = almacenamientoVacio;
  globalThis.sessionStorage = almacenamientoVacio;
  globalThis.fetch = async (ruta, opciones) => {
    solicitud = { ruta, opciones };
    return {
      ok: true,
      headers: { get: () => "application/json" },
      json: async () => ({ ok: true }),
    };
  };

  try {
    await actualizarPermisosSubusuario(8, ["ver", "configuracion"]);
  } finally {
    globalThis.fetch = fetchAnterior;
    globalThis.localStorage = localStorageAnterior;
    globalThis.sessionStorage = sessionStorageAnterior;
  }

  assert.equal(solicitud.ruta, "/api/subusuarios/editar");
  assert.deepEqual(JSON.parse(solicitud.opciones.body), {
    id: 8,
    permisos: ["ver", "configuracion"],
  });
});

test("traduce una caida de red a un mensaje comprensible", async () => {
  const fetchAnterior = globalThis.fetch;
  const localStorageAnterior = globalThis.localStorage;
  const sessionStorageAnterior = globalThis.sessionStorage;
  const almacenamientoVacio = { getItem: () => null };
  globalThis.localStorage = almacenamientoVacio;
  globalThis.sessionStorage = almacenamientoVacio;
  globalThis.fetch = async () => {
    throw new TypeError("Failed to fetch");
  };

  try {
    await assert.rejects(
      obtenerResumenCuenta(),
      /No se pudo conectar con Witcam/,
    );
  } finally {
    globalThis.fetch = fetchAnterior;
    globalThis.localStorage = localStorageAnterior;
    globalThis.sessionStorage = sessionStorageAnterior;
  }
});

test("una consulta GET se recupera de un fallo transitorio", async () => {
  const fetchAnterior = globalThis.fetch;
  const localStorageAnterior = globalThis.localStorage;
  const sessionStorageAnterior = globalThis.sessionStorage;
  const almacenamientoVacio = { getItem: () => null };
  let intentos = 0;
  globalThis.localStorage = almacenamientoVacio;
  globalThis.sessionStorage = almacenamientoVacio;
  globalThis.fetch = async () => {
    intentos += 1;
    if (intentos === 1) throw new TypeError("Failed to fetch");
    return {
      ok: true,
      headers: { get: () => "application/json" },
      json: async () => ({ nombreCuenta: "Witcam" }),
    };
  };

  try {
    const respuesta = await obtenerResumenCuenta();
    assert.equal(respuesta.nombreCuenta, "Witcam");
    assert.equal(intentos, 2);
  } finally {
    globalThis.fetch = fetchAnterior;
    globalThis.localStorage = localStorageAnterior;
    globalThis.sessionStorage = sessionStorageAnterior;
  }
});

test("una escritura POST no se repite despues de un fallo", async () => {
  const fetchAnterior = globalThis.fetch;
  const localStorageAnterior = globalThis.localStorage;
  const sessionStorageAnterior = globalThis.sessionStorage;
  const almacenamientoVacio = { getItem: () => null };
  let intentos = 0;
  globalThis.localStorage = almacenamientoVacio;
  globalThis.sessionStorage = almacenamientoVacio;
  globalThis.fetch = async () => {
    intentos += 1;
    throw new TypeError("Failed to fetch");
  };

  try {
    await assert.rejects(
      actualizarPermisosSubusuario(8, ["gestionar_identidades"]),
      /No se pudo conectar con Witcam/,
    );
    assert.equal(intentos, 1);
  } finally {
    globalThis.fetch = fetchAnterior;
    globalThis.localStorage = localStorageAnterior;
    globalThis.sessionStorage = sessionStorageAnterior;
  }
});

test("traduce una respuesta JSON incompleta", async () => {
  const fetchAnterior = globalThis.fetch;
  const localStorageAnterior = globalThis.localStorage;
  const sessionStorageAnterior = globalThis.sessionStorage;
  const almacenamientoVacio = { getItem: () => null };
  globalThis.localStorage = almacenamientoVacio;
  globalThis.sessionStorage = almacenamientoVacio;
  globalThis.fetch = async () => ({
    ok: false,
    status: 500,
    headers: { get: () => "application/json" },
    json: async () => {
      throw new SyntaxError("Unexpected end of JSON input");
    },
  });

  try {
    await assert.rejects(
      obtenerResumenCuenta(),
      /respuesta incompleta/,
    );
  } finally {
    globalThis.fetch = fetchAnterior;
    globalThis.localStorage = localStorageAnterior;
    globalThis.sessionStorage = sessionStorageAnterior;
  }
});

test("notifica globalmente cuando vence una sesion", async () => {
  const fetchAnterior = globalThis.fetch;
  const dispatchAnterior = globalThis.dispatchEvent;
  const localStorageAnterior = globalThis.localStorage;
  const sessionStorageAnterior = globalThis.sessionStorage;
  const almacenamiento = { getItem: () => "token-vencido" };
  let evento;
  globalThis.localStorage = almacenamiento;
  globalThis.sessionStorage = almacenamiento;
  globalThis.dispatchEvent = (recibido) => {
    evento = recibido;
    return true;
  };
  globalThis.fetch = async () => ({
    ok: false,
    status: 401,
    headers: { get: () => "application/json" },
    json: async () => ({ error: "La sesion no es valida" }),
  });

  try {
    await assert.rejects(obtenerResumenCuenta(), /sesion no es valida/);
  } finally {
    globalThis.fetch = fetchAnterior;
    globalThis.dispatchEvent = dispatchAnterior;
    globalThis.localStorage = localStorageAnterior;
    globalThis.sessionStorage = sessionStorageAnterior;
  }

  assert.equal(evento.type, "witcam:sesion-expirada");
});
