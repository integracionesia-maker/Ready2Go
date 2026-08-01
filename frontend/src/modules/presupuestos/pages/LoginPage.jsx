import { useState } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import BrandLogo from "../components/BrandLogo";

export default function LoginPage() {
  const { user, loading, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [identificador, setIdentificador] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  if (!loading && user) {
    const from = location.state?.from?.pathname || "/";
    return <Navigate to={from} replace />;
  }

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(identificador, password);
      const from = location.state?.from?.pathname || "/";
      navigate(from, { replace: true });
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <div className="mb-8 flex flex-col items-center gap-3">
          <BrandLogo variant="imagotipo" className="h-20 sm:h-28 w-auto" />
          <div className="text-center">
            <h1
              className="font-display text-lg font-bold uppercase tracking-[0.06em]"
              style={{ color: "var(--go-text-primary)" }}
            >
              Ready2Go
            </h1>
            <p className="font-body text-xs" style={{ color: "var(--go-text-secondary)" }}>
              Plataforma de Marketing — Grupo Ortiz
            </p>
          </div>
        </div>

        {/* Única superficie de cristal de /login — pantalla sola, sin
            competir con el presupuesto de 3-4 del shell. */}
        <form onSubmit={handleSubmit} className="glass relative">
        <div className="veil space-y-4 p-6">
          <div>
            <label className="go-eyebrow mb-1.5 block">Usuario o correo</label>
            <input
              type="text"
              value={identificador}
              onChange={(e) => setIdentificador(e.target.value)}
              className="go-input"
              autoComplete="username"
              autoFocus
              required
            />
          </div>

          <div>
            <label className="go-eyebrow mb-1.5 block">Contraseña</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="go-input"
              autoComplete="current-password"
              required
            />
          </div>

          {error && (
            <div
              className="rounded-go border px-4 py-3 font-body text-sm"
              style={{
                background: "rgba(229,62,62,0.08)",
                borderColor: "rgba(229,62,62,0.25)",
                color: "var(--go-error)",
              }}
            >
              {error}
            </div>
          )}

          <button type="submit" disabled={submitting} className="btn-go w-full justify-center">
            {submitting ? (
              <>
                <div className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                Ingresando...
              </>
            ) : (
              "Iniciar sesión"
            )}
          </button>
        </div>
        </form>
      </div>
    </div>
  );
}
