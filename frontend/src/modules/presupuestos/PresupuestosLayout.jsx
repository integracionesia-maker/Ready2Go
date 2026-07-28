import { useState, useEffect, useCallback } from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import Header from "./components/Header";
import Sidebar from "./components/Sidebar";
import Dashboard from "./components/Dashboard";
import CreatorList from "./components/CreatorList";
import TransactionTable from "./components/TransactionTable";
import AdminView from "./components/AdminView";
import ValidationQueue from "./components/ValidationQueue";
import GeneralExpensesPage from "./pages/GeneralExpensesPage";
import UploadTicketModal from "./components/UploadTicketModal";
import ProtectedRoute from "./components/ProtectedRoute";
import LoadingScreen from "./components/LoadingScreen";
import HomePage from "./pages/HomePage";
import ProfilePage from "./pages/ProfilePage";
import ForbiddenPage from "./pages/ForbiddenPage";
import { useAuth } from "@/context/AuthContext";
import { fetchCreators, fetchCreatorsKpi, fetchBrands, fetchTickets, isNetworkError } from "@/api";

const ADMIN_ROLES = ["admin", "superadmin"];

function firstOfMonth(y, m) {
  return new Date(y, m, 1);
}

function today() {
  const t = new Date();
  return new Date(t.getFullYear(), t.getMonth(), t.getDate());
}

// Renombrado de AppShell (B-I04): este componente NO es el chrome del shell
// (eso es src/shell/AppShell.jsx) — es el contenedor de datos y rutas de
// Presupuestos (loadData, creators, brands, kpi, pendingCount, dateRange,
// UploadTicketModal). Movido tal cual desde App.jsx, sin cambiar su lógica.
export default function PresupuestosLayout() {
  const { user } = useAuth();
  const isPrivileged = user && ADMIN_ROLES.includes(user.role);

  const [modalOpen, setModalOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(
    () => localStorage.getItem("sidebar-collapsed") === "true"
  );
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const [creators, setCreators] = useState([]);
  const [brands, setBrands] = useState([]);
  const [kpi, setKpi] = useState(null);
  const [pendingCount, setPendingCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [networkError, setNetworkError] = useState(false);

  const [dateRange, setDateRange] = useState(() => {
    const t = today();
    return { start: firstOfMonth(t.getFullYear(), t.getMonth()), end: t };
  });

  const handleToggleSidebar = () => {
    setSidebarCollapsed((prev) => {
      const next = !prev;
      localStorage.setItem("sidebar-collapsed", next ? "true" : "false");
      return next;
    });
  };

  const loadData = useCallback(async ({ silent = false } = {}) => {
    if (!silent) {
      setLoading(true);
      setNetworkError(false);
    }
    setError(null);
    try {
      const [c, k, b, pending] = await Promise.all([
        fetchCreators(),
        isPrivileged ? fetchCreatorsKpi() : Promise.resolve(null),
        fetchBrands(false), // incluye marcas inactivas para la vista de administración
        isPrivileged ? fetchTickets({ status: "pendiente" }) : Promise.resolve([]),
      ]);
      setCreators(c);
      setKpi(k);
      setBrands(b);
      setPendingCount(pending.length);
    } catch (e) {
      if (isNetworkError(e)) {
        // Una recarga "silent" (después de crear/aprobar/editar algo) nunca debe
        // tapar la página con la pantalla de sin conexión — desmontaría un
        // formulario abierto por una falla transitoria. Se degrada al banner
        // de error normal, igual que cualquier otro error en una carga silent.
        if (!silent) {
          setNetworkError(true);
        } else {
          setError("Se perdió la conexión con el servidor. Los datos podrían estar desactualizados.");
        }
      } else {
        setError(e.message);
      }
    } finally {
      if (!silent) setLoading(false);
    }
  }, [isPrivileged]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleTicketCreated = () => {
    loadData();
    setModalOpen(false);
  };

  return (
    <div className="min-h-screen" style={{ background: "var(--go-bg)" }}>
      <Header onOpenMobileMenu={() => setMobileMenuOpen(true)} />
      <Sidebar
        collapsed={sidebarCollapsed}
        onToggle={handleToggleSidebar}
        onNewTicket={() => setModalOpen(true)}
        pendingCount={pendingCount}
        mobileOpen={mobileMenuOpen}
        onCloseMobile={() => setMobileMenuOpen(false)}
      />

      <main
        className={`min-h-screen pt-16 transition-all duration-300 ${
          sidebarCollapsed ? "md:ml-16" : "md:ml-60"
        }`}
      >
        <div className="mx-auto w-full max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
          {error && (
            <div
              className="mb-6 rounded-go border px-4 py-3 font-body text-sm"
              style={{
                background: "rgba(229,62,62,0.08)",
                borderColor: "rgba(229,62,62,0.25)",
                color: "var(--go-error)",
              }}
            >
              {error}
            </div>
          )}

          <Routes>
            <Route
              path="/"
              element={
                <HomePage
                  creators={creators}
                  onNewTicket={() => setModalOpen(true)}
                />
              }
            />
            <Route
              path="/dashboard"
              element={
                <ProtectedRoute roles={ADMIN_ROLES}>
                  {loading || networkError ? (
                    <LoadingScreen isOffline={networkError} onRetry={loadData} />
                  ) : (
                    <Dashboard
                      kpi={kpi}
                      dateRange={dateRange}
                      onDateRangeChange={(start, end) =>
                        setDateRange({ start, end })
                      }
                    />
                  )}
                </ProtectedRoute>
              }
            />
            <Route
              path="/creadores"
              element={
                <ProtectedRoute roles={ADMIN_ROLES}>
                  {loading || networkError ? (
                    <LoadingScreen isOffline={networkError} onRetry={loadData} />
                  ) : (
                    <CreatorList creators={creators} />
                  )}
                </ProtectedRoute>
              }
            />
            <Route
              path="/transacciones"
              element={
                loading || networkError ? (
                  <LoadingScreen isOffline={networkError} onRetry={loadData} />
                ) : (
                  <TransactionTable
                    creators={creators}
                    brands={brands}
                    onChange={() => loadData({ silent: true })}
                  />
                )
              }
            />
            <Route
              path="/administracion"
              element={
                <ProtectedRoute roles={ADMIN_ROLES}>
                  {loading || networkError ? (
                    <LoadingScreen isOffline={networkError} onRetry={loadData} />
                  ) : (
                    <AdminView
                      creators={creators}
                      brands={brands}
                      onChange={() => loadData({ silent: true })}
                    />
                  )}
                </ProtectedRoute>
              }
            />
            <Route
              path="/validacion"
              element={
                <ProtectedRoute roles={ADMIN_ROLES}>
                  <ValidationQueue onChange={() => loadData({ silent: true })} />
                </ProtectedRoute>
              }
            />
            <Route
              path="/gastos-generales"
              element={
                <ProtectedRoute roles={ADMIN_ROLES}>
                  <GeneralExpensesPage brands={brands} />
                </ProtectedRoute>
              }
            />
            <Route path="/perfil" element={<ProfilePage />} />
            <Route path="/403" element={<ForbiddenPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </div>
      </main>

      {modalOpen && (
        <UploadTicketModal
          creators={creators}
          brands={brands}
          onClose={() => setModalOpen(false)}
          onSuccess={handleTicketCreated}
        />
      )}
    </div>
  );
}
