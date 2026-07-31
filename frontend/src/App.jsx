import { lazy, Suspense } from "react";
import { Routes, Route } from "react-router-dom";
import ProtectedRoute from "./modules/presupuestos/components/ProtectedRoute";
import PresupuestosLayout from "./modules/presupuestos/PresupuestosLayout";
import AppShell from "./shell/AppShell";
import EquiposLayout from "./modules/equipos/EquiposLayout";
import { SkeletonShimmer } from "@/design";

const LoginPage = lazy(() => import("./modules/presupuestos/pages/LoginPage"));
const InicioPage = lazy(() => import("./modules/equipos/pages/InicioPage"));
const DashboardEquiposPage = lazy(() => import("./modules/equipos/pages/DashboardEquiposPage"));
const InventarioPage = lazy(() => import("./modules/equipos/pages/InventarioPage"));
const NuevoPrestamoPage = lazy(() => import("./modules/equipos/pages/NuevoPrestamoPage"));
const ActivosPage = lazy(() => import("./modules/equipos/pages/ActivosPage"));
const AprobacionesPage = lazy(() => import("./modules/equipos/pages/AprobacionesPage"));
const HistorialPage = lazy(() => import("./modules/equipos/pages/HistorialPage"));
const FichaPrestamoPage = lazy(() => import("./modules/equipos/pages/FichaPrestamoPage"));
// Panel de diagnóstico TEMPORAL de I3 (ver DevMockHarness.jsx) — solo en
// desarrollo, `import.meta.env.DEV` es una constante de build: en
// `npm run build` (producción) esta rama es código muerto y Rollup la
// elimina, junto con el chunk del harness. Se borra cuando I4 tenga vistas
// reales de Equipos reaccionando a los mismos códigos de error.
const DevMockHarness = import.meta.env.DEV ? lazy(() => import("./modules/equipos/DevMockHarness")) : null;
// Demo TEMPORAL de I5 (ver PermisosDemo.jsx) — mismo trato: solo DEV, se
// borra cuando I4 tenga vistas reales consumiendo usePermisos/RequierePermiso.
const PermisosDemo = import.meta.env.DEV ? lazy(() => import("./modules/equipos/permisos/PermisosDemo")) : null;

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
          {import.meta.env.DEV && (
            <Route
              path="/equipos/_permisos-demo"
              element={
                <Suspense fallback={null}>
                  <PermisosDemo />
                </Suspense>
              }
            />
          )}
          <Route
            path="/equipos"
            element={
              <Suspense fallback={<SkeletonShimmer className="h-64 w-full" />}>
                <EquiposLayout />
              </Suspense>
            }
          >
            <Route index element={<InicioPage />} />
            <Route path="dashboard" element={<DashboardEquiposPage />} />
            <Route path="inventario" element={<InventarioPage />} />
            <Route path="nuevo" element={<NuevoPrestamoPage />} />
            <Route path="activos" element={<ActivosPage />} />
            <Route path="aprobaciones" element={<AprobacionesPage />} />
            <Route path="historial" element={<HistorialPage />} />
            <Route path="prestamo/:folio" element={<FichaPrestamoPage />} />
          </Route>
          <Route path="/*" element={<PresupuestosLayout />} />
        </Route>
      </Route>
    </Routes>
  );
}
