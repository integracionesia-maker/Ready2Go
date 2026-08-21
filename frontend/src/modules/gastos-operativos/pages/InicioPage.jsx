import { useEffect, useState } from "react";
import { GlassPanel, SectionCard, usePageTitle } from "@/design";
import { useAuth } from "@/context/AuthContext";
import { operationalDashboard } from "../api";

const ICON = {
  registro:
    "M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z",
  dashboard:
    "M4 5a1 1 0 011-1h14a1 1 0 011 1v2a1 1 0 01-1 1H5a1 1 0 01-1-1V5zm0 8a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H5a1 1 0 01-1-1v-6zm12 0a1 1 0 011-1h2a1 1 0 011 1v6a1 1 0 01-1 1h-2a1 1 0 01-1-1v-6z",
  rubros:
    "M7 7h.01M7 3h5a1.99 1.99 0 011.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.99 1.99 0 013 12V7a4 4 0 014-4z",
};

function formatCurrency(n) {
  return new Intl.NumberFormat("es-MX", { style: "currency", currency: "MXN", minimumFractionDigits: 2 }).format(n || 0);
}

const NOMBRE_MES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"];

export default function InicioPage() {
  usePageTitle("Gastos Operativos");
  const { user } = useAuth();
  const puedeGestionarRubros = (user?.permisos?.gastos_operativos || []).includes("gestionar_rubros");

  const [resumen, setResumen] = useState(null); // { total, count } del mes actual

  useEffect(() => {
    let cancelado = false;
    const hoy = new Date();
    const inicioMes = new Date(hoy.getFullYear(), hoy.getMonth(), 1);
    operationalDashboard({ startDate: inicioMes, endDate: hoy })
      .then((d) => { if (!cancelado) setResumen({ total: d.total, count: d.count }); })
      .catch(() => { if (!cancelado) setResumen(null); });
    return () => { cancelado = true; };
  }, []);

  const secciones = [
    { to: "/gastos-operativos/registro", title: "Registro", description: "Alta y listado de gastos, con filtros y total.", icon: ICON.registro },
    { to: "/gastos-operativos/dashboard", title: "Dashboard", description: "Total por rubro y tendencia mensual.", icon: ICON.dashboard },
    ...(puedeGestionarRubros
      ? [{ to: "/gastos-operativos/rubros", title: "Rubros", description: "Gestiona las clasificaciones de gasto.", icon: ICON.rubros }]
      : []),
  ];

  const mesActual = NOMBRE_MES[new Date().getMonth()];

  return (
    <div className="space-y-10">
      <div className="mx-auto max-w-2xl pt-8 text-center">
        <p className="go-eyebrow mb-3">Grupo Ortiz</p>
        <h1 className="font-display text-2xl font-bold uppercase tracking-[0.04em] sm:text-3xl" style={{ color: "var(--go-text-primary)" }}>
          Gastos Operativos
        </h1>
        <p className="mt-3 font-body text-sm sm:text-base" style={{ color: "var(--go-text-secondary)" }}>
          Registro de gastos por rubro, separado de marketing. Sube el comprobante, clasifícalo y consulta en qué se gasta más.
        </p>
      </div>

      {/* Total del mes en curso — solo si el dashboard respondió. */}
      {resumen && (
        <div className="mx-auto max-w-4xl">
          <GlassPanel className="flex flex-wrap items-center justify-between gap-3 p-5">
            <div>
              <p className="go-eyebrow">Gastado en {mesActual}</p>
              <p className="font-mono text-2xl font-bold tracking-tight" style={{ color: "var(--go-warning)" }}>
                {formatCurrency(resumen.total)}
              </p>
            </div>
            <span className="font-body text-sm" style={{ color: "var(--go-text-secondary)" }}>
              {resumen.count} {resumen.count === 1 ? "gasto" : "gastos"} este mes
            </span>
          </GlassPanel>
        </div>
      )}

      <div className="mx-auto grid max-w-4xl grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
        {secciones.map((s) => (
          <SectionCard key={s.to} {...s} />
        ))}
      </div>
    </div>
  );
}
