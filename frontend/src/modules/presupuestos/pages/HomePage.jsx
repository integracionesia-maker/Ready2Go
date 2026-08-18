import { useEffect, useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { fetchTickets } from "@/api";
import { GlassPanel, SectionCard, usePageTitle } from "@/design";
import { PRESUPUESTOS_ROLES } from "../roles";

// `roles: null` = visible para cualquier sesión, igual que en Sidebar.jsx.
// Una tarjeta que lleva a una ruta que el rol no puede abrir manda al usuario
// a /403 desde la portada, así que la lista se filtra por rol.
const ADMIN_SECTIONS = [
  {
    to: "/dashboard",
    title: "Dashboard",
    description: "Resumen de gastos, KPIs y tendencias por periodo.",
    icon: "M4 5a1 1 0 011-1h14a1 1 0 011 1v2a1 1 0 01-1 1H5a1 1 0 01-1-1V5zm0 8a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H5a1 1 0 01-1-1v-6zm12 0a1 1 0 011-1h2a1 1 0 011 1v6a1 1 0 01-1 1h-2a1 1 0 01-1-1v-6z",
    roles: PRESUPUESTOS_ROLES,
  },
  {
    to: "/creadores",
    title: "Creadores",
    description: "Consulta el presupuesto y progreso de cada creador.",
    icon: "M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z",
    roles: PRESUPUESTOS_ROLES,
  },
  {
    to: "/transacciones",
    title: "Transacciones",
    description: "Historial detallado de tickets y comprobantes.",
    icon: "M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z",
    roles: null,
  },
  {
    to: "/gastos-generales",
    title: "Gastos Generales",
    description: "Registra y consulta gastos operativos no ligados a creadores.",
    icon: "M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z",
    roles: PRESUPUESTOS_ROLES,
  },
  // Administración no tiene tarjeta a propósito: es la vista más destructiva
  // del módulo (creadores, marcas, estados) y no necesita un acceso directo en
  // la portada. Se sigue llegando por el menú lateral, que solo la muestra a
  // admin/superadmin.
];

const TICKET_ICON =
  "M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z";

import { formatMXN } from "@/design";

function formatDateShort(iso) {
  if (!iso) return "—";
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(y, m - 1, d).toLocaleDateString("es-MX", {
    day: "numeric",
    month: "short",
  });
}

/* ── Inicio para todo rol que no sea creador ───────────────────────────── */
function AdminHome({ role }) {
  const secciones = ADMIN_SECTIONS.filter((s) => !s.roles || s.roles.includes(role));

  return (
    <div className="mx-auto grid max-w-4xl grid-cols-1 gap-6 sm:grid-cols-2">
      {secciones.map(({ roles, ...s }) => (
        <SectionCard key={s.to} {...s} />
      ))}
    </div>
  );
}

/* ── Inicio para rol creador: su presupuesto + sus tickets + 2 acciones ── */
function CreatorHome({ creator, onNewTicket }) {
  const [counts, setCounts] = useState(null);

  useEffect(() => {
    let cancelled = false;
    fetchTickets()
      .then((tickets) => {
        if (cancelled) return;
        setCounts({
          pendiente: tickets.filter((t) => t.status === "pendiente").length,
          aprobado: tickets.filter((t) => t.status === "aprobado").length,
          rechazado: tickets.filter((t) => t.status === "rechazado").length,
        });
      })
      .catch(() => {
        if (!cancelled) setCounts(null);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const hasCycle = creator && creator.cycle_amount != null;
  const spent = hasCycle ? creator.cycle_spent || 0 : 0;
  const amount = hasCycle ? creator.cycle_amount || 0 : 0;
  const remaining = hasCycle ? creator.cycle_remaining || 0 : 0;
  const pct = amount > 0 ? Math.min((spent / amount) * 100, 100) : 0;
  const barColor =
    remaining <= 0
      ? "var(--go-error)"
      : pct >= 75
      ? "var(--go-warning)"
      : "var(--go-success)";

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      {/* ── Estatus de mi presupuesto ─────────────────────────────────── */}
      <GlassPanel className="p-5">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <span className="go-eyebrow">Mi presupuesto</span>
          {hasCycle && (
            <span className="go-badge go-badge-warning">
              Ciclo {creator.cycle_period === "semanal" ? "semanal" : "mensual"}
              {creator.cycle_end_date
                ? ` · termina el ${formatDateShort(creator.cycle_end_date)}`
                : ""}
            </span>
          )}
        </div>

        {hasCycle ? (
          <>
            <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-3">
              <div>
                <p className="font-body text-xs" style={{ color: "var(--go-text-secondary)" }}>
                  Asignado
                </p>
                <p className="font-mono text-xl font-semibold" style={{ color: "var(--go-text-primary)" }}>
                  {formatMXN(amount)}
                </p>
              </div>
              <div>
                <p className="font-body text-xs" style={{ color: "var(--go-text-secondary)" }}>
                  Gastado
                </p>
                <p className="font-mono text-xl font-semibold" style={{ color: "var(--go-warning)" }}>
                  {formatMXN(spent)}
                </p>
              </div>
              <div>
                <p className="font-body text-xs" style={{ color: "var(--go-text-secondary)" }}>
                  Disponible
                </p>
                <p
                  className="font-mono text-xl font-semibold"
                  style={{ color: remaining <= 0 ? "var(--go-error)" : "var(--go-success)" }}
                >
                  {formatMXN(remaining)}
                </p>
              </div>
            </div>

            <div className="mt-4">
              <div
                className="h-2.5 w-full overflow-hidden rounded-full"
                style={{ background: "var(--go-surface-sunken)" }}
              >
                <div
                  className="h-full rounded-full transition-all duration-500"
                  style={{ width: `${pct}%`, background: barColor }}
                />
              </div>
              <p className="mt-1.5 font-body text-xs" style={{ color: "var(--go-text-secondary)" }}>
                {pct.toFixed(0)}% del ciclo utilizado
              </p>
            </div>
          </>
        ) : (
          <p className="mt-3 font-body text-sm" style={{ color: "var(--go-text-secondary)" }}>
            Aún no tienes un ciclo de presupuesto asignado. Contacta a tu administrador.
          </p>
        )}
      </GlassPanel>

      {/* ── Mis tickets por estado ────────────────────────────────────── */}
      {counts && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          {[
            { label: "Pendientes", value: counts.pendiente, badge: "go-badge-warning" },
            { label: "Aprobados", value: counts.aprobado, badge: "go-badge-success" },
            { label: "Rechazados", value: counts.rechazado, badge: "go-badge-error" },
          ].map((c) => (
            <GlassPanel key={c.label} className="flex items-center justify-between py-4 px-5">
              <span className={`go-badge ${c.badge}`}>{c.label}</span>
              <span className="font-mono text-2xl font-semibold" style={{ color: "var(--go-text-primary)" }}>
                {c.value}
              </span>
            </GlassPanel>
          ))}
        </div>
      )}

      {/* ── Acciones ──────────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
        <SectionCard
          to="/transacciones"
          title="Mis Transacciones"
          description="Historial de tus tickets, su estado y comprobantes."
          icon={TICKET_ICON}
        />
        <SectionCard
          onClick={onNewTicket}
          title="Nuevo Ticket"
          description="Sube un ticket de gasto; quedará pendiente de validación."
          icon="M12 4v16m8-8H4"
        />
      </div>
    </div>
  );
}

export default function HomePage({ creators = [], onNewTicket }) {
  usePageTitle("Inicio");
  const { user } = useAuth();
  const isCreator = user?.role === "creador";
  const myCreator = isCreator
    ? creators.find((c) => c.id === user.creator_id) || creators[0] || null
    : null;

  return (
    <div className="space-y-10">
      {/* ── Welcome ───────────────────────────────────────────────────── */}
      <div className="mx-auto max-w-2xl pt-8 text-center">
        <p className="go-eyebrow mb-3">Grupo Ortiz</p>
        <h1
          className="font-display text-2xl font-bold uppercase tracking-[0.04em] sm:text-3xl"
          style={{ color: "var(--go-text-primary)" }}
        >
          {isCreator && user?.full_name
            ? `Hola, ${user.full_name.split(" ")[0]}`
            : "Bienvenido al Control de Presupuestos"}
        </h1>
        <p className="mt-3 font-body text-sm sm:text-base" style={{ color: "var(--go-text-secondary)" }}>
          {isCreator
            ? "Este es el estado de tu presupuesto y tus tickets."
            : "Gestiona los presupuestos de creadores de contenido, registra tickets de gasto y monitorea el desempeño de cada campaña."}
        </p>
      </div>

      {isCreator ? (
        <CreatorHome creator={myCreator} onNewTicket={onNewTicket} />
      ) : (
        <AdminHome role={user?.role} />
      )}
    </div>
  );
}
