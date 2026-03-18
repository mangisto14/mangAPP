import { useEffect, useRef, useState } from "react";
import { Pencil, Settings, PlusCircle, RefreshCw, ChevronDown } from "lucide-react";
import { getRotation, updateRotationSlots, syncRotationGuards, syncScheduleGuards } from "./api";
import type { SyncResult } from "./api";
import { getGuards } from "../../api";
import type { Guard } from "../../types";
import type { RotationConfig } from "./types";
import { computePeriods, PERIOD_CONFIG, PERIOD_COLORS } from "./utils";
import type { Period } from "./utils";
import EditRotationModal from "./EditRotationModal";
import GuardAutocomplete from "./GuardAutocomplete";

// ── Helpers ───────────────────────────────────────────────────────────────────

// ── EditPeriodModal ────────────────────────────────────────────────────────────

interface EditPeriodProps {
  config: RotationConfig;
  period: Period;
  guardNames: string[];
  guards: Guard[];
  onClose: () => void;
  onSaved: () => void;
}

function EditPeriodModal({ config, period, guardNames, guards, onClose, onSaved }: EditPeriodProps) {
  const [values, setValues] = useState<Record<number, string>>(
    Object.fromEntries(
      config.roles.map((r) => [r.id, (r.slots[period.slotIndex] ?? []).join(", ")])
    )
  );
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const handleSave = async () => {
    setSaving(true);
    setError("");
    try {
      for (const role of config.roles) {
        const needed = Math.max(9, period.slotIndex + 1);
        const newSlots = Array.from({ length: needed }, (_, i) => role.slots[i] ?? []);
        newSlots[period.slotIndex] = (values[role.id] ?? "")
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean);
        await updateRotationSlots(role.id, newSlots);
      }
      onSaved();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/60 flex items-end" onClick={onClose}>
      <div
        className="w-full bg-bg-card border-t border-bg-border rounded-t-2xl pb-8 slide-in
                   max-w-2xl mx-auto max-h-[80vh] flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-bg-border shrink-0">
          <h2 className="font-bold text-text text-lg">
            שיבוץ תקופה: {period.label} · {period.periodLabel}
          </h2>
          <button onClick={onClose} className="text-text-dim hover:text-text text-xl px-2">✕</button>
        </div>

        {/* Role inputs */}
        <div className="overflow-y-auto flex-1 p-5 space-y-3">
          {config.roles.map((role) => (
            <div key={role.id} className="flex items-start gap-3">
              <label className="text-sm font-bold text-text w-20 shrink-0 text-right pt-2">
                {role.name}
              </label>
              <GuardAutocomplete
                value={values[role.id] ?? ""}
                onChange={(v) => setValues((prev) => ({ ...prev, [role.id]: v }))}
                guardNames={guardNames}
                guards={guards}
                roleFilter={role.name}
              />
            </div>
          ))}
          {error && (
            <div className="text-danger text-sm bg-danger/10 border border-danger/30 rounded-xl p-3">
              {error}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-5 border-t border-bg-border shrink-0">
          <button onClick={handleSave} disabled={saving} className="btn-primary w-full">
            {saving ? "שומר..." : "💾 שמור שינויים"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── SyncModal ──────────────────────────────────────────────────────────────────

function SyncModal({ result, onClose }: { result: SyncResult; onClose: () => void }) {
  return (
    <div className="fixed inset-0 z-50 bg-black/60 flex items-end" onClick={onClose}>
      <div
        className="w-full bg-bg-card border-t border-bg-border rounded-t-2xl pb-8 slide-in
                   max-w-2xl mx-auto max-h-[80vh] flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between p-5 border-b border-bg-border shrink-0">
          <h2 className="font-bold text-text text-lg">תוצאות סנכרון סבב ↔ כוח אדם</h2>
          <button onClick={onClose} className="text-text-dim hover:text-text text-xl px-2">✕</button>
        </div>
        <div className="overflow-y-auto flex-1 p-5 space-y-5">

          {/* Updated */}
          <div>
            <h3 className="text-sm font-bold text-text mb-2 flex items-center gap-2">
              <span className="text-success">✓</span>
              {result.updated.length > 0
                ? `${result.updated.length} אנשים עודכנו בכוח האדם`
                : "לא עודכנו תפקידים"}
            </h3>
            {result.updated.length > 0 && (
              <div className="space-y-1">
                {result.updated.map((u) => (
                  <div key={u.name} className="flex items-center gap-2 text-xs bg-success/10 border border-success/25 rounded-xl px-3 py-2">
                    <span className="font-semibold text-text">{u.name}</span>
                    <span className="text-text-dim">{u.old_role ?? "ללא תפקיד"}</span>
                    <span className="text-text-dim">→</span>
                    <span className="text-success font-semibold">{u.new_role}</span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Conflicts */}
          {result.conflicts.length > 0 && (
            <div>
              <h3 className="text-sm font-bold text-warning mb-2 flex items-center gap-2">
                <span>⚠</span> {result.conflicts.length} התנגשויות — שם מופיע בכמה תפקידים
              </h3>
              <div className="space-y-1">
                {result.conflicts.map((c) => (
                  <div key={c.name} className="text-xs bg-warning/10 border border-warning/25 rounded-xl px-3 py-2">
                    <span className="font-semibold text-text">{c.name}</span>
                    <span className="text-warning mr-2">{c.roles.join(", ")}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Unknown in rotation */}
          {result.unknown_in_rotation.length > 0 && (
            <div>
              <h3 className="text-sm font-bold text-text-dim mb-2 flex items-center gap-2">
                <span>❓</span> {result.unknown_in_rotation.length} שמות בסבב שלא קיימים בכוח האדם
              </h3>
              <div className="flex flex-wrap gap-2">
                {result.unknown_in_rotation.map((n) => (
                  <span key={n} className="text-xs bg-bg-base border border-bg-border text-text-dim px-2.5 py-1 rounded-full">
                    {n}
                  </span>
                ))}
              </div>
            </div>
          )}

        </div>
        <div className="p-5 border-t border-bg-border shrink-0">
          <button onClick={onClose} className="btn-primary w-full">סגור</button>
        </div>
      </div>
    </div>
  );
}

// ── RotationTab ───────────────────────────────────────────────────────────────

export default function RotationTab() {
  const [config, setConfig] = useState<RotationConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [editSlot, setEditSlot] = useState<number | null>(null);
  const [showSettings, setShowSettings] = useState(false);
  const [extraWeeks, setExtraWeeks] = useState(0);
  const [syncing, setSyncing] = useState(false);
  const [syncingSchedule, setSyncingSchedule] = useState(false);
  const [syncResult, setSyncResult] = useState<SyncResult | null>(null);
  const [guardNames, setGuardNames] = useState<string[]>([]);
  const [guards, setGuards] = useState<Guard[]>([]);
  const [showUnassigned, setShowUnassigned] = useState(false);
  const [showSyncMenu, setShowSyncMenu] = useState(false);
  const activePeriodRef = useRef<HTMLTableCellElement>(null);

  const load = async () => {
    setLoading(true);
    setError("");
    try {
      const [cfg, guardList] = await Promise.all([getRotation(), getGuards()]);
      setConfig(cfg);
      setGuards(guardList);
      setGuardNames(guardList.map((g) => g.name));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  };

  const handleSync = async () => {
    setSyncing(true);
    try {
      const result = await syncRotationGuards();
      setSyncResult(result);
      load();
    } catch (e) {
      alert((e as Error).message);
    } finally {
      setSyncing(false);
    }
  };

  const handleSyncSchedule = async () => {
    setSyncingSchedule(true);
    try {
      const result = await syncScheduleGuards();
      setSyncResult(result);
      load();
    } catch (e) {
      alert((e as Error).message);
    } finally {
      setSyncingSchedule(false);
    }
  };

  useEffect(() => { load(); }, []);

  // Scroll to active period after data loads
  useEffect(() => {
    if (!loading && activePeriodRef.current) {
      activePeriodRef.current.scrollIntoView({ inline: "center", behavior: "smooth", block: "nearest" });
    }
  }, [loading]);

  if (loading) return <div className="fade-in text-center text-text-dim py-20">טוען...</div>;
  if (error || !config) return <div className="fade-in card border-danger/30 text-danger">{error || "שגיאה"}</div>;

  const numPeriods = 9 + extraWeeks * 3;
  const periods = computePeriods(config.start_date, numPeriods);
  const activePeriod = periods.find((p) => p.isActive);

  // Build name → role map for mismatch detection
  const guardRoleMap = new Map<string, string | null>(
    guards.map((g) => [g.name, g.role])
  );

  // Compute unassigned guards
  const assignedNames = new Set<string>();
  for (const role of config.roles) {
    for (const slot of role.slots) {
      for (const name of slot) assignedNames.add(name);
    }
  }
  const unassigned = guardNames.filter((n) => !assignedNames.has(n));

  return (
    <div className="fade-in space-y-4">
      {/* Toolbar */}
      <div className="flex items-center justify-between gap-2 flex-wrap">
        {activePeriod ? (
          <div className="text-xs font-semibold text-primary-light bg-primary/10 border border-primary/20
                          px-3 py-1.5 rounded-xl inline-flex items-center gap-2">
            <span className="w-2 h-2 bg-primary rounded-full animate-pulse" />
            תקופה פעילה: {activePeriod.label} · {activePeriod.periodLabel}
          </div>
        ) : <div />}
        <div className="flex items-center gap-2">
          {extraWeeks > 0 && (
            <button
              onClick={() => setExtraWeeks((n) => n - 1)}
              className="text-xs text-text-dim bg-bg-card border border-bg-border px-3 py-1.5
                         rounded-xl font-semibold hover:text-text hover:border-primary/40 transition-all"
            >
              הסר שבוע
            </button>
          )}
          <button
            onClick={() => setExtraWeeks((n) => n + 1)}
            className="flex items-center gap-1.5 text-xs text-success bg-success/10 border border-success/25
                       px-3 py-1.5 rounded-xl font-semibold hover:bg-success/20 transition-all"
          >
            <PlusCircle size={14} />
            הוסף שבוע
          </button>
          <div className="relative">
            <button
              onClick={() => setShowSyncMenu((v) => !v)}
              disabled={syncing || syncingSchedule}
              className="flex items-center gap-1.5 bg-bg-card border border-bg-border px-3 py-1.5
                         rounded-xl text-sm font-semibold text-text-dim hover:text-text
                         hover:border-primary/40 transition-all disabled:opacity-50"
            >
              <RefreshCw size={14} className={(syncing || syncingSchedule) ? "animate-spin" : ""} />
              סנכרן
              <ChevronDown size={12} className={`transition-transform ${showSyncMenu ? "rotate-180" : ""}`} />
            </button>
            {showSyncMenu && (
              <>
                <div className="fixed inset-0 z-10" onClick={() => setShowSyncMenu(false)} />
                <div className="absolute left-0 top-full mt-1 bg-bg-card border border-bg-border
                                rounded-xl shadow-lg z-20 min-w-[120px] overflow-hidden">
                  <button
                    onClick={() => { setShowSyncMenu(false); handleSync(); }}
                    disabled={syncing}
                    className="w-full text-right px-4 py-2.5 text-sm text-text-dim hover:text-text
                               hover:bg-bg-base/60 transition-colors disabled:opacity-50"
                  >
                    סנכרן סבב
                  </button>
                  <div className="border-t border-bg-border/50" />
                  <button
                    onClick={() => { setShowSyncMenu(false); handleSyncSchedule(); }}
                    disabled={syncingSchedule}
                    className="w-full text-right px-4 py-2.5 text-sm text-text-dim hover:text-text
                               hover:bg-bg-base/60 transition-colors disabled:opacity-50"
                  >
                    סנכרן לוח
                  </button>
                </div>
              </>
            )}
          </div>
          <button
            onClick={() => setShowSettings(true)}
            className="flex items-center gap-1.5 bg-bg-card border border-bg-border px-3 py-1.5
                       rounded-xl text-sm font-semibold text-text-dim hover:text-text
                       hover:border-primary/40 transition-all"
          >
            <Settings size={14} />
            הגדרות
          </button>
        </div>
      </div>

      {/* Legend + unassigned button */}
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <div className="flex gap-3 flex-wrap">
          {PERIOD_CONFIG.map((pc, i) => (
            <span key={i} className={`text-xs font-semibold px-3 py-1 rounded-full border ${PERIOD_COLORS[i]}`}>
              {pc.label}
            </span>
          ))}
        </div>
        <button
          onClick={() => setShowUnassigned((v) => !v)}
          className={`text-xs font-semibold px-3 py-1.5 rounded-xl border transition-all
            ${unassigned.length > 0
              ? "text-warning bg-warning/10 border-warning/25"
              : "text-success bg-success/10 border-success/25"}`}
        >
          {unassigned.length > 0
            ? `${unassigned.length} לא שובצו`
            : "כולם שובצו ✓"}
        </button>
      </div>

      {/* Unassigned report */}
      {showUnassigned && (
        <div className="card slide-in">
          <h3 className="font-semibold text-text text-sm mb-2">אנשים שלא שובצו לאף משבצת</h3>
          {unassigned.length === 0 ? (
            <p className="text-success text-sm">כל כוח האדם משובץ בסבב!</p>
          ) : (
            <div className="flex flex-wrap gap-2">
              {unassigned.map((name) => (
                <span key={name} className="text-xs bg-warning/10 text-warning border border-warning/25
                                            px-2.5 py-1 rounded-full font-medium">
                  {name}
                </span>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Table */}
      <div className="overflow-x-auto -mx-4 px-4">
        <table className="w-full text-sm border-collapse" style={{ minWidth: "700px" }}>
          <thead>
            <tr>
              <th className="text-right py-2 px-3 text-text-dim font-semibold text-xs w-20
                             sticky right-0 bg-bg-deep z-10">
                תפקיד
              </th>
              {periods.map((p) => (
                <th
                  key={p.slotIndex}
                  ref={p.isActive ? activePeriodRef : undefined}
                  className={`text-center py-2 px-1 text-xs font-semibold whitespace-nowrap
                    ${p.isActive
                      ? "text-primary bg-primary/10 rounded-t-lg border-t border-x border-primary/25"
                      : "text-text-dim"
                    }`}
                >
                  <div className="flex flex-col items-center gap-0.5">
                    <span>{p.label}</span>
                    <span className={`text-[10px] font-normal
                      ${p.isActive ? "text-primary-light" : "text-text-dim/60"}`}>
                      {p.periodLabel}
                    </span>
                    <button
                      onClick={() => setEditSlot(p.slotIndex)}
                      className="mt-0.5 p-0.5 text-text-dim/40 hover:text-primary transition-colors"
                      title="ערוך תקופה"
                    >
                      <Pencil size={10} />
                    </button>
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {config.roles.map((role) => (
              <tr key={role.id} className="border-t border-bg-border/50">
                <td className="py-2 px-3 font-bold text-primary text-sm sticky right-0 bg-bg-deep z-10 border-l-2 border-primary/30">
                  {role.name}
                </td>
                {periods.map((p) => {
                  const names = role.slots[p.slotIndex] ?? [];
                  return (
                    <td
                      key={p.slotIndex}
                      onClick={() => setEditSlot(p.slotIndex)}
                      className={`py-2 px-1 text-center align-top cursor-pointer
                        hover:bg-bg-card/60 transition-colors
                        ${p.isActive ? "bg-primary/5 border-x border-primary/25" : ""}`}
                    >
                      {names.length === 0 ? (
                        <span className="text-text-dim/30 text-xs">—</span>
                      ) : (
                        <div className="space-y-0.5">
                          {names.map((name) => {
                            const guardRole = guardRoleMap.get(name);
                            const mismatch = guardRole !== undefined && guardRole !== null && guardRole !== role.name;
                            return (
                              <div
                                key={name}
                                className={`text-xs px-1.5 py-0.5 rounded-lg border font-medium
                                  ${mismatch
                                    ? "bg-warning/10 border-warning/30 text-warning"
                                    : PERIOD_COLORS[p.periodIndex]
                                  }`}
                                title={mismatch ? `תפקיד אמיתי: ${guardRole || "ללא תפקיד"}` : undefined}
                              >
                                <div className="flex items-center gap-0.5">
                                  {mismatch && <span className="text-[9px]">⚠</span>}
                                  <span>{name}</span>
                                </div>
                                {guardRole && (
                                  <span className={`text-[9px] opacity-60 block leading-tight
                                    ${mismatch ? "text-warning" : ""}`}>
                                    {guardRole}
                                  </span>
                                )}
                              </div>
                            );
                          })}
                        </div>
                      )}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Edit period modal */}
      {editSlot !== null && (
        <EditPeriodModal
          config={config}
          period={periods[editSlot]}
          guardNames={guardNames}
          guards={guards}
          onClose={() => setEditSlot(null)}
          onSaved={() => { setEditSlot(null); load(); }}
        />
      )}

      {/* Settings modal (role management + start date) */}
      {showSettings && (
        <EditRotationModal
          config={config}
          guardNames={guardNames}
          guards={guards}
          onClose={() => setShowSettings(false)}
          onSaved={() => { setShowSettings(false); load(); }}
        />
      )}

      {/* Sync result modal */}
      {syncResult && (
        <SyncModal result={syncResult} onClose={() => setSyncResult(null)} />
      )}
    </div>
  );
}
