import { useCallback, useEffect, useRef, useState } from "react";
import Clock from "./Clock";
import {
  getAbsences, markLeave, markReturn, resetAbsence,
  getHistory, getSettings, historyCSVUrl,
} from "./api";
import type { AbsenceStatus, AbsenceHistory, Settings } from "./types";


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

function isOverAlert(leftAt: string, alertMin: number | null): boolean {
  if (!alertMin) return false;
  const diffMin = (Date.now() - new Date(leftAt.endsWith("Z") ? leftAt : leftAt + "Z").getTime()) / 60000;
  return diffMin >= alertMin;
}

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

// ── Floating Label Date Input ─────────────────────────────────────────────────
function DateInput({ label, value, onChange }: { label: string; value: string; onChange: (v: string) => void }) {
  return (
    <div className="relative flex-1">
      <input
        type="date"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="input text-sm w-full pt-5 pb-1"
      />
      <span className={`absolute right-3 pointer-events-none transition-all duration-150 text-text-muted
        ${value ? "top-1 text-[10px]" : "top-1/2 -translate-y-1/2 text-sm"}`}>
        {label}
      </span>
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
        <div className="flex gap-2">
          <DateInput label="מתאריך" value={dateFrom} onChange={setDateFrom} />
          <DateInput label="עד תאריך" value={dateTo} onChange={setDateTo} />
        </div>
      </div>

      {/* Table */}
      <div className="card p-0 overflow-hidden">
        {loading ? (
          <p className="text-center text-text-dim py-6">טוען...</p>
        ) : rows.length === 0 ? (
          <p className="text-center text-text-dim py-6">אין רשומות</p>
        ) : (
          <div className="overflow-auto max-h-[60vh]">
            <table className="text-sm" style={{ minWidth: "520px", width: "100%" }}>
              <thead className="sticky top-0 z-10">
                <tr className="border-b border-bg-border bg-bg-base">
                  <th className="text-right px-3 py-2 font-semibold text-text-muted whitespace-nowrap">שם</th>
                  <th className="text-right px-3 py-2 font-semibold text-text-muted whitespace-nowrap">סיבה</th>
                  <th className="text-right px-3 py-2 font-semibold text-text-muted whitespace-nowrap">תאריך</th>
                  <th className="text-right px-3 py-2 font-semibold text-text-muted whitespace-nowrap">יציאה</th>
                  <th className="text-right px-3 py-2 font-semibold text-text-muted whitespace-nowrap">חזרה</th>
                  <th className="text-right px-3 py-2 font-semibold text-text-muted whitespace-nowrap">משך</th>
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

// ── Main ──────────────────────────────────────────────────────────────────────
export default function AbsencesTab() {
  const [absences, setAbsences] = useState<AbsenceStatus[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<number | null>(null);
  const [error, setError] = useState("");
  const [view, setView] = useState<"now" | "history">("now");
  const [search, setSearch] = useState("");
  const [pendingLeave, setPendingLeave] = useState<{ id: number; name: string } | null>(null);
  const [settings, setSettings] = useState<Settings>({ alert_minutes: null });
  // tick to re-evaluate alert state every 30s
  const [, setTick] = useState(0);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const load = useCallback(async () => {
    try {
      const [data, cfg] = await Promise.all([getAbsences(), getSettings()]);
      setAbsences(data);
      setSettings(cfg);
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

  const out = absences.filter((a) => a.is_out);
  const inside = absences.filter((a) => !a.is_out);
  const filteredInside = search
    ? inside.filter((a) => a.name.includes(search))
    : inside;

  const alertOut = out.filter((a) => a.left_at && isOverAlert(a.left_at, settings.alert_minutes));

  if (loading) return <p className="text-center text-text-dim mt-10">טוען...</p>;

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
                ⚠️ {alertOut.map((a) => a.name).join(", ")} — מעל {settings.alert_minutes} דק' בחוץ!
              </p>
            </div>
          )}

          {/* ── מחוץ למסגרת ── */}
          <div className="card">
            <h2 className="font-bold text-base mb-3 flex items-center gap-2">
              <span>🚪</span> מחוץ למסגרת
              {out.length > 0 && (
                <span className="bg-warning/20 text-warning text-xs font-bold px-2 py-0.5 rounded-full">
                  {out.length}
                </span>
              )}
            </h2>
            {out.length === 0 ? (
              <p className="text-text-dim text-sm text-center py-4">אין יוצאים כרגע</p>
            ) : (
              <ul className="space-y-3">
                {out.map((a) => {
                  const alert = a.left_at ? isOverAlert(a.left_at, settings.alert_minutes) : false;
                  return (
                    <li
                      key={a.guard_id}
                      className={`flex items-center justify-between gap-2 rounded-xl px-3 py-3 slide-in
                        ${alert ? "bg-danger/10 border border-danger/30" : "bg-bg-base"}`}
                    >
                      <div className="flex flex-col gap-0.5 min-w-0">
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
                        {a.left_at && <Clock leftAt={a.left_at} alert={alert} />}
                      </div>
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
              <ul className="space-y-2 max-h-96 overflow-y-auto">
                {filteredInside.map((a) => (
                  <li
                    key={a.guard_id}
                    className="flex items-center justify-between gap-2 bg-bg-base rounded-xl px-3 py-2"
                  >
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-text">{a.name}</span>
                      {a.total_exits > 0 && (
                        <span className="text-xs bg-bg-border text-text-muted px-1.5 py-0.5 rounded-full">
                          {a.total_exits} יציאות
                        </span>
                      )}
                    </div>
                    <button
                      className="btn-danger text-xs px-3 py-1.5"
                      disabled={busy === a.guard_id}
                      onClick={() => setPendingLeave({ id: a.guard_id, name: a.name })}
                    >
                      יצא 🚪
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </>
      )}

      {/* Reason Sheet */}
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
    </div>
  );
}
