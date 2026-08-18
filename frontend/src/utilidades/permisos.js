export const PERMISOS = Object.freeze({
  VER_RESUMEN: "ver_resumen",
  VER_CAMARAS: "ver_camaras",
  CONTROLAR_CAMARAS: "controlar_camaras",
  VER_INGRESOS: "ver_ingresos",
  GESTIONAR_IDENTIDADES: "gestionar_identidades",
  ELIMINAR_IDENTIDADES: "eliminar_identidades",
  VER_OBSERVACION: "ver_observacion",
  GESTIONAR_OBSERVACION: "gestionar_observacion",
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
