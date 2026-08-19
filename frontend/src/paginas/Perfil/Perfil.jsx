import { useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

import Layout from "../../componentes/layout/Layout";
import Input from "../../componentes/comunes/Input";
import { useAutenticacion } from "../../contextos/AutenticacionContext";
import { validarPerfil } from "../../utilidades/validacionAutenticacion";
import iconoUsuario from "../../assets/iconos/006 icono-usuario-sinrelleno.png";
import iconoCorreo from "../../assets/iconos/007 icono-correo-sinrelleno.png";
import iconoCandado from "../../assets/iconos/008 icono-candado-sinfondo.png";
import iconoOjo from "../../assets/iconos/008 icono-ojo-sinrelleno.png";
import logoUsuario from "../../assets/logos/021 logo-usuario-default.png";
import "./Perfil.css";

function crearFormulario(usuario) {
  return {
    nombreCuenta: usuario?.nombreCuenta || "",
    nombre: usuario?.nombre || "",
    apellido: usuario?.apellido || "",
    nombreUsuario: usuario?.nombreUsuario || "",
    correo: usuario?.correo || "",
    telefono: usuario?.telefono || "",
    contrasenaActual: "",
    contrasenaNueva: "",
    confirmarContrasena: "",
  };
}

export default function Perfil() {
  const { usuario, actualizarPerfil } = useAutenticacion();
  const navegar = useNavigate();
  const esAdministrador = usuario?.rol === "Administrador";
  const [formulario, setFormulario] = useState(() => crearFormulario(usuario));
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState("");
  const [mensaje, setMensaje] = useState("");
  const envioEnCurso = useRef(false);

  const actualizarCampo = (evento) => {
    const { name, value } = evento.target;
    setFormulario((actual) => ({ ...actual, [name]: value }));
    setError("");
    setMensaje("");
  };

  const restaurar = () => {
    setFormulario(crearFormulario(usuario));
    setError("");
    setMensaje("");
  };

  const volver = () => {
    if ((window.history.state?.idx ?? 0) > 0) {
      navegar(-1);
      return;
    }
    navegar("/resumen");
  };

  const guardar = async (evento) => {
    evento.preventDefault();
    if (envioEnCurso.current) return;
    envioEnCurso.current = true;
    setGuardando(true);
    setError("");
    setMensaje("");
    try {
      const datos = validarPerfil(formulario, esAdministrador);
      const actualizado = await actualizarPerfil(datos);
      setFormulario(crearFormulario(actualizado));
      setMensaje("Tu perfil se actualizó correctamente.");
    } catch (errorSolicitud) {
      setError(errorSolicitud.message);
    } finally {
      envioEnCurso.current = false;
      setGuardando(false);
    }
  };

  return (
    <Layout
      titulo="Mi perfil"
      subtitulo="Administra tus datos personales y la seguridad de tu cuenta."
      compacto
    >
      <main className="perfil-contenido">
        <button type="button" className="perfil-volver" onClick={volver}>
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d="M15 18l-6-6 6-6" />
          </svg>
          Volver
        </button>
        <section className="perfil-presentacion">
          <div className="perfil-identidad">
            <img src={logoUsuario} alt="" />
            <div>
              <span>Perfil de usuario</span>
              <h2>{usuario?.nombreUsuario}</h2>
              <p>{usuario?.correo}</p>
            </div>
          </div>
          <dl>
            <div>
              <dt>Cuenta</dt>
              <dd>{usuario?.nombreCuenta}</dd>
            </div>
            <div>
              <dt>Tipo de usuario</dt>
              <dd>{usuario?.rol}</dd>
            </div>
          </dl>
        </section>

        <form className="perfil-formulario" onSubmit={guardar}>
          {esAdministrador && (
            <section className="perfil-seccion perfil-empresa">
              <header>
                <span>01</span>
                <div>
                  <h2>Empresa</h2>
                  <p>
                    Este nombre identifica la cuenta para todos sus usuarios.
                  </p>
                </div>
              </header>
              <Input
                label="Nombre de la empresa o negocio"
                name="nombreCuenta"
                value={formulario.nombreCuenta}
                onChange={actualizarCampo}
                icon={iconoUsuario}
                maxLength={150}
                required
              />
            </section>
          )}

          <section className="perfil-seccion">
            <header>
              <span>{esAdministrador ? "02" : "01"}</span>
              <div>
                <h2>Información personal</h2>
                <p>Estos datos identifican tu usuario dentro de Witcam.</p>
              </div>
            </header>
            <div className="perfil-grid">
              <Input
                label="Nombre"
                name="nombre"
                value={formulario.nombre}
                onChange={actualizarCampo}
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
                icon={iconoUsuario}
                autoComplete="family-name"
                maxLength={100}
                required
              />
              <Input
                label="Nombre de usuario"
                name="nombreUsuario"
                value={formulario.nombreUsuario}
                onChange={actualizarCampo}
                icon={iconoUsuario}
                autoComplete="username"
                maxLength={100}
                required
              />
              <Input
                label="Correo electrónico"
                type="email"
                name="correo"
                value={formulario.correo}
                onChange={actualizarCampo}
                icon={iconoCorreo}
                autoComplete="email"
                maxLength={250}
                required
              />
              <Input
                className="perfil-campo-ancho"
                label="Teléfono (opcional)"
                type="tel"
                name="telefono"
                value={formulario.telefono}
                onChange={actualizarCampo}
                icon={iconoUsuario}
                autoComplete="tel"
                maxLength={20}
              />
            </div>
          </section>

          <section className="perfil-seccion perfil-seguridad">
            <header>
              <span>{esAdministrador ? "03" : "02"}</span>
              <div>
                <h2>Seguridad</h2>
                <p>Déjalo en blanco si no deseas cambiar tu contraseña.</p>
              </div>
            </header>
            <div className="perfil-grid perfil-grid-seguridad">
              <Input
                label="Contraseña actual"
                type="password"
                name="contrasenaActual"
                value={formulario.contrasenaActual}
                onChange={actualizarCampo}
                icon={iconoCandado}
                rightIcon={iconoOjo}
                autoComplete="current-password"
                maxLength={128}
              />
              <Input
                label="Nueva contraseña"
                type="password"
                name="contrasenaNueva"
                value={formulario.contrasenaNueva}
                onChange={actualizarCampo}
                icon={iconoCandado}
                rightIcon={iconoOjo}
                autoComplete="new-password"
                minLength={8}
                maxLength={128}
              />
              <Input
                label="Confirmar nueva contraseña"
                type="password"
                name="confirmarContrasena"
                value={formulario.confirmarContrasena}
                onChange={actualizarCampo}
                icon={iconoCandado}
                rightIcon={iconoOjo}
                autoComplete="new-password"
                minLength={8}
                maxLength={128}
              />
            </div>
          </section>

          {(error || mensaje) && (
            <p
              className={`perfil-resultado${error ? " error" : " exito"}`}
              role={error ? "alert" : "status"}
            >
              {error || mensaje}
            </p>
          )}

          <footer className="perfil-acciones">
            <button type="button" onClick={restaurar} disabled={guardando}>
              Descartar cambios
            </button>
            <button type="submit" disabled={guardando}>
              {guardando ? "Guardando..." : "Guardar perfil"}
            </button>
          </footer>
        </form>
      </main>
    </Layout>
  );
}
