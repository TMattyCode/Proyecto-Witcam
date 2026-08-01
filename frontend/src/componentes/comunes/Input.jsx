import { useState } from "react";


function Input({
  label,
  type = "text",
  placeholder,
  icon,
  rightIcon,
  className = "",
  ...inputProps
}) {
  const id = inputProps.id || inputProps.name;
  const permiteMostrar = type === "password" && Boolean(rightIcon);
  const [contrasenaVisible, setContrasenaVisible] = useState(false);
  const tipoActual =
    permiteMostrar && contrasenaVisible ? "text" : type;

  return (
    <div className={`input-group ${className}`.trim()}>
      <label htmlFor={id}>{label}</label>

      <div className="input-wrapper">
        <img src={icon} alt="" className="input-icon" />

        <input
          id={id}
          type={tipoActual}
          placeholder={placeholder}
          {...inputProps}
        />

        {permiteMostrar && (
          <button
            type="button"
            className={`input-visibility${
              contrasenaVisible ? " password-visible" : ""
            }`}
            onClick={() => setContrasenaVisible((visible) => !visible)}
            aria-label={
              contrasenaVisible
                ? "Ocultar contraseña"
                : "Mostrar contraseña"
            }
            aria-pressed={contrasenaVisible}
            title={
              contrasenaVisible
                ? "Ocultar contraseña"
                : "Mostrar contraseña"
            }
          >
            <img src={rightIcon} alt="" className="input-icon right" />
          </button>
        )}
      </div>
    </div>
  );
}

export default Input;
