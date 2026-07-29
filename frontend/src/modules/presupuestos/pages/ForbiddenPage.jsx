import { Link } from "react-router-dom";

export default function ForbiddenPage() {
  return (
    <div className="mx-auto max-w-md pt-16 text-center">
      <div
        className="mx-auto mb-5 flex h-14 w-14 items-center justify-center rounded-go-lg"
        style={{ background: "var(--go-surface-sunken)" }}
      >
        <svg
          className="h-7 w-7"
          style={{ color: "var(--go-error)" }}
          fill="none"
          stroke="currentColor"
          strokeWidth={1.5}
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z"
          />
        </svg>
      </div>
      <h1
        className="font-display text-lg font-bold uppercase tracking-[0.06em]"
        style={{ color: "var(--go-text-primary)" }}
      >
        Acceso no autorizado
      </h1>
      <p className="mt-2 font-body text-sm" style={{ color: "var(--go-text-secondary)" }}>
        Tu rol no tiene permiso para ver esta sección.
      </p>
      <Link to="/" className="btn-go-ghost mt-6 inline-flex">
        Volver al inicio
      </Link>
    </div>
  );
}
