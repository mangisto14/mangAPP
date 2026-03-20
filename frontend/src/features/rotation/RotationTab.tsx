import { useEffect, useRef, useState } from "react";
import { Pencil, Settings, PlusCircle, MinusCircle, RefreshCw, ChevronDown, CalendarDays, FileDown } from "lucide-react";
import * as XLSX from "xlsx-js-style";
import {
  getRotation,
  updateRotationSlots,
  syncRotationGuards,
  syncScheduleGuards,
  updateRotationPeriod,
} from "./api";
import type { SyncResult } from "./api";
import { getGuards } from "../../api";
import type { Guard } from "../../types";
import type { RotationConfig } from "./types";
import { computePeriods, PERIOD_CONFIG, PERIOD_COLORS } from "./utils";
import { SkeletonRotation } from "../../components/Skeleton";
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

interface EditPeriodRangeProps {
  config: RotationConfig;
  period: Period;
  onClose: () => void;
  onSaved: () => void;
}

function dateInputValue(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

function EditPeriodRangeModal({ config, period, onClose, onSaved }: EditPeriodRangeProps) {
  const [newPeriodStart, setNewPeriodStart] = useState(dateInputValue(period.start));
  const [newPeriodEnd, setNewPeriodEnd] = useState(dateInputValue(period.end));
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const handleSave = async () => {
    if (!newPeriodStart || !newPeriodEnd) {
      setError("יש להזין תאריך התחלה וסיום");
      return;
    }
    if (newPeriodEnd <= newPeriodStart) {
      setError("תאריך סיום חייב להיות אחרי תאריך ההתחלה");
      return;
    }
    const nextStart = new Date(`${newPeriodStart}T00:00:00`).getTime();
    const nextEnd = new Date(`${newPeriodEnd}T00:00:00`).getTime();
    const overlapping = (config.periods ?? []).find((p) => {
      if (p.slot_num === period.slotIndex) return false;
      const otherStart = new Date(`${p.start_date}T00:00:00`).getTime();
      const otherEnd = new Date(`${p.end_date}T00:00:00`).getTime();
      return nextStart < otherEnd && nextEnd > otherStart;
    });
    if (overlapping) {
      setError(`הטווח חופף לתקופה ${overlapping.slot_num + 1}: ${overlapping.start_date} עד ${overlapping.end_date}`);
      return;
    }
    const message = `לעדכן את טווח החופשה של ${period.periodLabel} ל-${newPeriodStart} עד ${newPeriodEnd}?`;
    if (!window.confirm(message)) return;

    setSaving(true);
    setError("");
    try {
      await updateRotationPeriod(period.slotIndex, newPeriodStart, newPeriodEnd);
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
        <div className="flex items-center justify-between p-5 border-b border-bg-border shrink-0">
          <h2 className="font-bold text-text text-lg">עדכון טווח חופשה לתקופה</h2>
          <button onClick={onClose} className="text-text-dim hover:text-text text-xl px-2">✕</button>
        </div>
        <div className="overflow-y-auto flex-1 p-5 space-y-4">
          <div className="card space-y-2">
            <div className="text-xs text-text-dim">טווח נוכחי</div>
            <div className="text-sm font-semibold text-text">{period.label} · {period.periodLabel}</div>
          </div>
          <div>
            <label className="text-xs text-text-dim mb-1 block">תאריך התחלה חדש לתקופה</label>
            <input
              type="date"
              value={newPeriodStart}
              onChange={(e) => setNewPeriodStart(e.target.value)}
              className="input text-sm w-full"
            />
          </div>
          <div>
            <label className="text-xs text-text-dim mb-1 block">תאריך סיום חדש לתקופה</label>
            <input
              type="date"
              value={newPeriodEnd}
              onChange={(e) => setNewPeriodEnd(e.target.value)}
              className="input text-sm w-full"
            />
          </div>
          <div className="text-xs text-text-dim bg-primary/10 border border-primary/20 rounded-xl px-3 py-2">
            השינוי נשמר בנפרד לתקופה זו בלבד.
          </div>
          {error && (
            <div className="text-danger text-sm bg-danger/10 border border-danger/30 rounded-xl p-3">
              {error}
            </div>
          )}
        </div>
        <div className="p-5 border-t border-bg-border shrink-0">
          <button onClick={handleSave} disabled={saving} className="btn-primary w-full">
            {saving ? "שומר..." : "אישור ועדכון טווח"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── exportToExcel ─────────────────────────────────────────────────────────────

// Excel fill colors per period type (א-ג / ג-ה / ו-א)
const PERIOD_EXCEL_COLORS = [
  { header: "BFDBFE", cell: "EFF6FF" }, // blue  (א-ג)
  { header: "FDE68A", cell: "FFFBEB" }, // amber (ג-ה)
  { header: "BBF7D0", cell: "F0FDF4" }, // green (ו-א)
];


function exportToExcel(config: RotationConfig, periods: Period[]) {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const ws: Record<string, any> = {};
  const merges: { s: { r: number; c: number }; e: { r: number; c: number } }[] = [];

  const thin = { style: "thin", color: { rgb: "CBD5E1" } };
  const border = { top: thin, bottom: thin, left: thin, right: thin };

  const setCell = (r: number, c: number, v: string, s?: object) => {
    ws[XLSX.utils.encode_cell({ c, r })] = { v, t: "s", ...(s ? { s } : {}) };
  };

  const headerStyle = (bgColor: string) => ({
    font: { bold: true, sz: 11 },
    fill: { patternType: "solid", fgColor: { rgb: bgColor } },
    alignment: { horizontal: "center", vertical: "center" },
    border,
  });

  // Header row
  setCell(0, 0, "תפקיד", {
    font: { bold: true, sz: 11 },
    fill: { patternType: "solid", fgColor: { rgb: "E2E8F0" } },
    alignment: { horizontal: "right", vertical: "center" },
    border,
  });
  periods.forEach((p, ci) => {
    setCell(0, ci + 1, `${p.label} ${p.periodLabel}`, headerStyle(PERIOD_EXCEL_COLORS[p.periodIndex].header));
  });

  // Data rows — one row per guard, role cell merged vertically
  let row = 1;
  for (const [roleIdx, role] of config.roles.entries()) {
    if (roleIdx > 0) row += 1; // empty separator row between roles
    const maxGuards = Math.max(1, ...periods.map((p) => (role.slots[p.slotIndex] ?? []).length));

    setCell(row, 0, role.name, {
      font: { bold: true, sz: 10 },
      fill: { patternType: "solid", fgColor: { rgb: "F1F5F9" } },
      alignment: { horizontal: "right", vertical: "center" },
      border,
    });
    if (maxGuards > 1) {
      merges.push({ s: { r: row, c: 0 }, e: { r: row + maxGuards - 1, c: 0 } });
    }

    periods.forEach((p, ci) => {
      const names = role.slots[p.slotIndex] ?? [];
      const { cell: cellColor } = PERIOD_EXCEL_COLORS[p.periodIndex];
      for (let i = 0; i < maxGuards; i++) {
        setCell(row + i, ci + 1, names[i] ?? "", {
          fill: { patternType: "solid", fgColor: { rgb: cellColor } },
          alignment: { horizontal: "center", vertical: "center" },
          border,
        });
      }
    });

    row += maxGuards;
  }

  ws["!ref"] = XLSX.utils.encode_range({ s: { r: 0, c: 0 }, e: { r: row - 1, c: periods.length } });
  ws["!merges"] = merges;
  ws["!cols"] = [{ wch: 16 }, ...periods.map(() => ({ wch: 20 }))];

  const filename = `סבב_חופשה_${new Date().toISOString().slice(0, 10)}.xlsx`;
  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, ws, "סבב חופשה");

  // Try native share (mobile) → fallback to download (desktop)
  const buf: ArrayBuffer = XLSX.write(wb, { bookType: "xlsx", type: "array" });
  const file = new File([buf], filename, {
    type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  });

  if (navigator.canShare?.({ files: [file] })) {
    navigator.share({ files: [file], title: "סבב חופשה" }).catch(() => {
      XLSX.writeFile(wb, filename);
    });
  } else {
    XLSX.writeFile(wb, filename);
  }
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
  const [editRangePeriod, setEditRangePeriod] = useState<Period | null>(null);
  const [showActionsMenu, setShowActionsMenu] = useState(false);
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
  useEffect(() => {
    if (!loading && activePeriodRef.current) {
      activePeriodRef.current.scrollIntoView({ inline: "center", behavior: "smooth", block: "nearest" });
    }
  }, [loading]);

  if (loading) return <SkeletonRotation />;
  if (error || !config) return <div className="fade-in card border-danger/30 text-danger">{error || "שגיאה"}</div>;

  const numPeriods = Math.max(9 + extraWeeks * 3, config.periods?.length ?? 0);
  const periods = computePeriods(config, numPeriods);
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
          <div className="relative">
            <button
              onClick={() => setShowActionsMenu((v) => !v)}
              disabled={syncing || syncingSchedule}
              className="flex items-center gap-1.5 bg-bg-card border border-bg-border px-3 py-1.5
                         rounded-xl text-sm font-semibold text-text-dim hover:text-text
                         hover:border-primary/40 transition-all disabled:opacity-50"
            >
              פעולות
              <ChevronDown size={12} className={`transition-transform ${showActionsMenu ? "rotate-180" : ""}`} />
            </button>
            {showActionsMenu && (
              <>
                <div className="fixed inset-0 z-10" onClick={() => setShowActionsMenu(false)} />
                <div className="absolute left-0 top-full mt-1 bg-bg-card border border-bg-border
                                rounded-xl shadow-lg z-20 min-w-[140px] overflow-hidden">
                  <button
                    onClick={() => { setShowActionsMenu(false); setExtraWeeks((n) => n + 1); }}
                    className="w-full text-right px-4 py-2.5 text-sm text-text-dim hover:text-text
                               hover:bg-bg-base/60 transition-colors flex items-center gap-2 justify-end"
                  >
                    הוסף שבוע
                    <PlusCircle size={13} />
                  </button>
                  <button
                    onClick={() => { setShowActionsMenu(false); setExtraWeeks((n) => n - 1); }}
                    disabled={extraWeeks === 0}
                    className="w-full text-right px-4 py-2.5 text-sm text-text-dim hover:text-text
                               hover:bg-bg-base/60 transition-colors disabled:opacity-40 flex items-center gap-2 justify-end"
                  >
                    הסר שבוע
                    <MinusCircle size={13} />
                  </button>
                  <div className="border-t border-bg-border/50" />
                  <button
                    onClick={() => { setShowActionsMenu(false); handleSync(); }}
                    disabled={syncing}
                    className="w-full text-right px-4 py-2.5 text-sm text-text-dim hover:text-text
                               hover:bg-bg-base/60 transition-colors disabled:opacity-50 flex items-center gap-2 justify-end"
                  >
                    סנכרן סבב
                    <RefreshCw size={13} className={syncing ? "animate-spin" : ""} />
                  </button>
                  <button
                    onClick={() => { setShowActionsMenu(false); handleSyncSchedule(); }}
                    disabled={syncingSchedule}
                    className="w-full text-right px-4 py-2.5 text-sm text-text-dim hover:text-text
                               hover:bg-bg-base/60 transition-colors disabled:opacity-50 flex items-center gap-2 justify-end"
                  >
                    סנכרן לוח
                    <CalendarDays size={13} />
                  </button>
                  <div className="border-t border-bg-border/50" />
                  <button
                    onClick={() => { setShowActionsMenu(false); exportToExcel(config, periods); }}
                    className="w-full text-right px-4 py-2.5 text-sm text-text-dim hover:text-text
                               hover:bg-bg-base/60 transition-colors flex items-center gap-2 justify-end"
                  >
                    ייצוא
                    <FileDown size={13} />
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
                    <button
                      onClick={() => setEditRangePeriod(p)}
                      className="hover:text-primary transition-colors underline decoration-dotted underline-offset-2"
                      title="עדכון טווח תאריכים לחופשה"
                    >
                      {p.label}
                    </button>
                    <span className={`text-[10px] font-normal
                      ${p.isActive ? "text-primary-light" : "text-text-dim/60"}`}>
                      {p.periodLabel}
                    </span>
                    <div className="flex items-center gap-1 mt-0.5">
                      <button
                        onClick={() => setEditRangePeriod(p)}
                        className="p-0.5 text-text-dim/40 hover:text-primary transition-colors"
                        title="עדכן טווח תאריכים"
                      >
                        <CalendarDays size={10} />
                      </button>
                      <button
                        onClick={() => setEditSlot(p.slotIndex)}
                        className="p-0.5 text-text-dim/40 hover:text-primary transition-colors"
                        title="ערוך תקופה"
                      >
                        <Pencil size={10} />
                      </button>
                    </div>
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {config.roles.map((role) => (
              <tr key={role.id} className="border-t border-bg-border/50">
                <td className="py-2 px-3 font-bold text-text text-xs sticky right-0 bg-bg-deep z-10">
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

      {editRangePeriod && (
        <EditPeriodRangeModal
          config={config}
          period={editRangePeriod}
          onClose={() => setEditRangePeriod(null)}
          onSaved={() => { setEditRangePeriod(null); load(); }}
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

