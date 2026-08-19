import { useEffect, useState } from "react";
import {
  actualizarPerfil as solicitarActualizacionPerfil,
  cerrarSesion as solicitarCierreSesion,
  EVENTO_SESION_EXPIRADA,
  iniciarSesion as solicitarInicioSesion,
  obtenerSesion,
} from "../servicios/api";
import { AutenticacionContext } from "./AutenticacionContext";

const CLAVE_TOKEN = "witcam_token";
const CLAVE_USUARIO = "witcam_usuario";
const CLAVE_MENSAJE_SESION = "witcam_mensaje_sesion";

function limpiarAlmacenamiento() {
  for (const almacenamiento of [localStorage, sessionStorage]) {
    almacenamiento.removeItem(CLAVE_TOKEN);
    almacenamiento.removeItem(CLAVE_USUARIO);
  }
}

function guardarSesion(respuesta, recordar) {
  limpiarAlmacenamiento();
  const almacenamiento = recordar ? localStorage : sessionStorage;
  almacenamiento.setItem(CLAVE_TOKEN, respuesta.token);
  almacenamiento.setItem(CLAVE_USUARIO, JSON.stringify(respuesta.user));
}

function guardarUsuarioActualizado(usuario) {
  const almacenamiento = localStorage.getItem(CLAVE_TOKEN)
    ? localStorage
    : sessionStorage;
  almacenamiento.setItem(CLAVE_USUARIO, JSON.stringify(usuario));
}

export default function ProveedorAutenticacion({ children }) {
  const [usuario, setUsuario] = useState(null);
  const [cargando, setCargando] = useState(true);

  useEffect(() => {
    const manejarSesionExpirada = () => {
      limpiarAlmacenamiento();
      sessionStorage.setItem(
        CLAVE_MENSAJE_SESION,
        "Tu sesión venció. Inicia sesión nuevamente.",
      );
      setUsuario(null);
    };
    window.addEventListener(EVENTO_SESION_EXPIRADA, manejarSesionExpirada);
    return () => {
      window.removeEventListener(EVENTO_SESION_EXPIRADA, manejarSesionExpirada);
    };
  }, []);

  useEffect(() => {
    let activo = true;

    async function restaurarSesion() {
      const token =
        localStorage.getItem(CLAVE_TOKEN) ||
        sessionStorage.getItem(CLAVE_TOKEN);
      if (!token) {
        setCargando(false);
        return;
      }

      try {
        const respuesta = await obtenerSesion();
        if (activo) {
          setUsuario(respuesta.user);
        }
      } catch {
        limpiarAlmacenamiento();
      } finally {
        if (activo) {
          setCargando(false);
        }
      }
    }

    restaurarSesion();
    return () => {
      activo = false;
    };
  }, []);

  const iniciarSesion = async (credenciales, recordar) => {
    const respuesta = await solicitarInicioSesion(credenciales);
    guardarSesion(respuesta, recordar);
    setUsuario(respuesta.user);
    return respuesta.user;
  };

  const cerrarSesion = async () => {
    try {
      await solicitarCierreSesion();
    } catch {
      // La sesion local debe cerrarse aunque el backend no responda.
    } finally {
      limpiarAlmacenamiento();
      setUsuario(null);
    }
  };

  const actualizarPerfil = async (datos) => {
    const respuesta = await solicitarActualizacionPerfil(datos);
    guardarUsuarioActualizado(respuesta.user);
    setUsuario(respuesta.user);
    return respuesta.user;
  };

  return (
    <AutenticacionContext.Provider
      value={{
        usuario,
        cargando,
        iniciarSesion,
        cerrarSesion,
        actualizarPerfil,
      }}
    >
      {children}
    </AutenticacionContext.Provider>
  );
}
