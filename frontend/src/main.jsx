import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { HashRouter } from "react-router-dom";
import "./index.css";
import App from "./App.jsx";
import ProveedorAutenticacion from "./contextos/ProveedorAutenticacion.jsx";

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <HashRouter>
      <ProveedorAutenticacion>
        <App />
      </ProveedorAutenticacion>
    </HashRouter>
  </StrictMode>,
);
