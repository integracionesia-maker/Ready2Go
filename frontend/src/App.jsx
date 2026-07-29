import { lazy, Suspense } from "react";
import { Routes, Route } from "react-router-dom";
import ProtectedRoute from "./modules/presupuestos/components/ProtectedRoute";
import PresupuestosLayout from "./modules/presupuestos/PresupuestosLayout";
import AppShell from "./shell/AppShell";

const LoginPage = lazy(() => import("./modules/presupuestos/pages/LoginPage"));
// Panel de diagnóstico TEMPORAL de I3 (ver DevMockHarness.jsx) — solo en
// desarrollo, `import.meta.env.DEV` es una constante de build: en
// `npm run build` (producción) esta rama es código muerto y Rollup la
// elimina, junto con el chunk del harness. Se borra cuando I4 tenga vistas
// reales de Equipos reaccionando a los mismos códigos de error.
const DevMockHarness = import.meta.env.DEV ? lazy(() => import("./modules/equipos/DevMockHarness")) : null;

// App.jsx se queda solo con enrutado (B-I04): el chrome genérico vive en
// src/shell/AppShell.jsx, los datos y rutas de Presupuestos en
// src/modules/presupuestos/PresupuestosLayout.jsx.
export default function App() {
  return (
    <Routes>
      <Route
        path="/login"
        element={
          <Suspense fallback={<div className="min-h-screen" style={{ background: "var(--go-bg)" }} />}>
            <LoginPage />
          </Suspense>
        }
      />
      <Route element={<ProtectedRoute />}>
        <Route element={<AppShell />}>
          {import.meta.env.DEV && (
            <Route
              path="/equipos/_mock-harness"
              element={
                <Suspense fallback={null}>
                  <DevMockHarness />
                </Suspense>
              }
            />
          )}
          <Route path="/*" element={<PresupuestosLayout />} />
        </Route>
      </Route>
    </Routes>
  );
}
