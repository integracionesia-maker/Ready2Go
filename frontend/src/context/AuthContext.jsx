import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { fetchMe, login as apiLogin, logout as apiLogout, setAuthFailureHandler, isNetworkError } from "../api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [networkError, setNetworkError] = useState(false);
  const [retrying, setRetrying] = useState(false);

  useEffect(() => {
    setAuthFailureHandler(() => setUser(null));
  }, []);

  // Determina la sesión vigente. Si falla por red (no por 401 real) no debe
  // interpretarse como "sin sesión" — ProtectedRoute usa `networkError` para
  // mostrar el estado "sin conexión" en vez de mandar a /login engañosamente.
  // `isRetry` distingue el chequeo inicial (usa `loading`, como siempre) del
  // que dispara el botón "Reintentar" (usa `retrying`) — así ProtectedRoute
  // nunca vuelve a mostrar el spinner genérico durante un reintento, solo
  // LoadingScreen (evita el parpadeo entre dos loaders distintos).
  const checkSession = useCallback(async (isRetry = false) => {
    if (isRetry) setRetrying(true);
    else setLoading(true);
    setNetworkError(false);
    try {
      const me = await fetchMe();
      setUser(me);
    } catch (e) {
      setUser(null);
      setNetworkError(isNetworkError(e));
    } finally {
      if (isRetry) setRetrying(false);
      else setLoading(false);
    }
  }, []);

  const retryCheckSession = useCallback(() => checkSession(true), [checkSession]);

  useEffect(() => {
    checkSession(false);
  }, [checkSession]);

  const login = useCallback(async (identificador, password) => {
    // B1 (fix, dami-branch + BeniBranch): login no resuelve permisos — solo
    // /auth/me los llena. Si nos quedaramos con `permisos: {}`, EquiposSidebar
    // (que filtra por usePermisos) se veria vacio hasta el proximo F5.
    const { user: loggedInUser } = await apiLogin(identificador, password);
    setUser(loggedInUser); // respuesta rapida del login (sin permisos: {})
    const me = await fetchMe(); // permisos reales — login/refresh no los llenan (ver auth.py:166-175)
    setUser(me);
    return me;
  }, []);

  const logout = useCallback(async () => {
    try {
      await apiLogout();
    } finally {
      setUser(null);
    }
  }, []);

  const refreshUser = useCallback(async () => {
    const me = await fetchMe();
    setUser(me);
    return me;
  }, []);

  const value = {
    user,
    loading,
    networkError,
    retrying,
    retryCheckSession,
    isAuthenticated: !!user,
    login,
    logout,
    refreshUser,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth debe usarse dentro de <AuthProvider>.");
  }
  return ctx;
}
