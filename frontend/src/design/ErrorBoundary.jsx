import { Component } from "react";

/**
 * Boundary global de render de React. Convierte un crash (como el de
 * ApexCharts del 15/07/2026, que dejó pantalla en blanco sin boundary) en
 * una pantalla de recuperación con acciones, en vez de una página vacía.
 *
 * Solo captura errores de RENDER/lifecycle; los errores de handlers de
 * eventos y de async no pasan por aquí (comportamiento estándar de React).
 *
 * El detalle del error va a consola para diagnóstico; la pantalla no
 * muestra el mensaje crudo — no le aporta al usuario y podría filtrar
 * detalles internos.
 */
export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidCatch(error, info) {
    console.error("[ErrorBoundary]", error, info?.componentStack);
  }

  handleRecargar = () => {
    window.location.reload();
  };

  handleVolverInicio = () => {
    window.location.assign("/");
  };

  render() {
    if (!this.state.error) return this.props.children;

    return (
      <div className="flex min-h-screen items-center justify-center px-4">
        <div className="glass w-full max-w-md">
          <div className="veil px-6 py-10 text-center">
            <p
              className="font-mono text-4xl font-bold leading-none"
              style={{ color: "var(--go-error)" }}
            >
              ¡Ups!
            </p>
            <h1
              className="font-display mt-4 text-lg font-bold uppercase tracking-[0.06em]"
              style={{ color: "var(--go-text-primary)" }}
            >
              Algo salió mal
            </h1>
            <p className="font-body mt-2 text-sm" style={{ color: "var(--go-text-secondary)" }}>
              Ocurrió un error inesperado al mostrar esta pantalla.
              <br />
              Tus datos están a salvo; recarga para continuar.
            </p>
            <div className="mt-6 flex flex-col gap-2">
              <button type="button" className="btn-go w-full justify-center" onClick={this.handleRecargar}>
                Recargar
              </button>
              <button type="button" className="btn-go-ghost w-full justify-center" onClick={this.handleVolverInicio}>
                Volver al inicio
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }
}
