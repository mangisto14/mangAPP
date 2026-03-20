import { useCallback, useEffect, useRef, useState } from "react";
import Clock from "./Clock";
import {
  getAbsences, markLeave, markReturn, resetAbsence,
  getHistory, getSettings, historyCSVUrl,
} from "./api";
import type { AbsenceStatus, AbsenceHistory, Settings, AlertThreshold } from "./types";
import type { AlertLevel } from "./Clock";
import { getRotation } from "../rotation/api";
import type { RotationConfig } from "../rotation/types";
import { computePeriods } from "../rotation/utils";
import { SkeletonAbsenceCards, SkeletonTableRows } from "../../components/Skeleton";
import { useReadOnly } from "../../hooks/useReadOnly";


const REASONS = ["רופא", "מחלה", "חופשה", "אישי", "אחר"];

function fmtDuration(min: number): string {
  if (min < 60) return `${min} דק'`;
  const h = Math.floor(min / 60);
  const m = min % 60;
  return m > 0 ? `${h}ש' ${m}ד'` : `${h} שעות`;
}

function fmtDate(iso: string): string {
  try {
    const d = new Date(iso.endsWith("Z") ? iso : iso + "Z");
    return d.toLocaleDateString("he-IL", { day: "2-digit", month: "2-digit", year: "2-digit" });
  } catch {
    return iso;
  }
}

function fmtTime(iso: string): string {
  try {
    const d = new Date(iso.endsWith("Z") ? iso : iso + "Z");
    return d.toLocaleTimeString("he-IL", { hour: "2-digit", minute: "2-digit" });
  } catch {
    return iso;
  }
}

function getAlertLevel(leftAt: string, thresholds: AlertThreshold[]): AlertLevel {
  if (!thresholds.length) return null;
  const diffMin = (Date.now() - new Date(leftAt.endsWith("Z") ? leftAt : leftAt + "Z").getTime()) / 60000;
  const sorted = [...thresholds].sort((a, b) => b.minutes - a.minutes);
  for (const t of sorted) {
    if (diffMin >= t.minutes) return t.level as AlertLevel;
  }
  return null;
}

const LEVEL_ROW: Record<NonNullable<AlertLevel>, string> = {
  warning:  "bg-warning/10 border border-warning/30",
  danger:   "bg-orange-400/10 border border-orange-400/30",
  critical: "bg-danger/10 border border-danger/30",
};

// ── Reason Sheet ─────────────────────────────────────────────────────────────
function ReasonSheet({
  name,
  onSelect,
  onCancel,
}: {
  name: string;
  onSelect: (reason: string | undefined) => void;
  onCancel: () => void;
}) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-end"
      onClick={onCancel}
    >
      <div
        className="w-full bg-bg-card border-t border-bg-border rounded-t-2xl p-5 pb-8 space-y-4 slide-in"
        onClick={(e) => e.stopPropagation()}
      >
        <h3 className="font-bold text-text text-center">סיבת יציאה — {name}</h3>
        <div className="grid grid-cols-3 gap-2">
          {REASONS.map((r) => (
            <button
              key={r}
              onClick={() => onSelect(r)}
              className="bg-bg-base border border-bg-border rounded-xl py-3 text-sm font-medium
                         text-text hover:border-primary/50 hover:bg-primary/10 transition-colors"
            >
              {r}
            </button>
          ))}
        </div>
        <button
          onClick={() => onSelect(undefined)}
          className="w-full text-text-dim text-sm py-2"
        >
          ללא סיבה
        </button>
      </div>
    </div>
  );
}

// ── Label + Date Input ────────────────────────────────────────────────────────
function DateInput({ label, value, onChange }: { label: string; value: string; onChange: (v: string) => void }) {
  return (
    <div className="flex flex-col gap-1 min-w-0">
      <label className="text-xs font-medium text-text-muted px-1">{label}</label>
      <input
        type="date"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="input text-sm w-full min-w-0"
      />
    </div>
  );
}

