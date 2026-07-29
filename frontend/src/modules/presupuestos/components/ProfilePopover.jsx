import { useEffect, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";

const ROLE_LABELS = {
  superadmin: "Superadministrador",
  admin: "Administrador",
  creador: "Creador",
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
export default function ProfilePopover() {
  const { user, logout } = useAuth();
  const [open, setOpen] = useState(false);
  const containerRef = useRef(null);
  const location = useLocation();
  const navigate = useNavigate();

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
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        aria-haspopup="true"
        className="flex items-center gap-2.5 rounded-go px-2 py-1.5 transition-colors hover:bg-white/5"
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
          className="absolute right-0 top-[calc(100%+0.5rem)] z-50 w-52 overflow-hidden rounded-go-lg border"
          style={{
            background: "var(--go-surface-raised)",
            borderColor: "var(--go-border)",
            boxShadow: "0 10px 30px rgba(0,0,0,0.3)",
          }}
        >
          <div className="border-b px-4 py-3" style={{ borderColor: "var(--go-border)" }}>
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
            className="flex w-full items-center gap-2.5 px-4 py-2.5 text-left font-body text-sm transition-colors hover:bg-white/5"
            style={{ color: "var(--go-text-primary)" }}
          >
            <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={1.7} viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
            </svg>
            Mi perfil
          </button>
          <button
            role="menuitem"
            onClick={() => logout()}
            className="flex w-full items-center gap-2.5 px-4 py-2.5 text-left font-body text-sm transition-colors hover:bg-white/5"
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
        </div>
      )}
    </div>
  );
}
