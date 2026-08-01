import "./TarjetasResumen.css";

import iconoPersonas from "../../../assets/iconos/017 icono-personas-rellenas.png";
import iconoAlerta from "../../../assets/iconos/018 icono-alerta.png";
import iconoOjo from "../../../assets/iconos/019 icono-ojo-morado.png";

function Tarjeta({  icono, titulo, numero, tipo, iconoClase  }) {
  return (
    <article className="tarjeta-resumen">
      <div className="tarjeta-contenido">
        <div className={`tarjeta-icono ${tipo}`}>
          <img className={iconoClase} src={icono} alt="" />
        </div>

        <h3>{titulo}</h3>
      </div>

      <p className={`tarjeta-numero ${tipo}`}>{numero}</p>
    </article>
  );
}

function TarjetasResumen() {
  return (
    <section className="tarjetas-resumen">
      <Tarjeta
        icono={iconoPersonas}
        titulo="Personas detectadas recientemente"
        numero="0"
        tipo="azul"
        iconoClase="icono-personas-resumen"
      />

      <Tarjeta
        icono={iconoAlerta}
        titulo="Alertas pendientes"
        numero="0"
        tipo="rojo"
        iconoClase="icono-alerta-resumen"
      />

      <Tarjeta
        icono={iconoOjo}
        titulo="Personas en lista de observación"
        numero="0"
        tipo="morado"
        iconoClase="icono-ojo-resumen"
      />
    </section>
  );
}

export default TarjetasResumen;