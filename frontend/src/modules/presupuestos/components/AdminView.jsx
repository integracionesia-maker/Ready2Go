import { useRef, useState } from "react";
import { createCreator, updateCreator, createBrand, updateBrand, fetchCreatorCycles } from "@/api";
import { useAuth } from "@/context/AuthContext";
import { PRIORITY_BADGE_CLASS, PRIORITY_LABELS } from "../utils/priority";
import Modal from "./Modal";
import { GlassPanel, RowActions, ICONS, usePageTitle, SortableHeaderCell, useSortable } from "@/design";

const CREATOR_COLUMNS = [
  { key: "name", label: "Nombre", type: "string" },
  { key: "cycle_amount", label: "Presupuesto", type: "number", align: "right" },
  { key: "cycle_spent", label: "Gastado", type: "number", align: "right" },
  { key: "cycle_remaining", label: "Restante", type: "number", align: "right" },
];

const BRAND_COLUMNS = [{ key: "name", label: "Nombre", type: "string" }];

const CYCLE_HISTORY_COLUMNS = [
  { key: "start_date", label: "Periodo", type: "date" },
  { key: "amount", label: "Monto", type: "number", align: "right" },
  { key: "spent", label: "Gastado", type: "number", align: "right" },
  { key: "remaining", label: "Restante", type: "number", align: "right" },
];

import { formatMXN } from "@/design";

const SECTIONS = [
  { key: "creators", label: "Creadores" },
  { key: "brands", label: "Marcas" },
];

