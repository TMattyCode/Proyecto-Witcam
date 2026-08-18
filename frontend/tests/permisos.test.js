import test from "node:test";
import assert from "node:assert/strict";

import { PERMISOS, tienePermiso } from "../src/utilidades/permisos.js";

test("el administrador conserva todos los permisos", () => {
  assert.equal(
    tienePermiso(
      { rol: "Administrador", permisos: [] },
      PERMISOS.ELIMINAR_IDENTIDADES,
    ),
    true,
  );
});

test("el subusuario solo recibe los permisos asignados", () => {
  const usuario = {
    rol: "Subusuario",
    permisos: ["ver_ingresos", "gestionar_identidades"],
  };
  assert.equal(tienePermiso(usuario, PERMISOS.VER_INGRESOS), true);
  assert.equal(tienePermiso(usuario, PERMISOS.GESTIONAR_IDENTIDADES), true);
  assert.equal(tienePermiso(usuario, PERMISOS.ELIMINAR_IDENTIDADES), false);
});

test("una sesion ausente no recibe permisos", () => {
  assert.equal(tienePermiso(null, PERMISOS.VER_RESUMEN), false);
});
