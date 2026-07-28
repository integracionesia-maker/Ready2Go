import { useState, useEffect, useCallback } from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import Header from "./modules/presupuestos/components/Header";
import Sidebar from "./modules/presupuestos/components/Sidebar";
import Dashboard from "./modules/presupuestos/components/Dashboard";
import CreatorList from "./modules/presupuestos/components/CreatorList";
import TransactionTable from "./modules/presupuestos/components/TransactionTable";
import AdminView from "./modules/presupuestos/components/AdminView";
import ValidationQueue from "./modules/presupuestos/components/ValidationQueue";
import GeneralExpensesPage from "./modules/presupuestos/pages/GeneralExpensesPage";
import UploadTicketModal from "./modules/presupuestos/components/UploadTicketModal";
import ProtectedRoute from "./modules/presupuestos/components/ProtectedRoute";
import LoadingScreen from "./modules/presupuestos/components/LoadingScreen";
import HomePage from "./modules/presupuestos/pages/HomePage";
import LoginPage from "./modules/presupuestos/pages/LoginPage";
import ProfilePage from "./modules/presupuestos/pages/ProfilePage";
import ForbiddenPage from "./modules/presupuestos/pages/ForbiddenPage";
import { useAuth } from "./context/AuthContext";
import { fetchCreators, fetchCreatorsKpi, fetchBrands, fetchTickets, isNetworkError } from "./api";

const ADMIN_ROLES = ["admin", "superadmin"];

function firstOfMonth(y, m) {
  return new Date(y, m, 1);
}

function today() {
  const t = new Date();
  return new Date(t.getFullYear(), t.getMonth(), t.getDate());
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/*"
        element={
          <ProtectedRoute>
            <AppShell />
          </ProtectedRoute>
        }
      />
    </Routes>
  );
}

function AppShell() {
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
