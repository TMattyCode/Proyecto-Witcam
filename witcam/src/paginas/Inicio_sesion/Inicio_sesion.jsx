import { useState } from "react";
import "./Inicio_sesion.css";

import Input from "../../componentes/comunes/Input";
import Button from "../../componentes/comunes/Button";
import { useNavegacion } from "../../contextos/NavegacionContext";

import imagenIzquierda from "../../assets/images/001 witcam inicio imagen.png";

import iconoUsuario from "../../assets/iconos/006 icono-usuario-sinrelleno.png";
import iconoCandado from "../../assets/iconos/008 icono-candado-sinfondo.png";
import iconoOjo from "../../assets/iconos/008 icono-ojo-sinrelleno.png";

import whatsapp from "../../assets/logos/003 WhatsApp_icon.png";
import instagram from "../../assets/logos/002 Instagram-Logo.png";

function InicioSesion() {
  const navegacion = useNavegacion();

  // Controla si la contraseña se muestra o se oculta
  const [mostrarContrasena, setMostrarContrasena] = useState(false);

  const iniciarSesion = (event) => {
    event.preventDefault();
    navegacion?.cambiarPagina("resumen");
  };

  return (
    <main className="login-page">
      <section className="login-container">

        {/* LADO IZQUIERDO */}
        <aside className="left-section">
          <img
            src={imagenIzquierda}
            alt="Witcam"
            className="left-image"
          />
        </aside>

        {/* LADO DERECHO */}
        <section className="login-right-section">

          <div className="login-box">
            <h1>¡Bienvenido de vuelta!</h1>
            <p>Inicia sesión para acceder a tu cuenta</p>

            <form
              className="login-form"
              onSubmit={iniciarSesion}
            >

              {/* USUARIO */}
              <Input
                label="Usuario"
                placeholder="Ingresa tu usuario"
                icon={iconoUsuario}
              />

              {/* CONTRASEÑA */}
              <Input
                label="Contraseña"
                type={mostrarContrasena ? "text" : "password"}
                placeholder="Ingresa tu contraseña"
                icon={iconoCandado}
                rightIcon={iconoOjo}
                onRightIconClick={() =>
                  setMostrarContrasena(!mostrarContrasena)
                }
              />

              {/* OPCIONES */}
              <div className="login-options">

                <label className="remember-option">
                  <input type="checkbox" />
                  <span>Recordarme</span>
                </label>

                <a href="#">
                  ¿Olvidaste tu contraseña?
                </a>

              </div>

              {/* INICIAR SESIÓN */}
              <Button type="submit">
                Iniciar sesión
              </Button>

              {/* REGISTRO */}
              <button
                type="button"
                className="secondary-button"
                onClick={() =>
                  navegacion?.cambiarPagina("registro")
                }
              >
                Registrarse
              </button>

            </form>
          </div>

          {/* CONTACTO */}
          <div className="contact-area">

            <span className="contact-text">
              ¿Necesitas ayuda? Contáctanos
            </span>

            <img
              src={whatsapp}
              alt="WhatsApp"
            />

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