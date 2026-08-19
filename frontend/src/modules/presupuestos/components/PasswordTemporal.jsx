import { useState } from "react";

/**
 * Contraseña temporal recién generada. Se muestra una sola vez: el backend
 * solo devuelve el texto plano en la respuesta del reset (users.py:
 * reset_password y reset_password_superadmin), después ya es un hash.
 *
 * Compartido entre el modal de edición de usuarios y el reset entre
 * superadmins (2026-08-19).
 */
export default function PasswordTemporal({ username, password }) {
  const [copiado, setCopiado] = useState(false);

  const copiar = async () => {
    try {
      await navigator.clipboard.writeText(password);
      setCopiado(true);
      setTimeout(() => setCopiado(false), 2000);
    } catch {
      // Sin portapapeles (contexto no seguro o permiso denegado): el campo
      // sigue siendo select-all, así que se puede copiar a mano.
    }
  };

  return (
    <div
      className="space-y-2 rounded-go border p-3"
      style={{ background: "rgba(52,168,83,0.08)", borderColor: "rgba(52,168,83,0.25)" }}
    >
      <p className="font-body text-xs" style={{ color: "var(--go-text-primary)" }}>
        Contraseña temporal de <strong>{username}</strong>. Solo se muestra una vez — cópiala antes
        de cerrar. Sus sesiones activas se cerraron y deberá cambiarla al entrar.
      </p>
      <div className="flex items-center gap-2">
        <code className="go-input select-all flex-1 font-mono text-sm">{password}</code>
        <button type="button" onClick={copiar} className="btn-go-ghost whitespace-nowrap text-xs">
          {copiado ? "Copiado" : "Copiar"}
        </button>
      </div>
    </div>
  );
}
