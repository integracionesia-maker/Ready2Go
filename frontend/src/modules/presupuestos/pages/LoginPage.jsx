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
  const [showPassword, setShowPassword] = useState(false);
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
              GOCreate
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
            <div className="relative">
              <input
                type={showPassword ? "text" : "password"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="go-input pr-10"
                autoComplete="current-password"
                required
              />
              <button
                type="button"
                onClick={() => setShowPassword((v) => !v)}
                className="absolute right-2 top-1/2 -translate-y-1/2 rounded p-1 transition-colors hover:bg-white/5"
                style={{ color: "var(--go-text-secondary)" }}
                aria-label={showPassword ? "Ocultar contraseña" : "Mostrar contraseña"}
                tabIndex={-1}
              >
                {showPassword ? (
                  <svg className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth={1.5} viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M3.98 8.223A10.477 10.477 0 001.934 12c1.292 4.338 5.31 7.507 10.066 7.507.993 0 1.953-.138 2.863-.395M6.228 6.228A10.45 10.45 0 0112 4.5c4.756 0 8.773 3.162 10.065 7.498a10.523 10.523 0 01-4.293 5.774M6.228 6.228L3 3m3.228 3.228l3.65 3.65m7.894 7.894L21 21m-3.228-3.228l-3.65-3.65m0 0a3 3 0 10-4.243-4.243m4.242 4.242L9.88 9.88" />
                  </svg>
                ) : (
                  <svg className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth={1.5} viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M2.036 12.322a1.012 1.012 0 010-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178z" />
                    <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                  </svg>
                )}
              </button>
            </div>
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
