import "./Inicio_sesion.css";
import Input from "../../componentes/comunes/Input";
import Button from "../../componentes/comunes/Button";
import { useNavigate } from "react-router-dom";
import { useAutenticacion } from "../../contextos/AutenticacionContext";
import { useRef, useState } from "react";
import { validarInicioSesion } from "../../utilidades/validacionAutenticacion";

import imagenIzquierda from "../../assets/images/001 witcam inicio imagen.png";

import iconoUsuario from "../../assets/iconos/006 icono-usuario-sinrelleno.png";
import iconoCandado from "../../assets/iconos/008 icono-candado-sinfondo.png";
import iconoOjo from "../../assets/iconos/008 icono-ojo-sinrelleno.png";

import whatsapp from "../../assets/logos/003 WhatsApp_icon.png";
import instagram from "../../assets/logos/002 Instagram-Logo.png";

function InicioSesion() {
  const navigate = useNavigate();
  const autenticacion = useAutenticacion();
  const [formulario, setFormulario] = useState({
    nombreUsuario: "",
    contrasena: "",
  });
  const [recordarme, setRecordarme] = useState(false);
  const [error, setError] = useState("");
  const [enviando, setEnviando] = useState(false);
  const envioEnCurso = useRef(false);
  const [mensajeRegistro] = useState(() => {
    const mensaje = sessionStorage.getItem("witcam_mensaje_registro") || "";
    sessionStorage.removeItem("witcam_mensaje_registro");
    return mensaje;
  });

  const actualizarCampo = (event) => {
    const { name, value } = event.target;
    setFormulario((actual) => ({ ...actual, [name]: value }));
  };

  const iniciarSesion = async (event) => {
    event.preventDefault();
    if (envioEnCurso.current) return;
    setError("");
    envioEnCurso.current = true;
    setEnviando(true);
    try {
      await autenticacion.iniciarSesion(
        validarInicioSesion(formulario),
        recordarme,
      );
      navigate("/resumen", { replace: true });
    } catch (errorSolicitud) {
      setError(errorSolicitud.message);
    } finally {
      envioEnCurso.current = false;
      setEnviando(false);
    }
  };

  return (
    <main className="login-page">
      <section className="login-container">
        <aside className="left-section">
          <img src={imagenIzquierda} alt="Witcam" className="left-image" />
        </aside>

        <section className="login-right-section">
          <div className="login-box">
            <h1>¡Bienvenido de vuelta!</h1>
            <p>Inicia sesión para acceder a tu cuenta</p>

            <form className="login-form" onSubmit={iniciarSesion}>
              <Input
                label="Usuario"
                name="nombreUsuario"
                value={formulario.nombreUsuario}
                onChange={actualizarCampo}
                placeholder="Ingresa tu usuario"
                icon={iconoUsuario}
                autoComplete="username"
                maxLength={100}
                required
              />

              <Input
                label="Contraseña"
                type="password"
                name="contrasena"
                value={formulario.contrasena}
                onChange={actualizarCampo}
                placeholder="Ingresa tu contraseña"
                icon={iconoCandado}
                rightIcon={iconoOjo}
                autoComplete="current-password"
                maxLength={128}
                required
              />

              <div className="login-options">
                <label className="remember-option">
                  <input
                    type="checkbox"
                    checked={recordarme}
                    onChange={(event) => setRecordarme(event.target.checked)}
                  />
                  <span>Recordarme</span>
                </label>

                <a href="#">¿Olvidaste tu contraseña?</a>
              </div>

              {mensajeRegistro && (
                <div className="mensaje-formulario exito">{mensajeRegistro}</div>
              )}
              {error && (
                <div className="mensaje-formulario error" role="alert">
                  {error}
                </div>
              )}

              <Button type="submit" disabled={enviando}>
                {enviando ? "Ingresando..." : "Iniciar sesión"}
              </Button>

              <button
                type="button"
                className="secondary-button"
                onClick={() => navigate("/registro")}
              >
                Registrarse
              </button>
            </form>
          </div>

          <div className="contact-area">
            <span className="contact-text">
              ¿Necesitas ayuda? Contáctanos
            </span>

            <img src={whatsapp} alt="WhatsApp" />

            <img
              src={instagram}
              alt="Instagram"
              className="instagram-icon"
            />
          </div>
        </section>
      </section>
    </main>
  );
}

export default InicioSesion;
