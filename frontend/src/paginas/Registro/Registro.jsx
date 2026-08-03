import "./Registro.css";
import Input from "../../componentes/comunes/Input";
import Button from "../../componentes/comunes/Button";
import { useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { registrarCuenta } from "../../servicios/api";
import { validarRegistro } from "../../utilidades/validacionAutenticacion";

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
  const navigate = useNavigate();
  const [formulario, setFormulario] = useState({
    nombreCuenta: "",
    nombreUsuario: "",
    contrasena: "",
    confirmarContrasena: "",
    correo: "",
    telefono: "",
    nombre: "",
    apellido: "",
  });
  const [error, setError] = useState("");
  const [enviando, setEnviando] = useState(false);
  const envioEnCurso = useRef(false);

  const actualizarCampo = (event) => {
    const { name, value } = event.target;
    setFormulario((actual) => ({ ...actual, [name]: value }));
  };

  const registrarUsuario = async (event) => {
    event.preventDefault();
    if (envioEnCurso.current) return;
    setError("");
    envioEnCurso.current = true;
    setEnviando(true);
    try {
      await registrarCuenta(validarRegistro(formulario));
      sessionStorage.setItem(
        "witcam_mensaje_registro",
        "Cuenta creada correctamente. Ya puedes iniciar sesión.",
      );
      navigate("/inicio-sesion", { replace: true });
    } catch (errorSolicitud) {
      setError(errorSolicitud.message);
    } finally {
      envioEnCurso.current = false;
      setEnviando(false);
    }
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
            onClick={() => navigate("/inicio-sesion")}
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
              <div className="register-grid">
                <Input
                  className="campo-cuenta"
                  label="Nombre de la cuenta"
                  name="nombreCuenta"
                  value={formulario.nombreCuenta}
                  onChange={actualizarCampo}
                  placeholder="Ejemplo: Local Centro"
                  icon={iconoUsuario}
                  autoComplete="organization"
                  maxLength={150}
                  required
                />

                <Input
                  label="Nombre de usuario"
                  name="nombreUsuario"
                  value={formulario.nombreUsuario}
                  onChange={actualizarCampo}
                  placeholder="Ingresa tu nombre de usuario"
                  icon={iconoUsuario}
                  autoComplete="username"
                  maxLength={100}
                  required
                />

                <Input
                  label="Contraseña ⓘ"
                  type="password"
                  name="contrasena"
                  value={formulario.contrasena}
                  onChange={actualizarCampo}
                  placeholder="Crea una contraseña"
                  icon={iconoCandado}
                  rightIcon={iconoOjo}
                  autoComplete="new-password"
                  minLength={8}
                  maxLength={128}
                  required
                />

                <Input
                  label="Confirmar contraseña"
                  type="password"
                  name="confirmarContrasena"
                  value={formulario.confirmarContrasena}
                  onChange={actualizarCampo}
                  placeholder="Repite la contraseña"
                  icon={iconoCandado}
                  rightIcon={iconoOjo}
                  autoComplete="new-password"
                  minLength={8}
                  maxLength={128}
                  required
                />

                <Input
                  label="Correo electrónico"
                  type="email"
                  name="correo"
                  value={formulario.correo}
                  onChange={actualizarCampo}
                  placeholder="Ingresa tu correo electrónico"
                  icon={iconoCorreo}
                  autoComplete="email"
                  maxLength={250}
                  required
                />

                <Input
                  className="campo-telefono"
                  label="Teléfono"
                  type="tel"
                  name="telefono"
                  value={formulario.telefono}
                  onChange={actualizarCampo}
                  placeholder="Ingresa tu teléfono"
                  icon={iconoUsuario}
                  autoComplete="tel"
                  maxLength={20}
                />

                <Input
                  label="Nombre"
                  name="nombre"
                  value={formulario.nombre}
                  onChange={actualizarCampo}
                  placeholder="Ingresa tu nombre"
                  icon={iconoUsuario}
                  autoComplete="given-name"
                  maxLength={100}
                  required
                />

                <Input
                  label="Apellido"
                  name="apellido"
                  value={formulario.apellido}
                  onChange={actualizarCampo}
                  placeholder="Ingresa tu apellido"
                  icon={iconoUsuario}
                  autoComplete="family-name"
                  maxLength={100}
                  required
                />
              </div>

              {error && (
                <div className="mensaje-formulario error" role="alert">
                  {error}
                </div>
              )}

              <Button type="submit" disabled={enviando}>
                {enviando ? "Creando cuenta..." : "Registrarse"}
              </Button>
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
