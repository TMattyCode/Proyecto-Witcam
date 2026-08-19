export const PERMISOS = Object.freeze({
  GESTIONAR_CAMARAS: "gestionar_camaras",
  GESTIONAR_IDENTIDADES: "gestionar_identidades",
  ELIMINAR_IDENTIDADES: "eliminar_identidades",
});

export function tienePermiso(usuario, codigo) {
  return Boolean(
    usuario
    && (
      usuario.rol === "Administrador"
      || usuario.permisos?.includes(codigo)
    ),
  );
}
