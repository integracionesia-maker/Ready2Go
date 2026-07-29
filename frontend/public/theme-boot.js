// Aplica el tema guardado ANTES del primer paint para evitar el flash del tema incorrecto.
// Default oscuro si no hay preferencia guardada (R2).
// Script clásico bloqueante (sin type="module", sin defer): si no bloquea,
// vuelve el flash que este script existe para evitar.
(function () {
  var saved = localStorage.getItem("theme");
  var theme = saved === "light" ? "light" : "dark";
  document.documentElement.setAttribute("data-theme", theme);
})();