export default function AdminView({ creators, brands, onChange }) {
  usePageTitle("Administración");
  const { user } = useAuth();
  const visibleSections = SECTIONS.filter((s) => !s.roles || s.roles.includes(user.role));

  const [section, setSection] = useState("creators");

  const {
    sortedItems: sortedCreators,
    sortKey: creatorSortKey,
    sortDir: creatorSortDir,
    cycleSort: cycleCreatorSort,
  } = useSortable(creators, CREATOR_COLUMNS);
  const {
    sortedItems: sortedBrands,
    sortKey: brandSortKey,
    sortDir: brandSortDir,
    cycleSort: cycleBrandSort,
  } = useSortable(brands, BRAND_COLUMNS);
  const {
    sortedItems: sortedCycleHistory,
    sortKey: cycleHistorySortKey,
    sortDir: cycleHistorySortDir,
    cycleSort: cycleCycleHistorySort,
  } = useSortable(cycleHistory, CYCLE_HISTORY_COLUMNS);

  /* Creator form modal (create when editingCreator === null, edit otherwise) */
  const [creatorFormOpen, setCreatorFormOpen] = useState(false);
  const [editingCreator, setEditingCreator] = useState(null);

  /* Brand form modal */
  const [brandFormOpen, setBrandFormOpen] = useState(false);
  const [editingBrand, setEditingBrand] = useState(null);

  /* Activation toggle confirmation: { type: "creator"|"brand", item, newActive } */
  const [confirmToggle, setConfirmToggle] = useState(null);

  /* Cycle history modal */
  const [cycleHistoryCreator, setCycleHistoryCreator] = useState(null);
  const [cycleHistory, setCycleHistory] = useState([]);
  const [cycleHistoryLoading, setCycleHistoryLoading] = useState(false);

  /* Shared form state (only one modal is open at a time) */
  const [formName, setFormName] = useState("");
  const [formBudget, setFormBudget] = useState("");
  const [formCyclePeriod, setFormCyclePeriod] = useState("mensual");
  const [formPriority, setFormPriority] = useState("media");
  // Campos del usuario vinculado (solo al crear creator)
  const [formUsername, setFormUsername] = useState("");
  const [formUserEmail, setFormUserEmail] = useState("");
  // Contraseña temporal mostrada tras crear
  const [tempPassword, setTempPassword] = useState(null);
  const [copied, setCopied] = useState(false);
  const copiedTimeout = useRef(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);

  /* ── Open / close helpers ────────────────────────────────────────────── */

  const resetFeedback = () => {
    setError(null);
    setSuccessMsg(null);
  };

  const openCreatorForm = (creator = null) => {
    resetFeedback();
    setTempPassword(null);
    setCopied(false);
    setEditingCreator(creator);
    setFormName(creator ? creator.name : "");
    // Creador sin configuración de ciclo: ciclo materializado es $0; abrir el
    // formulario con monto vacío (no "0") para que guardar sea un no-op.
    setFormBudget(creator && creator.cycle_amount ? String(creator.cycle_amount) : "");
    setFormCyclePeriod(creator ? creator.cycle_period || "mensual" : "mensual");
    setFormUsername("");
    setFormUserEmail("");
    setCreatorFormOpen(true);
  };

  const closeCreatorForm = () => {
    setCreatorFormOpen(false);
    setEditingCreator(null);
    setTempPassword(null);
    resetFeedback();
  };

  const openBrandForm = (brand = null) => {
    resetFeedback();
    setEditingBrand(brand);
    setFormName(brand ? brand.name : "");
    setFormPriority(brand ? brand.priority : "media");
    setBrandFormOpen(true);
  };

  const closeBrandForm = () => {
    setBrandFormOpen(false);
    setEditingBrand(null);
    resetFeedback();
  };

  const openCycleHistory = async (creator) => {
    resetFeedback();
    setCycleHistoryCreator(creator);
    setCycleHistoryLoading(true);
    try {
      setCycleHistory(await fetchCreatorCycles(creator.id));
    } catch (err) {
      setError(err.message);
    } finally {
      setCycleHistoryLoading(false);
    }
  };

  const closeCycleHistory = () => {
    setCycleHistoryCreator(null);
    setCycleHistory([]);
  };

  const openConfirmToggle = (type, item) => {
    resetFeedback();
    setConfirmToggle({ type, item, newActive: !item.is_active });
  };

  const closeConfirmToggle = () => {
    setConfirmToggle(null);
    resetFeedback();
  };

  /* ── Copy to clipboard ───────────────────────────────────────────────── */

  const handleCopyPassword = async () => {
    if (!tempPassword) return;
    try {
      await navigator.clipboard.writeText(tempPassword.password);
      setCopied(true);
      if (copiedTimeout.current) clearTimeout(copiedTimeout.current);
      copiedTimeout.current = setTimeout(() => setCopied(false), 2500);
    } catch {
      // clipboard API may fail silently (non-HTTPS, permission denied, etc.)
    }
  };
  // NOTA: sin auto-copia al montar el modal. Escribir la contraseña temporal al
  // portapapeles sin un gesto explícito del usuario la deja viva en el
  // portapapeles del sistema (máquinas compartidas: el siguiente Ctrl+V la
  // vierte) — se copia SOLO con el botón (auditoría de seguridad 2026-08-18).

  /* ── Submit handlers ─────────────────────────────────────────────────── */

  const handleCreatorSubmit = async (e) => {
    e.preventDefault();
    resetFeedback();

    const name = formName.trim();
    if (!name) { setError("El nombre es obligatorio."); return; }
    if (name.length > 100) { setError("El nombre no puede exceder 100 caracteres."); return; }
    // Monto opcional: vacío = creador sin configuración de ciclo todavía.
    if (formBudget !== "" && Number(formBudget) <= 0) { setError("El monto del ciclo debe ser mayor a $0."); return; }

    // Validar campos del usuario vinculado (solo al crear)
    if (!editingCreator) {
      if (!formUsername.trim() || formUsername.trim().length < 3) {
        setError("El nombre de usuario debe tener al menos 3 caracteres.");
        return;
      }
      if (!formUserEmail.trim()) {
        setError("El correo del creador es obligatorio.");
        return;
      }
    }

    setSubmitting(true);
    try {
      if (editingCreator) {
        await updateCreator(editingCreator.id, {
          name,
          cycle_budget_amount: hasBudget ? Number(formBudget) : null,
          cycle_period: hasBudget ? formCyclePeriod : null,
        });
        setSuccessMsg("Creador actualizado.");
        setTimeout(() => { closeCreatorForm(); onChange(); }, 800);
      } else {
        const result = await createCreator({
          name,
          cycle_budget_amount: hasBudget ? Number(formBudget) : null,
          cycle_period: hasBudget ? formCyclePeriod : null,
          username: formUsername.trim(),
          email: formUserEmail.trim(),
        });
        if (result.temporary_password) {
          setTempPassword({ username: formUsername.trim(), password: result.temporary_password });
        }
        setSuccessMsg("Creador y usuario vinculado creados.");
        onChange();
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  const handleBrandSubmit = async (e) => {
    e.preventDefault();
    resetFeedback();

    const name = formName.trim();
    if (!name) {
      setError("El nombre es obligatorio.");
      return;
    }
    if (name.length > 100) {
      setError("El nombre no puede exceder 100 caracteres.");
      return;
    }

    setSubmitting(true);
    try {
      if (editingBrand) {
        await updateBrand(editingBrand.id, { name, priority: formPriority });
      } else {
        await createBrand({ name, priority: formPriority });
      }
      setSuccessMsg("Marca guardada exitosamente.");
      setTimeout(() => {
        closeBrandForm();
        onChange();
      }, 800);
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  const handleToggleConfirm = async () => {
    if (!confirmToggle) return;
    resetFeedback();
    setSubmitting(true);
    try {
      const { type, item, newActive } = confirmToggle;
      if (type === "creator") {
        await updateCreator(item.id, { is_active: newActive });
      } else {
        await updateBrand(item.id, { is_active: newActive });
      }
      setConfirmToggle(null);
      onChange();
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  /* ── Derived ─────────────────────────────────────────────────────────── */

  const hasBudget = formBudget !== "" && Number(formBudget) > 0;

  const budgetWarning =
    editingCreator &&
    hasBudget &&
    Number(formBudget) < (editingCreator.cycle_spent ?? 0);

  const toggleText = confirmToggle
    ? confirmToggle.type === "creator"
      ? confirmToggle.newActive
        ? `¿Reactivar al creador ${confirmToggle.item.name}?`
        : `Al desactivar a ${confirmToggle.item.name}, no podrá recibir tickets nuevos hasta que sea reactivado.`
      : confirmToggle.newActive
      ? `¿Reactivar la marca ${confirmToggle.item.name}?`
      : `¿Desactivar la marca ${confirmToggle.item.name}? Las marcas inactivas no aparecerán en el registro de tickets.`
    : "";

  /* ── Shared banner styles ────────────────────────────────────────────── */

  const errorBanner = error && (
    <div
      className="rounded-go border px-4 py-3 font-body text-sm"
      style={{
        background: "rgba(229,62,62,0.08)",
        borderColor: "rgba(229,62,62,0.25)",
        color: "var(--go-error)",
      }}
    >
      {error}
    </div>
  );

  const successBanner = successMsg && (
    <div
      className="rounded-go border px-4 py-3 font-body text-sm"
      style={{
        background: "rgba(0,163,110,0.08)",
        borderColor: "rgba(0,163,110,0.25)",
        color: "var(--go-success)",
      }}
    >
      {successMsg}
    </div>
  );

  /* ── Render ──────────────────────────────────────────────────────────── */

  return (
    <div className="space-y-6">
      {/* ── Header + section tabs ──────────────────────────────────────── */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h2
          className="font-display text-lg font-bold uppercase tracking-[0.06em]"
          style={{ color: "var(--go-text-primary)" }}
        >
          Administración
        </h2>
        <nav
          aria-label="Secciones de Administracion"
          className="flex items-center gap-1 rounded-go p-1"
          style={{ background: "var(--go-surface)" }}
        >
          {visibleSections.map((s) => {
            const isActive = section === s.key;
            return (
              <button
                key={s.key}
                onClick={() => setSection(s.key)}
                className="rounded-go px-3 sm:px-4 py-1.5 font-display text-xs sm:text-sm font-semibold tracking-wide transition-all duration-200"
                style={{
                  background: isActive ? "var(--go-surface-sunken)" : "transparent",
                  color: isActive ? "var(--go-orange)" : "var(--go-text-secondary)",
                }}
              >
                {s.label}
              </button>
            );
          })}
        </nav>
      </div>

      {/* ── Creators section ───────────────────────────────────────────── */}
      {section === "creators" && (
        <GlassPanel className="space-y-4 p-4 sm:p-6">
          <div className="flex items-center justify-between">
            <span className="go-eyebrow">{creators.length} creadores</span>
            <button onClick={() => openCreatorForm()} className="btn-go">
              <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
              </svg>
              Nuevo Creador
            </button>
          </div>

          {creators.length === 0 ? (
            <div
              className="flex flex-col items-center justify-center py-16 font-body text-sm"
              style={{ color: "var(--go-text-secondary)" }}
            >
              <svg className="mb-3 h-10 w-10" fill="none" stroke="currentColor" strokeWidth={1} viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"
                />
              </svg>
              <p>No hay creadores registrados.</p>
            </div>
          ) : (
            <div className="go-table-scroll-wrapper">
            <div
              className="overflow-x-auto rounded-go-lg border go-table-scroll"
              style={{ borderColor: "var(--go-border)" }}
            >
              <table className="go-table">
                <thead>
                  <tr>
                    <SortableHeaderCell
                      label="Nombre"
                      columnKey="name"
                      activeKey={creatorSortKey}
                      dir={creatorSortDir}
                      onSort={cycleCreatorSort}
                    />
                    <th className="text-center">Ciclo</th>
                    <SortableHeaderCell
                      label="Presupuesto"
                      columnKey="cycle_amount"
                      activeKey={creatorSortKey}
                      dir={creatorSortDir}
                      onSort={cycleCreatorSort}
                      align="right"
                    />
                    <SortableHeaderCell
                      label="Gastado"
                      columnKey="cycle_spent"
                      activeKey={creatorSortKey}
                      dir={creatorSortDir}
                      onSort={cycleCreatorSort}
                      align="right"
                    />
                    <SortableHeaderCell
                      label="Restante"
                      columnKey="cycle_remaining"
                      activeKey={creatorSortKey}
                      dir={creatorSortDir}
                      onSort={cycleCreatorSort}
                      align="right"
                    />
                    <th className="text-center">Estado</th>
                    <th className="text-right">Acciones</th>
                  </tr>
                </thead>
                <tbody>
                  {sortedCreators.map((c) => (
                    <tr key={c.id}>
                      <td>
                        <span
                          className="font-display text-sm font-semibold"
                          style={{ color: "var(--go-text-primary)" }}
                        >
                          {c.name}
                        </span>
                      </td>
                      <td className="text-center">
                        <span className="go-badge" style={{ background: "var(--go-surface-sunken)", color: "var(--go-text-secondary)" }}>
                          {c.cycle_period === "semanal" ? "Semanal" : "Mensual"}
                        </span>
                      </td>
                      <td className="num text-right">{formatMXN(c.cycle_amount ?? 0)}</td>
                      <td className="num text-right" style={{ color: "var(--go-warning)" }}>
                        {formatMXN(c.cycle_spent ?? 0)}
                      </td>
                      <td
                        className="num text-right font-semibold"
                        style={{
                          color: (c.cycle_remaining ?? 0) <= 0 ? "var(--go-error)" : "var(--go-success)",
                        }}
                      >
                        {formatMXN(c.cycle_remaining ?? 0)}
                      </td>
                      <td className="text-center">
                        <span className={`go-badge ${c.is_active ? "go-badge-success" : "go-badge-error"}`}>
                          {c.is_active ? "Activo" : "Inactivo"}
                        </span>
                      </td>
                      <td>
                        <RowActions
                          actions={[
                            { key: "editar", label: "Editar", icon: ICONS.editar, onClick: () => openCreatorForm(c) },
                            {
                              key: "historico",
                              label: "Histórico",
                              icon: ICONS.historico,
                              onClick: () => openCycleHistory(c),
                            },
                            {
                              key: "toggle",
                              label: c.is_active ? "Desactivar" : "Activar",
                              icon: ICONS.toggle,
                              variant: c.is_active ? "danger" : undefined,
                              onClick: () => openConfirmToggle("creator", c),
                            },
                          ]}
                        />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            </div>
          )}
        </GlassPanel>
      )}

      {/* ── Brands section ─────────────────────────────────────────────── */}
      {section === "brands" && (
        <GlassPanel className="space-y-4 p-4 sm:p-6">
          <div className="flex items-center justify-between">
            <span className="go-eyebrow">{brands.length} marcas</span>
            <button onClick={() => openBrandForm()} className="btn-go">
              <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
              </svg>
              Nueva Marca
            </button>
          </div>

          {brands.length === 0 ? (
            <div
              className="flex flex-col items-center justify-center py-16 font-body text-sm"
              style={{ color: "var(--go-text-secondary)" }}
            >
              <svg className="mb-3 h-10 w-10" fill="none" stroke="currentColor" strokeWidth={1} viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M7 7h.01M7 3h5a2 2 0 011.414.586l7 7a2 2 0 010 2.828l-5 5a2 2 0 01-2.828 0l-7-7A2 2 0 015 8V5a2 2 0 012-2z"
                />
              </svg>
              <p>No hay marcas registradas.</p>
            </div>
          ) : (
            <div className="go-table-scroll-wrapper">
            <div
              className="overflow-x-auto rounded-go-lg border go-table-scroll"
              style={{ borderColor: "var(--go-border)" }}
            >
              <table className="go-table">
                <thead>
                  <tr>
                    <SortableHeaderCell
                      label="Nombre"
                      columnKey="name"
                      activeKey={brandSortKey}
                      dir={brandSortDir}
                      onSort={cycleBrandSort}
                    />
                    <th className="text-center">Prioridad</th>
                    <th className="text-center">Estado</th>
                    <th className="text-right">Acciones</th>
                  </tr>
                </thead>
                <tbody>
                  {sortedBrands.map((b) => (
                    <tr key={b.id}>
                      <td>
                        <span
                          className="font-display text-sm font-semibold"
                          style={{ color: "var(--go-text-primary)" }}
                        >
                          {b.name}
                        </span>
                      </td>
                      <td className="text-center">
                        <span className={`go-badge ${PRIORITY_BADGE_CLASS[b.priority] || "go-badge-warning"}`}>
                          {PRIORITY_LABELS[b.priority] || b.priority}
                        </span>
                      </td>
                      <td className="text-center">
                        <span className={`go-badge ${b.is_active ? "go-badge-success" : "go-badge-error"}`}>
                          {b.is_active ? "Activa" : "Inactiva"}
                        </span>
                      </td>
                      <td>
                        <RowActions
                          actions={[
                            { key: "editar", label: "Editar", icon: ICONS.editar, onClick: () => openBrandForm(b) },
                            {
                              key: "toggle",
                              label: b.is_active ? "Desactivar" : "Activar",
                              icon: ICONS.toggle,
                              variant: b.is_active ? "danger" : undefined,
                              onClick: () => openConfirmToggle("brand", b),
                            },
                          ]}
                        />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            </div>
          )}
        </GlassPanel>
      )}

      {/* ── Creator create/edit modal ──────────────────────────────────── */}
      {creatorFormOpen && (
        <Modal
          title={editingCreator ? "Editar Creador" : "Crear Creador"}
          onClose={closeCreatorForm}
          submitting={submitting}
        >
          <form onSubmit={handleCreatorSubmit} className="space-y-3 px-4 sm:px-6 py-4">
            {/* ── Creator data (2-col on sm+) ──────────────────────────── */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="go-eyebrow mb-1 block">Nombre</label>
                <input
                  type="text"
                  value={formName}
                  onChange={(e) => setFormName(e.target.value)}
                  placeholder="Nombre del creador..."
                  className="go-input"
                  maxLength={100}
                  required
                />
              </div>

              <div>
                <label className="go-eyebrow mb-1 block">
                  Monto del ciclo{" "}
                  <span className="font-normal" style={{ color: "var(--go-text-muted)" }}>
                    (Opcional)
                  </span>
                </label>
                <div className="relative">
                  <span
                    className="absolute left-3.5 top-[10px] font-mono text-sm"
                    style={{ color: "var(--go-text-secondary)" }}
                  >
                    $
                  </span>
                  <input
                    type="number"
                    step="0.01"
                    min="0.01"
                    value={formBudget}
                    onChange={(e) => setFormBudget(e.target.value)}
                    placeholder="Sin definir"
                    className="go-input pl-7 font-mono"
                  />
                </div>
                <p className="mt-1 font-body text-[10px]" style={{ color: "var(--go-text-muted)" }}>
                  Déjalo vacío si aún no tiene monto definido; podrás configurarlo después.
                </p>
              </div>
            </div>

            <div>
              <label className="go-eyebrow mb-1 block">Periodicidad</label>
              <select
                value={formCyclePeriod}
                onChange={(e) => setFormCyclePeriod(e.target.value)}
                className="go-select"
                disabled={!hasBudget}
              >
                <option value="mensual">Mensual</option>
                <option value="semanal">Semanal</option>
              </select>
              {!hasBudget && (
                <p className="mt-1 font-body text-[10px]" style={{ color: "var(--go-text-muted)" }}>
                  Se define junto con el monto del ciclo.
                </p>
              )}
            </div>

            {/* ── Cuenta de acceso (solo al crear) ──────────────────────── */}
            {!editingCreator && (
              <div className="border-t pt-3" style={{ borderColor: "var(--go-border)" }}>
                <p className="go-eyebrow mb-2">Cuenta de acceso</p>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <label className="go-eyebrow mb-1 block">Usuario</label>
                    <input
                      type="text" value={formUsername}
                      onChange={(e) => setFormUsername(e.target.value)}
                      placeholder={formName.trim().toLowerCase().replace(/\s+/g, ".").normalize("NFD").replace(/[̀-ͯ]/g, "") || "usuario.creador"}
                      className="go-input" minLength={3} maxLength={50} required
                    />
                    <p className="mt-1 font-body text-[10px]" style={{ color: "var(--go-text-muted)" }}>
                      Se genera a partir del nombre. Puedes cambiarlo.
                    </p>
                  </div>
                  <div>
                    <label className="go-eyebrow mb-1 block">Correo electrónico</label>
                    <input
                      type="email" value={formUserEmail}
                      onChange={(e) => setFormUserEmail(e.target.value)}
                      placeholder={formUsername.trim() ? `${formUsername.trim()}@creadores.grupo-ortiz.com` : "usuario@creadores.grupo-ortiz.com"}
                      className="go-input" maxLength={255} required
                    />
                  </div>
                </div>
              </div>
            )}

            {/* ── Contraseña temporal generada ─────────────────────────── */}
            {tempPassword && (
              <div
                className="rounded-go border px-4 py-3 space-y-2"
                style={{ background: "rgba(251,103,11,0.08)", borderColor: "rgba(251,103,11,0.25)" }}
              >
                <p className="font-body text-sm font-bold" style={{ color: "var(--go-orange)" }}>
                  Contraseña temporal generada
                </p>
                <p className="font-body text-xs" style={{ color: "var(--go-text-secondary)" }}>
                  Comparte esto con <strong>{tempPassword.username}</strong> por un canal seguro. Deberá cambiarla en su primer inicio de sesión.
                </p>
                <div className="flex items-center gap-2">
                  <div className="go-input flex-1 select-all font-mono text-sm" style={{ color: "var(--go-text-primary)" }}>
                    {tempPassword.password}
                  </div>
                  <button
                    type="button"
                    onClick={handleCopyPassword}
                    className="btn-go shrink-0 flex items-center gap-1.5"
                  >
                    {copied ? (
                      <>
                        <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                        </svg>
                        Copiado
                      </>
                    ) : (
                      <>
                        <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                          <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
                          <path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1" />
                        </svg>
                        Copiar
                      </>
                    )}
                  </button>
                </div>
              </div>
            )}

            {editingCreator && (
              <div
                className="rounded-go border px-4 py-3 font-body text-sm"
                style={{
                  background: "rgba(56,189,248,0.08)",
                  borderColor: "rgba(56,189,248,0.25)",
                  color: "#38bdf8",
                }}
              >
                Este cambio aplica al <strong>próximo ciclo</strong> — el ciclo vigente de{" "}
                {editingCreator.name} no se modifica.
                {budgetWarning && " El nuevo monto es menor a lo ya gastado en el ciclo actual."}
              </div>
            )}

            {errorBanner}
            {successBanner}

            <div className="flex items-center justify-end gap-3 pt-2">
              <button
                type="button"
                onClick={closeCreatorForm}
                disabled={submitting}
                className="btn-go-ghost"
              >
                {tempPassword ? "Cerrar" : "Cancelar"}
              </button>
              <button type="submit" disabled={submitting} className="btn-go">
                {submitting ? (
                  <>
                    <div className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                    Guardando...
                  </>
                ) : editingCreator ? (
                  "Guardar"
                ) : (
                  "Crear"
                )}
              </button>
            </div>
          </form>
        </Modal>
      )}

      {/* ── Brand create/edit modal ────────────────────────────────────── */}
      {brandFormOpen && (
        <Modal
          title={editingBrand ? "Editar Marca" : "Crear Marca"}
          onClose={closeBrandForm}
          submitting={submitting}
        >
          <form onSubmit={handleBrandSubmit} className="space-y-4 px-4 sm:px-6 py-5">
            <div>
              <label className="go-eyebrow mb-1.5 block">Nombre</label>
              <input
                type="text"
                value={formName}
                onChange={(e) => setFormName(e.target.value)}
                placeholder="Nombre de la marca..."
                className="go-input"
                maxLength={100}
                required
              />
            </div>

            <div>
              <label className="go-eyebrow mb-1.5 block">Prioridad</label>
              <select
                value={formPriority}
                onChange={(e) => setFormPriority(e.target.value)}
                className="go-select"
              >
                <option value="alta">Alta</option>
                <option value="media">Media</option>
                <option value="baja">Baja</option>
              </select>
            </div>

            {errorBanner}
            {successBanner}

            <div className="flex items-center justify-end gap-3 pt-2">
              <button
                type="button"
                onClick={closeBrandForm}
                disabled={submitting}
                className="btn-go-ghost"
              >
                Cancelar
              </button>
              <button type="submit" disabled={submitting} className="btn-go">
                {submitting ? (
                  <>
                    <div className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                    Guardando...
                  </>
                ) : editingBrand ? (
                  "Guardar"
                ) : (
                  "Crear"
                )}
              </button>
            </div>
          </form>
        </Modal>
      )}

      {/* ── Toggle confirmation modal ──────────────────────────────────── */}
      {confirmToggle && (
        <Modal
          title="Confirmar cambio de estado"
          onClose={closeConfirmToggle}
          submitting={submitting}
        >
          <div className="space-y-4 px-4 sm:px-6 py-5">
            <p className="font-body text-sm" style={{ color: "var(--go-text-primary)" }}>
              {toggleText}
            </p>

            {errorBanner}

            <div className="flex items-center justify-end gap-3 pt-2">
              <button
                type="button"
                onClick={closeConfirmToggle}
                disabled={submitting}
                className="btn-go-ghost"
              >
                Cancelar
              </button>
              <button
                type="button"
                onClick={handleToggleConfirm}
                disabled={submitting}
                className="btn-go"
              >
                {submitting ? (
                  <>
                    <div className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                    Aplicando...
                  </>
                ) : (
                  "Confirmar"
                )}
              </button>
            </div>
          </div>
        </Modal>
      )}

      {/* ── Histórico de ciclos ──────────────────────────────────────────── */}
      {cycleHistoryCreator && (
        <Modal
          title={`Histórico de ciclos — ${cycleHistoryCreator.name}`}
          onClose={closeCycleHistory}
        >
          <div className="space-y-4 px-4 sm:px-6 py-5">
            {cycleHistoryLoading ? (
              <p className="font-body text-sm" style={{ color: "var(--go-text-secondary)" }}>
                Cargando...
              </p>
            ) : cycleHistory.length === 0 ? (
              <p className="font-body text-sm" style={{ color: "var(--go-text-secondary)" }}>
                Sin ciclos registrados todavía.
              </p>
            ) : (
              <div className="go-table-scroll-wrapper">
                <div className="max-h-[60vh] overflow-y-auto overflow-x-auto rounded-go-lg border go-table-scroll" style={{ borderColor: "var(--go-border)" }}>
                  <table className="go-table">
                    <thead>
                      <tr>
                        <SortableHeaderCell
                          label="Periodo"
                          columnKey="start_date"
                          activeKey={cycleHistorySortKey}
                          dir={cycleHistorySortDir}
                          onSort={cycleCycleHistorySort}
                        />
                        <SortableHeaderCell
                          label="Monto"
                          columnKey="amount"
                          activeKey={cycleHistorySortKey}
                          dir={cycleHistorySortDir}
                          onSort={cycleCycleHistorySort}
                          align="right"
                        />
                        <SortableHeaderCell
                          label="Gastado"
                          columnKey="spent"
                          activeKey={cycleHistorySortKey}
                          dir={cycleHistorySortDir}
                          onSort={cycleCycleHistorySort}
                          align="right"
                        />
                        <SortableHeaderCell
                          label="Restante"
                          columnKey="remaining"
                          activeKey={cycleHistorySortKey}
                          dir={cycleHistorySortDir}
                          onSort={cycleCycleHistorySort}
                          align="right"
                        />
                      </tr>
                    </thead>
                    <tbody>
                      {sortedCycleHistory.map((cy) => (
                        <tr key={cy.id}>
                          <td>{cy.start_date} — {cy.end_date}</td>
                          <td className="num text-right">{formatMXN(cy.amount)}</td>
                          <td className="num text-right" style={{ color: "var(--go-warning)" }}>
                            {formatMXN(cy.spent)}
                          </td>
                          <td
                            className="num text-right font-semibold"
                            style={{ color: cy.remaining <= 0 ? "var(--go-error)" : "var(--go-success)" }}
                          >
                            {formatMXN(cy.remaining)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            <div className="flex justify-end">
              <button onClick={closeCycleHistory} className="btn-go-ghost">
                Cerrar
              </button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
}
