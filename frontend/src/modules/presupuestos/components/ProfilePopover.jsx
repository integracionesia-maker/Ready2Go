import { useCallback, useEffect, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { AboutPanel, APP_VERSION, ICONS } from "@/design";

/** Clics sobre la versión que abren el panel "acerca de" (design/AboutPanel.jsx). */
const TAPS_PARA_ABRIR = 7;
/** Sin clics durante este tiempo, el contador vuelve a cero: así los clics
 *  sueltos de toda una sesión no se acumulan hasta disparar el panel solos. */
const MS_PARA_OLVIDAR = 2000;

const ROLE_LABELS = {
  superadmin: "Superadministrador",
  admin: "Administrador",
  creador: "Creador",
  marketing_presupuestos: "Marketing (Presupuestos)",
  marketing_equipos: "Marketing (Equipos)",
  marketing_admin: "Marketing (Administrador)",
  marketing_basico: "Marketing (Básico)",
  colaborador_mkt: "Marketing",
  usuario: "Usuario",
};

function initials(fullName) {
  if (!fullName) return "?";
  return fullName
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0].toUpperCase())
    .join("");
}

/** Popover de perfil (R1): anclado al botón, cierra con click-fuera, Escape,
 * o al navegar. Reemplaza el bloque de usuario + logout que vivía en el Sidebar. */
