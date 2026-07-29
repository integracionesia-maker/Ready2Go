import { useEffect, useState } from "react";
import BrandLogo from "./BrandLogo";

const PHRASES = [
  "Sumando presupuestos...",
  "Contando tickets uno por uno...",
  "Afinando los gráficos...",
  "Poniendo los pesos en orden...",
  "Verificando que las cuentas cuadren...",
  "Espantando centavos perdidos...",
  "Alineando marcas y prioridades...",
  "Puliendo el dashboard...",
  "Consultando con el creador interior...",
  "Casi listo, lo prometemos...",
];

function useRotatingPhrase(intervalMs = 4000) {
  const [index, setIndex] = useState(() => Math.floor(Math.random() * PHRASES.length));

  useEffect(() => {
    const id = setInterval(() => {
      setIndex((i) => (i + 1) % PHRASES.length);
    }, intervalMs);
    return () => clearInterval(id);
  }, [intervalMs]);

  return { phrase: PHRASES[index], key: index };
}

/**
 * Pantalla de carga (R1): reemplaza al spinner simple en las rutas de
 * AppShell. Dos estados:
 *  - Normal: isotipo con pulso, barra de progreso indeterminada estilo
 *    NProgress y una frase que rota cada 4s con fade.
 *  - Sin conexión (`isOffline`): isotipo atenuado + mensaje + botón Reintentar,
 *    reemplaza por completo el estado normal (no hay parpadeo spinner→error).
 */
export default function LoadingScreen({ isOffline = false, onRetry }) {
  const { phrase, key } = useRotatingPhrase();

  return (
    <div className="flex min-h-[50vh] flex-col items-center justify-center gap-6 py-20">
      {!isOffline && (
        <div
          className="fixed left-0 right-0 top-0 z-[60] h-[3px] overflow-hidden"
          style={{ background: "var(--go-surface-sunken)" }}
          aria-hidden="true"
        >
          <div
            className="go-progress-fill h-full w-2/5"
            style={{
              background: "linear-gradient(90deg, transparent, var(--go-orange), transparent)",
            }}
          />
        </div>
      )}

      <div className={isOffline ? "opacity-40 grayscale" : "go-loading-logo"}>
        <BrandLogo variant="isotipo" className="h-12 w-auto" />
      </div>

      {isOffline ? (
        <div className="flex flex-col items-center gap-3 text-center">
          <p
            className="font-display text-base font-bold uppercase tracking-[0.06em]"
            style={{ color: "var(--go-text-primary)" }}
          >
            Sin conexión al servidor
          </p>
          <p className="max-w-sm font-body text-sm" style={{ color: "var(--go-text-secondary)" }}>
            Verifica tu conexión de red o que el servidor esté funcionando.
          </p>
          <button type="button" onClick={() => onRetry?.()} className="btn-go mt-2">
            Reintentar
          </button>
        </div>
      ) : (
        <p
          key={key}
          className="go-loading-phrase font-body text-sm"
          style={{ color: "var(--go-text-secondary)" }}
        >
          {phrase}
        </p>
      )}
    </div>
  );
}
