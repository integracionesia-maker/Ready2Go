/**
 * Estado vacío — reusa el lenguaje visual de LoadingScreen (glifo atenuado en
 * escala de grises + texto centrado) en vez de inventar un segundo estilo.
 * Sin dependencia de BrandLogo (vive en modules/presupuestos): src/design/ no
 * importa de un módulo específico.
 */
export default function EmptyState({ title = "Nada por aquí todavía", message, action, icon }) {
  return (
    <div className="flex flex-col items-center justify-center gap-4 py-16 text-center">
      <div className="opacity-40 grayscale">
        {icon || (
          <svg className="h-10 w-10" fill="none" stroke="currentColor" strokeWidth={1.5} viewBox="0 0 24 24" style={{ color: "var(--go-text-muted)" }}>
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M3.75 9.75l1.72-4.3A2.25 2.25 0 017.57 4h8.86a2.25 2.25 0 012.1 1.45l1.72 4.3m-16.5 0h16.5m-16.5 0v7.5A2.25 2.25 0 006 19.5h12a2.25 2.25 0 002.25-2.25v-7.5m-16.5 0h4.5l1.06 2.25h5.88l1.06-2.25h4.5"
            />
          </svg>
        )}
      </div>
      <div className="flex flex-col items-center gap-1">
        <p className="font-display text-sm font-bold uppercase tracking-[0.06em]" style={{ color: "var(--go-text-primary)" }}>
          {title}
        </p>
        {message && (
          <p className="max-w-sm font-body text-sm" style={{ color: "var(--go-text-secondary)" }}>
            {message}
          </p>
        )}
      </div>
      {action}
    </div>
  );
}