export default function ProfilePopover({ onBeforeToggle }) {
  const { user, logout } = useAuth();
  const [open, setOpen] = useState(false);
  const containerRef = useRef(null);
  const location = useLocation();
  const navigate = useNavigate();

  // Easter egg: 7 clics sobre la versión abren el panel "acerca de".
  const [taps, setTaps] = useState(0);
  const [aboutOpen, setAboutOpen] = useState(false);
  const tapTimer = useRef(null);

  // El temporizador vive fuera de React, así que hay que limpiarlo a mano al
  // desmontar; si no, dispara un setState sobre un componente que ya no está.
  useEffect(() => () => clearTimeout(tapTimer.current), []);

  const registrarTap = useCallback(() => {
    clearTimeout(tapTimer.current);
    setTaps((previos) => {
      const siguiente = previos + 1;
      if (siguiente >= TAPS_PARA_ABRIR) {
        // El popover se cierra: el panel es un modal a pantalla completa y
        // dejar el menú abierto detrás se ve como un bug.
        setOpen(false);
        setAboutOpen(true);
        return 0;
      }
      tapTimer.current = setTimeout(() => setTaps(0), MS_PARA_OLVIDAR);
      return siguiente;
    });
  }, []);

  useEffect(() => {
    setOpen(false);
  }, [location.pathname]);

  useEffect(() => {
    if (!open) return undefined;

    function handleClickOutside(e) {
      if (containerRef.current && !containerRef.current.contains(e.target)) {
        setOpen(false);
      }
    }
    function handleEscape(e) {
      if (e.key === "Escape") setOpen(false);
    }

    document.addEventListener("mousedown", handleClickOutside);
    document.addEventListener("keydown", handleEscape);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      document.removeEventListener("keydown", handleEscape);
    };
  }, [open]);

  if (!user) return null;

  return (
    <div className="relative" ref={containerRef}>
      <button
        onClick={() => { if (onBeforeToggle) onBeforeToggle(); setOpen((o) => !o); }}
        aria-expanded={open}
        aria-haspopup="true"
        className="flex min-h-[44px] items-center gap-2.5 rounded-go px-2 py-1.5 transition-colors hover:bg-white/5"
      >
        <div
          className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full font-display text-xs font-bold"
          style={{ background: "var(--go-surface-sunken)", color: "var(--go-orange)" }}
        >
          {initials(user.full_name)}
        </div>
        <span className="hidden flex-col items-start sm:flex">
          <span className="font-display text-xs font-semibold" style={{ color: "var(--go-text-primary)" }}>
            {user.full_name}
          </span>
          <span className="font-body text-[10px]" style={{ color: "var(--go-text-secondary)" }}>
            {ROLE_LABELS[user.role] || user.role}
          </span>
        </span>
        <svg
          className={`h-4 w-4 flex-shrink-0 transition-transform ${open ? "rotate-180" : ""}`}
          fill="none"
          stroke="currentColor"
          strokeWidth={2}
          viewBox="0 0 24 24"
          style={{ color: "var(--go-text-secondary)" }}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {open && (
        <div
          role="menu"
          className="glass absolute right-0 top-[calc(100%+0.5rem)] z-50 w-52 overflow-hidden"
        >
            {/* Orange glow — same as sidebar */}
            <div aria-hidden="true" className="pointer-events-none absolute inset-0 overflow-hidden" style={{ borderRadius: "inherit" }}>
              <div
                className="absolute inset-0"
                style={{
                  background: "linear-gradient(0deg, rgba(251,103,11,0.10) 0%, rgba(251,103,11,0.05) 30%, transparent 60%, rgba(251,103,11,0.03) 100%)",
                }}
              />
            </div>

            <div className="relative z-10 border-b px-4 py-3" style={{ borderColor: "var(--go-border)" }}>
              <p className="truncate font-display text-sm font-semibold" style={{ color: "var(--go-text-primary)" }}>
                {user.full_name}
              </p>
              <p className="truncate font-body text-xs" style={{ color: "var(--go-text-secondary)" }}>
                {ROLE_LABELS[user.role] || user.role}
              </p>
            </div>
            <button
              role="menuitem"
              onClick={() => navigate("/perfil")}
              className="relative z-10 flex w-full items-center gap-2.5 px-4 py-2.5 text-left font-body text-sm transition-colors hover:bg-white/5"
              style={{ color: "var(--go-text-primary)" }}
            >
              <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={1.7} viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
              </svg>
              Mi perfil
            </button>
            {user.role === "superadmin" && (
              <button
                role="menuitem"
                onClick={() => navigate("/administracion-sistema")}
                className="relative z-10 flex w-full items-center gap-2.5 px-4 py-2.5 text-left font-body text-sm transition-colors hover:bg-white/5"
                style={{ color: "var(--go-text-primary)" }}
              >
                <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={1.7} viewBox="0 0 24 24">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065zM15 12a3 3 0 11-6 0 3 3 0 016 0z"
                  />
                </svg>
                Administración
              </button>
            )}
            {user.role === "superadmin" && (
              <button
                role="menuitem"
                onClick={() => navigate("/auditoria")}
                className="relative z-10 flex w-full items-center gap-2.5 px-4 py-2.5 text-left font-body text-sm transition-colors hover:bg-white/5"
                style={{ color: "var(--go-text-primary)" }}
              >
                <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={1.7} viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" d={ICONS.auditar} />
                </svg>
                Auditoría
              </button>
            )}
            <button
              role="menuitem"
              onClick={() => logout()}
              className="relative z-10 flex w-full items-center gap-2.5 px-4 py-2.5 text-left font-body text-sm transition-colors hover:bg-white/5"
              style={{ color: "var(--go-error)" }}
            >
              <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={1.7} viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"
                />
              </svg>
              Cerrar sesión
            </button>
            {/* Versión de la app (lote de calidad 2026-08-18): para soporte
                interno — "¿qué versión ves en el menú de perfil?".
                La versión sale de `design/buildInfo.js` (ver ahí por qué va por
                import.meta.env y no por `define`).

                Y desde 2026-08-27, el disparador del panel "acerca de": 7 clics
                aquí lo abren. Sin `cursor-pointer` a propósito — es un easter
                egg, no debe anunciarse como botón. `select-none` evita que los
                clics rápidos seleccionen el texto. */}
            <div
              className="relative z-10 border-t px-4 py-2 text-center"
              style={{ borderColor: "var(--go-border)" }}
            >
              <p
                onClick={registrarTap}
                className="select-none font-mono text-[11px]"
                style={{ color: "var(--go-text-muted)" }}
              >
                GOCreate v{APP_VERSION}
                {/* A partir del quinto clic se muestra cuántos faltan: sin esta
                    pista, quien va llegando abandona en el sexto y nunca sabe
                    que había algo. */}
                {taps >= 5 && (
                  <span style={{ color: "var(--go-orange)" }}> · {TAPS_PARA_ABRIR - taps}</span>
                )}
              </p>
            </div>
          </div>
      )}

      {/* Fuera del bloque del popover: al abrirse el panel el menú se cierra, y
          si viviera dentro se desmontaría con él. Se renderiza con portal a
          document.body (ver el comentario de AboutPanel.jsx sobre el
          backdrop-filter del header). */}
      <AboutPanel open={aboutOpen} onClose={() => setAboutOpen(false)} />
    </div>
  );
}
