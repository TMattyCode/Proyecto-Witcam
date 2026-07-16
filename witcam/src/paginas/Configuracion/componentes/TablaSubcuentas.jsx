import "./TablaSubcuentas.css";

const subcuentas = [];

function Permiso({ activo }) {
  return (
    <span className={`permiso ${activo ? "permiso-activo" : "permiso-inactivo"}`}>
      {activo ? "✓" : "×"}
    </span>
  );
}

function TablaSubcuentas() {
  return (
    <section className="configuracion-tarjeta configuracion-subcuentas">
      <div className="subcuentas-encabezado">
        <div className="subcuentas-titulo">
          <div className="configuracion-icono configuracion-icono-subcuentas">
            👥
          </div>

          <div>
            <h2>Subcuentas</h2>
            <p>Administra las subcuentas y sus permisos.</p>
          </div>
        </div>

        <button className="boton-anadir-subcuenta" type="button">
          <span>+</span>
          Añadir subcuenta
        </button>
      </div>

      <div className="subcuentas-tabla-contenedor">
        <table className="subcuentas-tabla">
          <colgroup>
            <col className="col-nombre" />
            <col className="col-usuario" />
            <col className="col-contrasena" />
            <col className="col-correo" />
            <col className="col-permiso" />
            <col className="col-permiso" />
            <col className="col-permiso" />
            <col className="col-permiso" />
            <col className="col-configuracion" />
            <col className="col-acciones" />
          </colgroup>

          <thead>
            <tr>
              <th rowSpan="2">Nombre</th>
              <th rowSpan="2">Usuario</th>
              <th rowSpan="2">Contraseña</th>
              <th rowSpan="2">Correo electrónico</th>

              <th colSpan="5" className="subcuentas-permisos-titulo">
                Permisos
              </th>

              <th rowSpan="2">Acciones</th>
            </tr>

            <tr>
              <th>Ver</th>
              <th>Añadir</th>
              <th>Editar</th>
              <th>Eliminar</th>
              <th>Configuración</th>
            </tr>
          </thead>

          <tbody>
            {subcuentas.length === 0 ? (
              <tr>
                <td colSpan="10" className="subcuentas-vacia">
                  No hay subcuentas registradas.
                </td>
              </tr>
            ) : (
              subcuentas.map((subcuenta) => (
                <tr key={subcuenta.id}>
                  <td>
                    <div className="subcuenta-usuario">
                      <div className="subcuenta-avatar">
                        {subcuenta.nombre.charAt(0)}
                      </div>

                      <span
                        className="subcuenta-texto-recortado"
                        title={subcuenta.nombre}
                      >
                        {subcuenta.nombre}
                      </span>
                    </div>
                  </td>

                  <td>
                    <span
                      className="subcuenta-texto-recortado"
                      title={subcuenta.usuario}
                    >
                      {subcuenta.usuario}
                    </span>
                  </td>

                  <td>**********</td>

                  <td>
                    <span
                      className="subcuenta-texto-recortado"
                      title={subcuenta.correo}
                    >
                      {subcuenta.correo}
                    </span>
                  </td>

                  <td>
                    <Permiso activo={subcuenta.permisos.ver} />
                  </td>

                  <td>
                    <Permiso activo={subcuenta.permisos.anadir} />
                  </td>

                  <td>
                    <Permiso activo={subcuenta.permisos.editar} />
                  </td>

                  <td>
                    <Permiso activo={subcuenta.permisos.eliminar} />
                  </td>

                  <td>
                    <Permiso activo={subcuenta.permisos.configuracion} />
                  </td>

                  <td>
                    <div className="subcuenta-acciones">
                      <button
                        className="boton-accion boton-accion-editar"
                        type="button"
                        aria-label={`Editar a ${subcuenta.nombre}`}
                      >
                        ✎
                      </button>

                      <button
                        className="boton-accion boton-accion-eliminar"
                        type="button"
                        aria-label={`Eliminar a ${subcuenta.nombre}`}
                      >
                        ⌫
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}

export default TablaSubcuentas;