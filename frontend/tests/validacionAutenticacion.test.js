import test from "node:test";
import assert from "node:assert/strict";

import {
  validarInicioSesion,
  validarEdicionSubusuario,
  validarRegistro,
  validarSubusuario,
} from "../src/utilidades/validacionAutenticacion.js";

const registroValido = {
  nombreCuenta: " Cuenta Centro ",
  nombreUsuario: "matias",
  contrasena: "segura123",
  confirmarContrasena: "segura123",
  correo: " MATIAS@example.com ",
  telefono: "+56 9 1234 5678",
  nombre: "Matias",
  apellido: "Prueba",
};

test("normaliza un registro válido sin modificar su contraseña", () => {
  const resultado = validarRegistro(registroValido);
  assert.equal(resultado.nombreCuenta, "Cuenta Centro");
  assert.equal(resultado.correo, "matias@example.com");
  assert.equal(resultado.contrasena, "segura123");
});

test("rechaza contraseñas distintas", () => {
  assert.throws(
    () => validarRegistro({ ...registroValido, confirmarContrasena: "otra1234" }),
    /no coinciden/,
  );
});

test("rechaza valores nulos y datos con formato inválido", () => {
  assert.throws(() => validarRegistro({ ...registroValido, nombre: null }));
  assert.throws(() => validarRegistro({ ...registroValido, correo: "invalido" }));
  assert.throws(
    () => validarRegistro({ ...registroValido, nombreUsuario: "dos palabras" }),
  );
});

test("el inicio de sesión exige ambas credenciales", () => {
  assert.throws(
    () => validarInicioSesion({ nombreUsuario: "", contrasena: "" }),
    /Ingresa usuario y contraseña/,
  );
  assert.deepEqual(
    validarInicioSesion({ nombreUsuario: " matias ", contrasena: "segura123" }),
    { nombreUsuario: "matias", contrasena: "segura123" },
  );
});

test("valida subusuarios y elimina permisos duplicados", () => {
  const resultado = validarSubusuario({
    ...registroValido,
    permisos: ["ver", "ver", "editar"],
  });
  assert.equal("nombreCuenta" in resultado, false);
  assert.deepEqual(resultado.permisos, ["ver", "editar"]);
});

test("la edición permite conservar la contraseña o cambiarla con confirmación", () => {
  const sinCambio = validarEdicionSubusuario({
    ...registroValido,
    id: 2,
    contrasena: "",
    confirmarContrasena: "",
    permisos: ["ver"],
  });
  assert.equal(sinCambio.contrasena, "");
  assert.throws(
    () => validarEdicionSubusuario({
      ...registroValido,
      id: 2,
      confirmarContrasena: "otra1234",
      permisos: [],
    }),
    /no coinciden/,
  );
});
