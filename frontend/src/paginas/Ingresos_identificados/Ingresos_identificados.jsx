import "./Ingresos_identificados.css";

import { useEffect, useState } from "react";
import Layout from "../../componentes/layout/Layout";
import {
  obtenerCamarasIngresos,
  obtenerIngresos,
} from "../../servicios/api";
import FiltrosIngresos from "./componentes/FiltrosIngresos";
import TablaIngresos from "./componentes/TablaIngresos";

const LIMITE_PAGINA = 25;

export default function IngresosIdentificados() {
  const [ingresos, setIngresos] = useState([]);
  const [pagina, setPagina] = useState(1);
  const [total, setTotal] = useState(0);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState("");
  const [camaras, setCamaras] = useState([]);
  const [filtrosAplicados, setFiltrosAplicados] = useState({});

  useEffect(() => {
    let activo = true;
    obtenerIngresos(pagina, LIMITE_PAGINA, filtrosAplicados)
      .then((respuesta) => {
        if (!activo) return;
        setIngresos(respuesta.ingresos);
        setTotal(respuesta.total);
      })
      .catch((errorSolicitud) => {
        if (!activo) return;
        setIngresos([]);
        setTotal(0);
        setError(errorSolicitud.message);
      })
      .finally(() => {
        if (activo) setCargando(false);
      });
    return () => {
      activo = false;
    };
  }, [pagina, filtrosAplicados]);

  useEffect(() => {
    let activo = true;
    obtenerCamarasIngresos()
      .then((respuesta) => {
        if (activo) setCamaras(respuesta.camaras);
      })
      .catch((errorSolicitud) => {
        if (activo) setError(errorSolicitud.message);
      });
    return () => {
      activo = false;
    };
  }, []);

  const cambiarPagina = (nuevaPagina) => {
    setCargando(true);
    setError("");
    setPagina(nuevaPagina);
  };

  const aplicarFiltros = (nuevosFiltros) => {
    setCargando(true);
    setError("");
    setPagina(1);
    setFiltrosAplicados(nuevosFiltros);
  };

  return (
    <Layout
      titulo="Ingresos identificados"
      subtitulo="Consulta y revisa todos los ingresos detectados por el sistema."
    >
      <section className="ingresos-identificados">
        <FiltrosIngresos
          camaras={camaras}
          cargando={cargando}
          onAplicar={aplicarFiltros}
        />

        <TablaIngresos
          ingresos={ingresos}
          total={total}
          pagina={pagina}
          limite={LIMITE_PAGINA}
          cargando={cargando}
          error={error}
          onCambiarPagina={cambiarPagina}
        />
      </section>
    </Layout>
  );
}
