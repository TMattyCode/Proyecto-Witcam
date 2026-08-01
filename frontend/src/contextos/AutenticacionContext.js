import { createContext, useContext } from "react";

export const AutenticacionContext = createContext(null);

export function useAutenticacion() {
  const contexto = useContext(AutenticacionContext);
  if (contexto === null) {
    throw new Error(
      "useAutenticacion debe usarse dentro de ProveedorAutenticacion",
    );
  }
  return contexto;
}
