import test from "node:test";
import assert from "node:assert/strict";

import {
  validarInicioSesion,
  validarPerfil,
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

test("el perfil permite conservar la contrasena actual", () => {
  const resultado = validarPerfil({
    nombre: " Matias ",
    apellido: "Prueba",
    nombreUsuario: "matias.nuevo",
    correo: " NUEVO@example.com ",
    telefono: "",
    contrasenaActual: "",
    contrasenaNueva: "",
    confirmarContrasena: "",
  });
  assert.equal(resultado.nombre, "Matias");
  assert.equal(resultado.correo, "nuevo@example.com");
});

test("el perfil del administrador exige el nombre de la empresa", () => {
  const perfil = {
    nombreCuenta: "Witcam SpA",
    nombre: "Matias",
    apellido: "Prueba",
    nombreUsuario: "matias",
    correo: "matias@example.com",
    telefono: "",
    contrasenaActual: "",
    contrasenaNueva: "",
    confirmarContrasena: "",
  };
  assert.equal(validarPerfil(perfil, true).nombreCuenta, "Witcam SpA");
  assert.throws(
    () => validarPerfil({ ...perfil, nombreCuenta: "" }, true),
    /campos obligatorios/,
  );
});

test("el cambio de contrasena exige los tres campos", () => {
  const perfil = {
    nombre: "Matias",
    apellido: "Prueba",
    nombreUsuario: "matias",
    correo: "matias@example.com",
    telefono: "",
    contrasenaActual: "segura123",
    contrasenaNueva: "nuevaSegura123",
    confirmarContrasena: "",
  };
  assert.throws(() => validarPerfil(perfil), /tres campos/);
  assert.throws(
    () => validarPerfil({ ...perfil, confirmarContrasena: "distinta123" }),
    /no coinciden/,
  );
});
