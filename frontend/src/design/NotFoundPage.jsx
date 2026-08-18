import { Link } from "react-router-dom";

/**
 * Página 404 compartida de ambos módulos. Antes, una ruta inexistente
 * redirigía a `/` en silencio (Presupuestos) o dejaba el área de contenido
 * vacía (Equipos): el usuario nunca sabía que la dirección estaba mal.
 *
 * Se renderiza DENTRO del shell autenticado (sidebar y header visibles),
 * así que el usuario puede seguir navegando sin perder contexto.
 */
export default function NotFoundPage() {
  return (
    <div className="flex min-h-[60vh] items-center justify-center px-4">
      <div className="glass w-full max-w-md">
        <div className="veil px-6 py-10 text-center">
          <p
            className="font-mono text-6xl font-bold leading-none"
            style={{ color: "var(--go-orange)" }}
          >
            404
          </p>
          <h1
            className="font-display mt-4 text-lg font-bold uppercase tracking-[0.06em]"
            style={{ color: "var(--go-text-primary)" }}
          >
            Página no encontrada
          </h1>
          <p className="font-body mt-2 text-sm" style={{ color: "var(--go-text-secondary)" }}>
            La dirección que escribiste no existe o fue movida.
            <br />
            Revisa la URL o vuelve al inicio.
          </p>
          <Link to="/" className="btn-go mt-6 inline-flex w-full justify-center">
            Volver al inicio
          </Link>
        </div>
      </div>
    </div>
  );
}
