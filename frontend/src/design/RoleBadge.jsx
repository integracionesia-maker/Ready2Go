/** Etiqueta de rol/paquete — lee permisos_catalogo.json (docs/contratos/, solo lectura). */
const ROLE_META = {
  superadmin: { label: "Superadmin", tone: "success" },
  admin: { label: "Admin", tone: "success" },
  creador: { label: "Creador", tone: "warning" },
  colaborador_mkt: { label: "Colaborador Marketing", tone: "warning" },
  APROBADOR_EQUIPO: { label: "Aprobador de Equipo", tone: "neutral" },
  CUSTODIO_EQUIPO: { label: "Custodio de Equipo", tone: "neutral" },
  AUDITOR: { label: "Auditor", tone: "neutral" },
};

const TONE_CLASS = {
  success: "go-badge-success",
  warning: "go-badge-warning",
  error: "go-badge-error",
  neutral: "go-badge-neutral",
};

export default function RoleBadge({ role, className = "" }) {
  const meta = ROLE_META[role] || { label: role, tone: "neutral" };
  return <span className={`go-badge ${TONE_CLASS[meta.tone]} ${className}`.trim()}>{meta.label}</span>;
}
