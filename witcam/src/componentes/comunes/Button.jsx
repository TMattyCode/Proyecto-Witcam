function Button({ children, ...props }) {
  return (
    <button className="primary-button" {...props}>
      {children}
    </button>
  );
}

export default Button;