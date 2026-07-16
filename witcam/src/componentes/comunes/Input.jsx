function Input({ label, type = "text", placeholder, icon, rightIcon }) {
  return (
    <div className="input-group">
      <label>{label}</label>

      <div className="input-wrapper">
        <img src={icon} alt="" className="input-icon" />

        <input type={type} placeholder={placeholder} />

        {rightIcon && <img src={rightIcon} alt="" className="input-icon right" />}
      </div>
    </div>
  );
}

export default Input;