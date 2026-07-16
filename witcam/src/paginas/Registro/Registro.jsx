import "./Registro.css";
import Input from "../../componentes/comunes/Input";
import Button from "../../componentes/comunes/Button";
import { useNavegacion } from "../../contextos/NavegacionContext";

import imagenIzquierda from "../../assets/images/001 witcam inicio imagen.png";

import iconoUsuario from "../../assets/iconos/006 icono-usuario-sinrelleno.png";
import iconoCorreo from "../../assets/iconos/007 icono-correo-sinrelleno.png";
import iconoCandado from "../../assets/iconos/008 icono-candado-sinfondo.png";
import iconoOjo from "../../assets/iconos/008 icono-ojo-sinrelleno.png";
import iconoFlecha from "../../assets/iconos/009 icono-flecha.png";
import iconoUsuarioRegistro from "../../assets/iconos/005 icono-usuario.png";

import whatsapp from "../../assets/logos/003 WhatsApp_icon.png";
import instagram from "../../assets/logos/002 Instagram-Logo.png";

function Registro() {
  const navegacion = useNavegacion();

  const registrarUsuario = (event) => {
    event.preventDefault();
    navegacion?.cambiarPagina("resumen");
  };

  return (
    <main className="register-page">
      <section className="register-container">
        <aside className="left-section">
          <img src={imagenIzquierda} alt="Witcam" className="left-image" />
        </aside>

        <section className="right-section">
          <button
            type="button"
            className="back-link"
            onClick={() => navegacion?.cambiarPagina("inicioSesion")}
          >
            <img src={iconoFlecha} alt="" />
            Volver al inicio de sesión
          </button>

          <div className="register-box">
            <img
              src={iconoUsuarioRegistro}
              alt="Crear usuario"
              className="register-user-icon"
            />

            <h1>Crear una cuenta</h1>
            <p>Completa la información para registrarte</p>

            <form className="register-form" onSubmit={registrarUsuario}>
              <Input
                label="Nombre de usuario"
                placeholder="Ingresa tu nombre de usuario"
                icon={iconoUsuario}
              />

              <Input
                label="Correo electrónico"
                type="email"
                placeholder="Ingresa tu correo electrónico"
                icon={iconoCorreo}
              />

              <Input
                label="Contraseña"
                type="password"
                placeholder="Crea una contraseña"
                icon={iconoCandado}
                rightIcon={iconoOjo}
              />

              <span className="password-help">
                La contraseña debe tener al menos 8 caracteres, incluyendo
                letras y números.
              </span>

              <Button type="submit">Registrarse</Button>
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

export default Registro;