// ── History View ──────────────────────────────────────────────────────────────
function HistoryView({ absences }: { absences: AbsenceStatus[] }) {
  const [rows, setRows] = useState<AbsenceHistory[]>([]);
  const [loading, setLoading] = useState(true);
  const [guardFilter, setGuardFilter] = useState<number | undefined>();
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getHistory({
        guard_id: guardFilter,
        date_from: dateFrom || undefined,
        date_to: dateTo || undefined,
      });
      setRows(data);
    } finally {
      setLoading(false);
    }
  }, [guardFilter, dateFrom, dateTo]);

  useEffect(() => { load(); }, [load]);

  const csvUrl = historyCSVUrl({
    guard_id: guardFilter,
    date_from: dateFrom || undefined,
    date_to: dateTo || undefined,
  });

  return (
    <div className="space-y-4 fade-in">
      {/* Filters */}
      <div className="card space-y-3">
        <div className="flex gap-2">
          <select
            value={guardFilter ?? ""}
            onChange={(e) => setGuardFilter(e.target.value ? Number(e.target.value) : undefined)}
            className="input flex-1 text-sm"
          >
            <option value="">כל השומרים</option>
            {absences.map((a) => (
              <option key={a.guard_id} value={a.guard_id}>{a.name}</option>
            ))}
          </select>
          <a
            href={csvUrl}
            download
            className="btn-ghost text-xs px-3 py-2 shrink-0 flex items-center gap-1"
          >
            📥 CSV
          </a>
        </div>
        <div className="grid grid-cols-2 gap-2 min-w-0">
          <DateInput label="מתאריך" value={dateFrom} onChange={setDateFrom} />
          <DateInput label="עד תאריך" value={dateTo} onChange={setDateTo} />
        </div>
      </div>

      {/* Table */}
      <div className="card p-0 rounded-xl overflow-hidden">
        {loading ? (
          <SkeletonTableRows />
        ) : rows.length === 0 ? (
          <p className="text-center text-text-dim py-6">אין רשומות</p>
        ) : (
          <div style={{ overflowX: "auto", overflowY: "auto", maxHeight: "60vh" }}>
            <table className="text-sm w-full" style={{ minWidth: "520px" }}>
              <thead>
                <tr>
                  {["שם","סיבה","תאריך","יציאה","חזרה","משך"].map((h) => (
                    <th
                      key={h}
                      className="text-right px-3 py-2 font-semibold text-text-muted whitespace-nowrap border-b border-bg-border bg-bg-base"
                      style={{ position: "sticky", top: 0, zIndex: 10 }}
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.id} className="border-b border-bg-border/50 hover:bg-bg-base/50">
                    <td className="px-3 py-2 font-medium text-text whitespace-nowrap">{r.name}</td>
                    <td className="px-3 py-2 text-text-muted whitespace-nowrap">{r.reason || "—"}</td>
                    <td className="px-3 py-2 text-text-muted tabular-nums whitespace-nowrap">{fmtDate(r.left_at)}</td>
                    <td className="px-3 py-2 text-text-muted tabular-nums whitespace-nowrap">{fmtTime(r.left_at)}</td>
                    <td className="px-3 py-2 text-text-muted tabular-nums whitespace-nowrap">
                      {r.returned_at ? fmtTime(r.returned_at) : <span className="text-warning">בחוץ</span>}
                    </td>
                    <td className="px-3 py-2 text-text-muted tabular-nums whitespace-nowrap">
                      {r.duration_min != null ? fmtDuration(r.duration_min) : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}


// ── Copy Names Button ─────────────────────────────────────────────────────────
function CopyNamesButton({ names }: { names: string[] }) {
  const [copied, setCopied] = useState(false);
  if (!names.length) return null;
  const handleCopy = () => {
    navigator.clipboard.writeText(names.join(", "));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };
  return (
    <button
      onClick={handleCopy}
      className="text-xs text-text-dim hover:text-primary border border-bg-border hover:border-primary/40
                 bg-bg-base px-2 py-0.5 rounded-lg transition-colors"
      title="העתק שמות"
    >
      {copied ? "✓ הועתק" : "📋 העתק שמות"}
    </button>
  );
}


export default function AbsencesTab() {
  const [absences, setAbsences] = useState<AbsenceStatus[]>([]);
  const [rotationConfig, setRotationConfig] = useState<RotationConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<number | null>(null);
  const [bulkBusy, setBulkBusy] = useState(false);
  const [error, setError] = useState("");
  const [view, setView] = useState<"now" | "history">("now");
  const [search, setSearch] = useState("");
  const readOnly = useReadOnly();
  const [pendingLeave, setPendingLeave] = useState<{ id: number; name: string } | null>(null);
  const [pendingBulkLeave, setPendingBulkLeave] = useState(false);
  const [pendingRotationLeave, setPendingRotationLeave] = useState(false);
  const [settings, setSettings] = useState<Settings>({ alert_minutes: null, alert_thresholds: [] });
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [outFilter, setOutFilter] = useState<"all" | "temp" | "absent">("all");
  const ABSENT_REASONS = ["מחלה", "חופשה"];
  // tick to re-evaluate alert state every 30s
  const [, setTick] = useState(0);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const load = useCallback(async () => {
    try {
      const [data, cfg, rot] = await Promise.all([getAbsences(), getSettings(), getRotation().catch(() => null)]);
      setAbsences(data);
      setSettings(cfg);
      setRotationConfig(rot);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
    timerRef.current = setInterval(() => setTick((t) => t + 1), 30000);
    return () => { if (timerRef.current) clearInterval(timerRef.current); };
  }, [load]);

  function toggleSelect(id: number) {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  }

  function clearSelection() {
    setSelectedIds(new Set());
  }

  async function doAction(fn: () => Promise<unknown>, guardId: number) {
    setBusy(guardId);
    setError("");
    try {
      await fn();
      await load();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setBusy(null);
    }
  }

  async function doBulkReturn() {
    const ids = [...selectedIds].filter((id) => absences.find((a) => a.guard_id === id && a.is_out));
    if (!ids.length) return;
    setBulkBusy(true);
    setError("");
    try {
      await Promise.all(ids.map((id) => markReturn(id)));
      clearSelection();
      await load();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setBulkBusy(false);
    }
  }

  async function doRotationLeave(ids: number[], reason: string | undefined) {
    if (!ids.length) return;
    setBulkBusy(true);
    setError("");
    try {
      await Promise.all(ids.map((id) => markLeave(id, reason)));
      await load();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setBulkBusy(false);
    }
  }

  async function doBulkLeave(reason: string | undefined) {
    const ids = [...selectedIds].filter((id) => absences.find((a) => a.guard_id === id && !a.is_out));
    if (!ids.length) return;
    setBulkBusy(true);
    setError("");
    try {
      await Promise.all(ids.map((id) => markLeave(id, reason)));
      clearSelection();
      await load();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setBulkBusy(false);
    }
  }

  // Compute names in today's active rotation slot
  const rotationNamesNow = (() => {
    if (!rotationConfig) return new Set<string>();
    const periods = computePeriods(rotationConfig, 9);
    const active = periods.find((p) => p.isActive);
    if (!active) return new Set<string>();
    const names: string[] = [];
    for (const role of rotationConfig.roles) {
      const slotIdx = active.slotIndex % role.slots.length;
      names.push(...(role.slots[slotIdx] ?? []));
    }
    return new Set(names);
  })();

  const tempOut = absences.filter(
    (a) => a.is_out && (!a.reason || !ABSENT_REASONS.includes(a.reason))
  );
  
  const absentOut = absences.filter(
    (a) => a.is_out && a.reason && ABSENT_REASONS.includes(a.reason)
  );
  
  const out =
    outFilter === "temp"
      ? tempOut
      : outFilter === "absent"
      ? absentOut
      : [...tempOut, ...absentOut];
  const inside = absences.filter((a) => !a.is_out);
  const filteredInside = search
    ? inside.filter((a) => a.name.includes(search))
    : inside;
  const insideInRotation = filteredInside.filter((a) => rotationNamesNow.has(a.name));
  const insideNotInRotation = filteredInside.filter((a) => !rotationNamesNow.has(a.name));

  const alertOut = out.filter((a) => a.left_at && getAlertLevel(a.left_at, settings.alert_thresholds) !== null);

  // derive bulk action counts
  const selectedOutCount = [...selectedIds].filter((id) => out.some((a) => a.guard_id === id)).length;
  const selectedInCount  = [...selectedIds].filter((id) => inside.some((a) => a.guard_id === id)).length;
  const hasSelection = selectedIds.size > 0;

  if (loading) return <SkeletonAbsenceCards />;

  return (
    <div className="space-y-4 fade-in">
      {/* Sub-tab toggle */}
      <div className="flex gap-1 bg-bg-base rounded-xl p-1">
        {(["now", "history"] as const).map((v) => (
          <button
            key={v}
            onClick={() => setView(v)}
            className={`flex-1 py-2 rounded-lg text-sm font-semibold transition-colors
              ${view === v ? "bg-bg-card text-text shadow-sm" : "text-text-dim hover:text-text"}`}
          >
            {v === "now" ? "🏠 נוכחות" : "📋 היסטוריה"}
          </button>
        ))}
      </div>

      {view === "history" ? (
        <HistoryView absences={absences} />
      ) : (
        <>
          {error && (
            <div className="card border-danger/40 bg-danger/10 text-danger text-sm">{error}</div>
          )}

          {/* Alert banner */}
          {alertOut.length > 0 && (
            <div className="card border-danger/40 bg-danger/10 slide-in">
              <p className="text-danger text-sm font-semibold">
                ⚠️ {alertOut.map((a) => a.name).join(", ")} — חרגו מסף ההתראה!
              </p>
            </div>
          )}

          {/* ── מחוץ למסגרת ── */}
          <div className="card">
            <div className="flex items-center justify-between mb-3">
              <h2 className="font-bold text-base flex items-center gap-2">
                <span>🚪</span> מחוץ למסגרת
                {out.length > 0 && (
                  <span className="bg-warning/20 text-warning text-xs font-bold px-2 py-0.5 rounded-full">
                    {out.length}
                  </span>
                )}
              </h2>
              <CopyNamesButton names={out.map((a) => a.name)} />
            </div>
            <div className="flex gap-1 mb-3">
              <button
                onClick={() => setOutFilter("all")}
                className={`px-3 py-1 text-xs rounded-md ${
                  outFilter === "all"
                    ? "bg-bg-card text-text shadow"
                    : "text-text-dim"
                }`}
              >
                הכל
              </button>
              <button
                onClick={() => setOutFilter("temp")}
                className={`px-3 py-1 text-xs rounded-md ${
                  outFilter === "temp"
                    ? "bg-bg-card text-text shadow"
                    : "text-text-dim"
                }`}
              >
                🚪 יצאו זמנית
              </button>
              <button
                onClick={() => setOutFilter("absent")}
                className={`px-3 py-1 text-xs rounded-md ${
                  outFilter === "absent"
                    ? "bg-bg-card text-text shadow"
                    : "text-text-dim"
                }`}
              >
                🏖 נעדרים
              </button>
            </div>  
            {out.length === 0 ? (
              <p className="text-text-dim text-sm text-center py-4">אין יוצאים כרגע</p>
            ) : (
              <ul className="space-y-3 max-h-80 overflow-y-auto pr-1">
                {out.map((a) => {
                  const alertLevel = a.left_at ? getAlertLevel(a.left_at, settings.alert_thresholds) : null;
                  const checked = selectedIds.has(a.guard_id);
                  return (
                    <li
                      key={a.guard_id}
                      className={`flex items-center gap-2 rounded-xl px-3 py-3 slide-in
                        ${alertLevel ? LEVEL_ROW[alertLevel] : "bg-bg-base"}
                        ${checked ? "ring-2 ring-primary/50" : ""}`}
                    >
                      <input
                        type="checkbox"
                        checked={checked}
                        onChange={() => toggleSelect(a.guard_id)}
                        className="w-4 h-4 accent-primary shrink-0"
                      />
                      <div className="flex flex-col gap-0.5 min-w-0 flex-1">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="font-semibold text-text">{a.name}</span>
                          {a.reason && (
                            <span className="text-xs bg-primary/20 text-primary px-1.5 py-0.5 rounded-full">
                              {a.reason}
                            </span>
                          )}
                          {a.total_exits > 0 && (
                            <span className="text-xs bg-bg-border text-text-muted px-1.5 py-0.5 rounded-full">
                              {a.total_exits} יציאות
                            </span>
                          )}
                        </div>
                        {a.left_at && <Clock leftAt={a.left_at} level={alertLevel} />}
                      </div>
                      {!readOnly && (
                        <div className="flex gap-2 shrink-0">
                          <button
                            className="btn-ghost text-xs px-2 py-1"
                            disabled={busy === a.guard_id}
                            onClick={() => doAction(() => resetAbsence(a.guard_id), a.guard_id)}
                          >
                            🔄
                          </button>
                          <button
                            className="btn-primary text-xs px-3 py-1.5"
                            disabled={busy === a.guard_id}
                            onClick={() => doAction(() => markReturn(a.guard_id), a.guard_id)}
                          >
                            חזר ✅
                          </button>
                        </div>
                      )}
                    </li>
                  );
                })}
              </ul>
            )}
          </div>

          {/* ── במסגרת ── */}
          <div className="card">
            <div className="flex items-center justify-between mb-3">
              <h2 className="font-bold text-base flex items-center gap-2">
                <span>🏠</span> במסגרת
                <span className="bg-success/20 text-success text-xs font-bold px-2 py-0.5 rounded-full">
                  {inside.length}
                </span>
              </h2>
              <CopyNamesButton names={filteredInside.map((a) => a.name)} />
            </div>

            {/* Search */}
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="חיפוש לפי שם..."
              className="input text-sm mb-3"
            />

            {filteredInside.length === 0 ? (
              <p className="text-text-dim text-sm text-center py-4">
                {search ? "לא נמצאו תוצאות" : "אין שומרים במסגרת"}
              </p>
            ) : (
              <div className="space-y-3 max-h-96 overflow-y-auto">
                {insideInRotation.length > 0 && (
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <p className="text-xs font-semibold text-primary flex items-center gap-1">
                        <span>🔄</span> בסבב עכשיו
                        <span className="bg-primary/20 text-primary px-1.5 py-0.5 rounded-full">
                          {insideInRotation.length}
                        </span>
                      </p>
                      {!readOnly && (
                        <button
                          className="btn-danger text-xs px-2 py-1"
                          disabled={bulkBusy}
                          onClick={() => setPendingRotationLeave(true)}
                        >
                          כולם יצאו 🚪
                        </button>
                      )}
                    </div>
                    <ul className="space-y-2">
                      {insideInRotation.map((a) => {
                        const checked = selectedIds.has(a.guard_id);
                        return (
                          <li
                            key={a.guard_id}
                            className={`flex items-center gap-2 bg-primary/8 border border-primary/20 rounded-xl px-3 py-2
                              ${checked ? "ring-2 ring-primary/50" : ""}`}
                          >
                            <input
                              type="checkbox"
                              checked={checked}
                              onChange={() => toggleSelect(a.guard_id)}
                              className="w-4 h-4 accent-primary shrink-0"
                            />
                            <div className="flex items-center gap-2 flex-1 min-w-0">
                              <span className="font-medium text-text">{a.name}</span>
                              {a.total_exits > 0 && (
                                <span className="text-xs bg-bg-border text-text-muted px-1.5 py-0.5 rounded-full">
                                  {a.total_exits} יציאות
                                </span>
                              )}
                            </div>
                            {!readOnly && (
                              <button
                                className="btn-danger text-xs px-3 py-1.5 shrink-0"
                                disabled={busy === a.guard_id}
                                onClick={() => setPendingLeave({ id: a.guard_id, name: a.name })}
                              >
                                יצא 🚪
                              </button>
                            )}
                          </li>
                        );
                      })}
                    </ul>
                  </div>
                )}
                {insideNotInRotation.length > 0 && (
                  <div>
                    {insideInRotation.length > 0 && (
                      <p className="text-xs font-semibold text-text-muted mb-2">שאר הכוח</p>
                    )}
                    <ul className="space-y-2">
                      {insideNotInRotation.map((a) => {
                        const checked = selectedIds.has(a.guard_id);
                        return (
                          <li
                            key={a.guard_id}
                            className={`flex items-center gap-2 bg-bg-base rounded-xl px-3 py-2
                              ${checked ? "ring-2 ring-primary/50" : ""}`}
                          >
                            <input
                              type="checkbox"
                              checked={checked}
                              onChange={() => toggleSelect(a.guard_id)}
                              className="w-4 h-4 accent-primary shrink-0"
                            />
                            <div className="flex items-center gap-2 flex-1 min-w-0">
                              <span className="font-medium text-text">{a.name}</span>
                              {a.total_exits > 0 && (
                                <span className="text-xs bg-bg-border text-text-muted px-1.5 py-0.5 rounded-full">
                                  {a.total_exits} יציאות
                                </span>
                              )}
                            </div>
                            {!readOnly && (
                              <button
                                className="btn-danger text-xs px-3 py-1.5 shrink-0"
                                disabled={busy === a.guard_id}
                                onClick={() => setPendingLeave({ id: a.guard_id, name: a.name })}
                              >
                                יצא 🚪
                              </button>
                            )}
                          </li>
                        );
                      })}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </div>
        </>
      )}

      {/* ── Bulk action bar — hidden for viewers ── */}
      {hasSelection && view === "now" && !readOnly && (
        <div
          className="fixed bottom-16 inset-x-0 z-40 flex justify-center px-4 pointer-events-none"
          dir="rtl"
        >
          <div className="bg-bg-card border border-bg-border rounded-2xl shadow-2xl px-4 py-3 flex items-center gap-3 pointer-events-auto slide-in">
            <span className="text-sm font-bold text-text">
              נבחרו {selectedIds.size}
            </span>
            <div className="w-px h-5 bg-bg-border" />
            {selectedInCount > 0 && (
              <button
                className="btn-danger text-xs px-3 py-1.5"
                disabled={bulkBusy}
                onClick={() => setPendingBulkLeave(true)}
              >
                יצאו ({selectedInCount}) 🚪
              </button>
            )}
            {selectedOutCount > 0 && (
              <button
                className="btn-primary text-xs px-3 py-1.5"
                disabled={bulkBusy}
                onClick={doBulkReturn}
              >
                חזרו ({selectedOutCount}) ✅
              </button>
            )}
            <button
              className="text-text-dim hover:text-text text-sm px-1"
              onClick={clearSelection}
            >
              ✕
            </button>
          </div>
        </div>
      )}

      {/* Single Reason Sheet */}
      {pendingLeave && (
        <ReasonSheet
          name={pendingLeave.name}
          onSelect={(reason) => {
            const id = pendingLeave.id;
            setPendingLeave(null);
            doAction(() => markLeave(id, reason), id);
          }}
          onCancel={() => setPendingLeave(null)}
        />
      )}

      {/* Bulk Reason Sheet */}
      {pendingBulkLeave && (
        <ReasonSheet
          name={`${selectedInCount} אנשים`}
          onSelect={(reason) => {
            setPendingBulkLeave(false);
            doBulkLeave(reason);
          }}
          onCancel={() => setPendingBulkLeave(false)}
        />
      )}

      {/* Rotation Bulk Leave Sheet */}
      {pendingRotationLeave && (
        <ReasonSheet
          name={`${insideInRotation.length} אנשים בסבב`}
          onSelect={(reason) => {
            const ids = insideInRotation.map((a) => a.guard_id);
            setPendingRotationLeave(false);
            doRotationLeave(ids, reason);
          }}
          onCancel={() => setPendingRotationLeave(false)}
        />
      )}
    </div>
  );
}
