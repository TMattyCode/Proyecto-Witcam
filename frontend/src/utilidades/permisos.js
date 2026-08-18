export const PERMISOS = Object.freeze({
  VER: "ver",
  ANADIR: "anadir",
  EDITAR: "editar",
  ELIMINAR: "eliminar",
  CONFIGURACION: "configuracion",
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
