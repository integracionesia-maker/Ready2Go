import ProfilePopover from "./ProfilePopover";
import ThemeToggle from "./ThemeToggle";
import BrandLogo from "./BrandLogo";

/** Barra superior fija global (R1): logo + Grupo Ortiz, hamburguesa en móvil
 * (abre el drawer del Sidebar, R3), toggle de tema y popover de perfil. */
export default function Header({ onOpenMobileMenu }) {
  return (
    <header
      className="fixed left-0 right-0 top-0 z-40 flex h-16 items-center justify-between border-b px-4 sm:px-6"
      style={{ background: "var(--go-surface)", borderColor: "var(--go-border)" }}
    >
      <div className="flex items-center gap-3">
        <button
          onClick={onOpenMobileMenu}
          className="-ml-1 flex h-9 w-9 items-center justify-center rounded-go transition-colors hover:bg-white/5 md:hidden"
          title="Abrir menú"
          aria-label="Abrir menú"
        >
          <svg className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24" style={{ color: "var(--go-text-secondary)" }}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h16M4 18h16" />
          </svg>
        </button>

        <BrandLogo variant="isotipo" className="h-8 w-auto flex-shrink-0" />
        <div className="hidden min-w-0 sm:block">
          <h1 className="truncate font-display text-sm font-bold uppercase tracking-[0.08em]" style={{ color: "var(--go-text-primary)" }}>
            Grupo Ortiz
          </h1>
          <p className="truncate font-body text-[10px] tracking-wide" style={{ color: "var(--go-text-secondary)" }}>
            Control de Presupuestos
          </p>
        </div>
      </div>

      <div className="flex items-center gap-2 sm:gap-3">
        <ThemeToggle />
        <ProfilePopover />
      </div>
    </header>
  );
}
