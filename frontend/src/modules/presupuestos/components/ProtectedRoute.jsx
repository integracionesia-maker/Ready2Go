import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import LoadingScreen from "./LoadingScreen";

function FullScreenSpinner() {
  return (
    <div className="flex min-h-screen items-center justify-center">
      <div
        className="h-10 w-10 animate-spin rounded-full border-[3px]"
        style={{ borderColor: "var(--go-border)", borderTopColor: "var(--go-orange)" }}
      />
    </div>
  );
}

/**
 * Guard de rutas: sin sesión -> /login (preservando destino); con sesión pero
 * must_change_password pendiente -> /perfil; con sesión pero rol no permitido -> /403.
 * Si la verificación de sesión falla por red (no por 401 real), muestra el
 * estado "sin conexión" (R1) en vez de mandar a /login engañosamente.
 */
export default function ProtectedRoute({ roles, children }) {
  const { user, loading, networkError, retrying, retryCheckSession } = useAuth();
  const location = useLocation();

  if (loading) {
    return <FullScreenSpinner />;
  }

  if (networkError) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <LoadingScreen isOffline={!retrying} onRetry={retryCheckSession} />
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  if (user.must_change_password && location.pathname !== "/perfil") {
    return <Navigate to="/perfil" replace />;
  }

  if (roles && !roles.includes(user.role)) {
    return <Navigate to="/403" replace />;
  }

  // Sin children (uso como layout route del shell): renderiza el Outlet.
  // Con children (uso existente, por página dentro de PresupuestosLayout):
  // comportamiento idéntico al de siempre.
  return children ?? <Outlet />;
}
