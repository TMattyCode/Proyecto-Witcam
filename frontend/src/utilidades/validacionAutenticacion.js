const PATRON_CORREO = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const PATRON_USUARIO = /^[\p{L}\p{N}_.-]+$/u;
const PATRON_TELEFONO = /^[+\d\s().-]+$/;

function texto(valor, campo, maximo, recortar = true) {
  if (typeof valor !== "string") {
    throw new Error(`El campo ${campo} no es válido`);
  }
  const resultado = recortar ? valor.trim() : valor;
  if (resultado.length > maximo) {
    throw new Error(`El campo ${campo} supera el largo permitido`);
  }
  return resultado;
}

export function validarRegistro(datos) {
  const normalizados = {
    nombreCuenta: texto(datos.nombreCuenta, "nombre de la cuenta", 150),
    nombreUsuario: texto(datos.nombreUsuario, "nombre de usuario", 100),
    contrasena: texto(datos.contrasena, "contraseña", 128, false),
    confirmarContrasena: texto(
      datos.confirmarContrasena,
      "confirmación de contraseña",
      128,
      false,
    ),
    correo: texto(datos.correo, "correo", 250).toLowerCase(),
    telefono: texto(datos.telefono, "teléfono", 20),
    nombre: texto(datos.nombre, "nombre", 100),
    apellido: texto(datos.apellido, "apellido", 100),
  };
  const obligatorios = [
    normalizados.nombreCuenta,
    normalizados.nombreUsuario,
    normalizados.contrasena,
    normalizados.correo,
    normalizados.nombre,
    normalizados.apellido,
  ];
  if (obligatorios.some((valor) => !valor)) {
    throw new Error("Completa todos los campos obligatorios");
  }
  if (normalizados.contrasena.length < 8) {
    throw new Error("La contraseña debe tener al menos 8 caracteres");
  }
  if (normalizados.contrasena !== normalizados.confirmarContrasena) {
    throw new Error("Las contraseñas no coinciden");
  }
  if (!PATRON_USUARIO.test(normalizados.nombreUsuario)) {
    throw new Error(
      "El usuario solo puede contener letras, números, punto, guion y guion bajo",
    );
  }
  if (!PATRON_CORREO.test(normalizados.correo)) {
    throw new Error("El correo electrónico no es válido");
  }
  if (normalizados.telefono && !PATRON_TELEFONO.test(normalizados.telefono)) {
    throw new Error("El teléfono no es válido");
  }
  return normalizados;
}

export function validarInicioSesion(datos) {
  const nombreUsuario = texto(datos.nombreUsuario, "nombre de usuario", 100);
  const contrasena = texto(datos.contrasena, "contraseña", 128, false);
  if (!nombreUsuario || !contrasena) {
    throw new Error("Ingresa usuario y contraseña");
  }
  return { nombreUsuario, contrasena };
}
