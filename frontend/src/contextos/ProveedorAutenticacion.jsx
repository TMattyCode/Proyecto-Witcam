import { useEffect, useState } from "react";
import {
  cerrarSesion as solicitarCierreSesion,
  iniciarSesion as solicitarInicioSesion,
  obtenerSesion,
} from "../servicios/api";
import { AutenticacionContext } from "./AutenticacionContext";

const CLAVE_TOKEN = "witcam_token";
const CLAVE_USUARIO = "witcam_usuario";

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

export default function ProveedorAutenticacion({ children }) {
  const [usuario, setUsuario] = useState(null);
  const [cargando, setCargando] = useState(true);

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

  return (
    <AutenticacionContext.Provider
      value={{ usuario, cargando, iniciarSesion, cerrarSesion }}
    >
      {children}
    </AutenticacionContext.Provider>
  );
}
