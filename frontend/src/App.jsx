import { lazy, Suspense } from "react";
import { Routes, Route } from "react-router-dom";
import ProtectedRoute from "./modules/presupuestos/components/ProtectedRoute";
import PresupuestosLayout from "./modules/presupuestos/PresupuestosLayout";
import AppShell from "./shell/AppShell";

const LoginPage = lazy(() => import("./modules/presupuestos/pages/LoginPage"));

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
          <Route path="/*" element={<PresupuestosLayout />} />
        </Route>
      </Route>
    </Routes>
  );
}
