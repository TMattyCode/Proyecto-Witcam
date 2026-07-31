function Input({
  label,
  type = "text",
  placeholder,
  icon,
  rightIcon,
  onRightIconClick,
  labelIcon,
  labelTooltip,
}) {
  return (
    <div className="input-group">

      <div className="input-label-row">
        <label>{label}</label>

        {labelIcon && (
          <span className="input-help">
            <img
              src={labelIcon}
              alt="Información"
              className="input-help-icon"
            />

            {labelTooltip && (
              <span className="input-tooltip">
                {labelTooltip}
              </span>
            )}
          </span>
        )}
      </div>

      <div className="input-wrapper">

        <img
          src={icon}
          alt=""
          className="input-icon"
        />

        <input
          type={type}
          placeholder={placeholder}
        />

        {rightIcon && (
          <button
            type="button"
            className="input-right-button"
            onClick={onRightIconClick}
            aria-label="Mostrar u ocultar contraseña"
          >
            <img
              src={rightIcon}
              alt=""
              className="input-icon right"
            />
          </button>
        )}

      </div>
    </div>
  );
}

export default Input;