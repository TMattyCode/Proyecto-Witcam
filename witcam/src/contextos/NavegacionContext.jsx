import { createContext, useContext } from "react";

export const NavegacionContext = createContext(null);

export function useNavegacion() {
  return useContext(NavegacionContext);
}