import test from "node:test";
import assert from "node:assert/strict";

import { PERMISOS, tienePermiso } from "../src/utilidades/permisos.js";

test("el administrador conserva todos los permisos", () => {
  assert.equal(
    tienePermiso({ rol: "Administrador", permisos: [] }, PERMISOS.ELIMINAR),
    true,
  );
});

test("el subusuario solo recibe los permisos asignados", () => {
  const usuario = { rol: "Subusuario", permisos: ["ver", "editar"] };
  assert.equal(tienePermiso(usuario, PERMISOS.VER), true);
  assert.equal(tienePermiso(usuario, PERMISOS.EDITAR), true);
  assert.equal(tienePermiso(usuario, PERMISOS.ELIMINAR), false);
});

test("una sesion ausente no recibe permisos", () => {
  assert.equal(tienePermiso(null, PERMISOS.VER), false);
});
