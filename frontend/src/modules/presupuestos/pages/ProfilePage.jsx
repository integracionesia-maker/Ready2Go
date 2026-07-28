import { useEffect, useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { changePassword, fetchCreators, updateMe } from "@/api";

const ROLE_LABELS = {
  superadmin: "Superadministrador",
  admin: "Administrador",
  creador: "Creador",
};

function formatCurrency(amount) {
  return new Intl.NumberFormat("es-MX", {
    style: "currency",
    currency: "MXN",
    minimumFractionDigits: 2,
  }).format(amount);
}

function Banner({ type, children }) {
  if (!children) return null;
  const isError = type === "error";
  return (
    <div
      className="rounded-go border px-4 py-3 font-body text-sm"
      style={{
        background: isError ? "rgba(229,62,62,0.08)" : "rgba(0,163,110,0.08)",
        borderColor: isError ? "rgba(229,62,62,0.25)" : "rgba(0,163,110,0.25)",
        color: isError ? "var(--go-error)" : "var(--go-success)",
      }}
    >
      {children}
    </div>
  );
}

export default function ProfilePage() {
  const { user, refreshUser } = useAuth();

  const [fullName, setFullName] = useState(user?.full_name || "");
  const [email, setEmail] = useState(user?.email || "");
  const [profileSubmitting, setProfileSubmitting] = useState(false);
  const [profileError, setProfileError] = useState(null);
  const [profileSuccess, setProfileSuccess] = useState(null);

  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [passwordSubmitting, setPasswordSubmitting] = useState(false);
  const [passwordError, setPasswordError] = useState(null);
  const [passwordSuccess, setPasswordSuccess] = useState(null);

  const [ownBudget, setOwnBudget] = useState(null);

  const forcedChange = Boolean(user?.must_change_password);

  useEffect(() => {
    if (user?.role === "creador") {
      fetchCreators()
        .then((list) => setOwnBudget(list[0] || null))
        .catch(() => setOwnBudget(null));
    }
  }, [user?.role]);

  if (!user) return null;

  const handleProfileSubmit = async (e) => {
    e.preventDefault();
    setProfileError(null);
    setProfileSuccess(null);
    setProfileSubmitting(true);
    try {
      await updateMe({ full_name: fullName, email });
      await refreshUser();
      setProfileSuccess("Perfil actualizado.");
    } catch (err) {
      setProfileError(err.message);
    } finally {
      setProfileSubmitting(false);
    }
  };

  const handlePasswordSubmit = async (e) => {
    e.preventDefault();
    setPasswordError(null);
    setPasswordSuccess(null);

    if (newPassword !== confirmPassword) {
      setPasswordError("La confirmación no coincide con la nueva contraseña.");
      return;
    }

    setPasswordSubmitting(true);
    try {
      await changePassword(currentPassword, newPassword);
      await refreshUser();
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
      setPasswordSuccess("Contraseña actualizada.");
    } catch (err) {
      setPasswordError(err.message);
    } finally {
      setPasswordSubmitting(false);
    }
  };

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div>
        <h2
          className="font-display text-lg font-bold uppercase tracking-[0.06em]"
          style={{ color: "var(--go-text-primary)" }}
        >
          Mi Perfil
        </h2>
        <p className="mt-1 font-body text-sm" style={{ color: "var(--go-text-secondary)" }}>
          {ROLE_LABELS[user.role] || user.role}
        </p>
      </div>

      {forcedChange && (
        <Banner type="error">
          Debes cambiar tu contraseña temporal antes de continuar usando el sistema.
        </Banner>
      )}

      {user.role === "creador" && ownBudget && (
        <div className="go-card space-y-3">
          <div className="flex items-center justify-between">
            <span className="go-eyebrow">Mi ciclo de presupuesto</span>
            <span className="font-body text-xs capitalize" style={{ color: "var(--go-text-secondary)" }}>
              {ownBudget.cycle_period === "semanal" ? "Semanal" : "Mensual"}
              {ownBudget.cycle_start_date && ownBudget.cycle_end_date
                ? ` · ${ownBudget.cycle_start_date} a ${ownBudget.cycle_end_date}`
                : ""}
            </span>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <p className="font-body text-xs" style={{ color: "var(--go-text-secondary)" }}>
                Monto del ciclo
              </p>
              <p className="num font-display text-base font-bold" style={{ color: "var(--go-text-primary)" }}>
                {formatCurrency(ownBudget.cycle_amount ?? 0)}
              </p>
            </div>
            <div>
              <p className="font-body text-xs" style={{ color: "var(--go-text-secondary)" }}>
                Gastado
              </p>
              <p className="num font-display text-base font-bold" style={{ color: "var(--go-warning)" }}>
                {formatCurrency(ownBudget.cycle_spent ?? 0)}
              </p>
            </div>
            <div>
              <p className="font-body text-xs" style={{ color: "var(--go-text-secondary)" }}>
                Restante
              </p>
              <p
                className="num font-display text-base font-bold"
                style={{
                  color: (ownBudget.cycle_remaining ?? 0) <= 0 ? "var(--go-error)" : "var(--go-success)",
                }}
              >
                {formatCurrency(ownBudget.cycle_remaining ?? 0)}
              </p>
            </div>
          </div>
        </div>
      )}

      {!forcedChange && (
        <form onSubmit={handleProfileSubmit} className="go-card space-y-4">
          <span className="go-eyebrow">Datos personales</span>
          <div>
            <label className="go-eyebrow mb-1.5 block">Nombre completo</label>
            <input
              type="text"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              className="go-input"
              maxLength={150}
              required
            />
          </div>
          <div>
            <label className="go-eyebrow mb-1.5 block">Correo</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="go-input"
              required
            />
          </div>
          <div>
            <label className="go-eyebrow mb-1.5 block">Usuario</label>
            <input type="text" value={user.username} className="go-input opacity-60" disabled />
          </div>

          <Banner type="error">{profileError}</Banner>
          <Banner type="success">{profileSuccess}</Banner>

          <div className="flex justify-end">
            <button type="submit" disabled={profileSubmitting} className="btn-go">
              {profileSubmitting ? "Guardando..." : "Guardar cambios"}
            </button>
          </div>
        </form>
      )}

      <form onSubmit={handlePasswordSubmit} className="go-card space-y-4">
        <span className="go-eyebrow">Cambiar contraseña</span>
        <div>
          <label className="go-eyebrow mb-1.5 block">Contraseña actual</label>
          <input
            type="password"
            value={currentPassword}
            onChange={(e) => setCurrentPassword(e.target.value)}
            className="go-input"
            autoComplete="current-password"
            required
          />
        </div>
        <div>
          <label className="go-eyebrow mb-1.5 block">Nueva contraseña</label>
          <input
            type="password"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            className="go-input"
            autoComplete="new-password"
            minLength={10}
            required
          />
        </div>
        <div>
          <label className="go-eyebrow mb-1.5 block">Confirmar nueva contraseña</label>
          <input
            type="password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            className="go-input"
            autoComplete="new-password"
            minLength={10}
            required
          />
        </div>

        <Banner type="error">{passwordError}</Banner>
        <Banner type="success">{passwordSuccess}</Banner>

        <div className="flex justify-end">
          <button type="submit" disabled={passwordSubmitting} className="btn-go">
            {passwordSubmitting ? "Actualizando..." : "Actualizar contraseña"}
          </button>
        </div>
      </form>
    </div>
  );
}
