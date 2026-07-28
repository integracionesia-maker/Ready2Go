import { Routes, Route } from "react-router-dom";
import LoginPage from "./modules/presupuestos/pages/LoginPage";
import ProtectedRoute from "./modules/presupuestos/components/ProtectedRoute";
import PresupuestosLayout from "./modules/presupuestos/PresupuestosLayout";
import AppShell from "./shell/AppShell";

// App.jsx se queda solo con enrutado (B-I04): el chrome genérico vive en
// src/shell/AppShell.jsx, los datos y rutas de Presupuestos en
// src/modules/presupuestos/PresupuestosLayout.jsx.
export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<ProtectedRoute />}>
        <Route element={<AppShell />}>
          <Route path="/*" element={<PresupuestosLayout />} />
        </Route>
      </Route>
    </Routes>
  );
}
