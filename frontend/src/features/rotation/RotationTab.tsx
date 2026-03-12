import { useEffect, useState } from "react";
import { Pencil, Settings } from "lucide-react";
import { getRotation, updateRotationSlots } from "./api";
import type { RotationConfig } from "./types";
import EditRotationModal from "./EditRotationModal";

// ── Helpers ───────────────────────────────────────────────────────────────────

function addDays(d: Date, n: number): Date {
  const r = new Date(d);
  r.setDate(r.getDate() + n);
  return r;
}

function fmtShort(d: Date): string {
  return `${d.getDate()}/${d.getMonth() + 1}`;
}

const PERIOD_CONFIG = [
  { label: "א-ג", startDow: 0, days: 2 },
  { label: "ג-ה", startDow: 2, days: 2 },
  { label: "ו-א", startDow: 5, days: 2 },
] as const;

// צבעים לפי סוג תקופה: א-ג=כחול, ג-ה=כתום, ו-א=ירוק
const PERIOD_COLORS = [
  "bg-primary/10 border-primary/25 text-primary-light",
  "bg-warning/10 border-warning/25 text-warning",
  "bg-success/10 border-success/25 text-success",
];

interface Period {
  start: Date;
  end: Date;
  slotIndex: number;   // 0–8 → maps directly to role.slots[slotIndex]
  label: string;       // "08/3-10/3"
  periodLabel: string; // "א-ג" | "ג-ה" | "ו-א"
  periodIndex: number; // 0 | 1 | 2  (index in PERIOD_CONFIG → color)
  isActive: boolean;
}

/**
 * Compute the 9 periods of the current 3-week cycle.
 * slotIndex is simply the position within the cycle (0–8), with no modular rotation.
 */
function computePeriods(startDate: string): Period[] {
  const origin = new Date(startDate + "T00:00:00");
  const now = new Date();

  // Cycle anchor = first Sunday on/after origin
  const originDow = origin.getDay();
  const daysToSunday = originDow === 0 ? 0 : 7 - originDow;
  const anchor = addDays(origin, daysToSunday);

  // Which 3-week cycle (21 days) contains today?
  const daysSinceAnchor = Math.floor((now.getTime() - anchor.getTime()) / 86400000);
  const cycleNumber = Math.max(0, Math.floor(daysSinceAnchor / 21));
  const cycleStart = addDays(anchor, cycleNumber * 21);

  return Array.from({ length: 3 }, (_, w) =>
    PERIOD_CONFIG.map((pc, p) => {
      const start = addDays(addDays(cycleStart, w * 7), pc.startDow);
      const end = addDays(start, 2);
      return {
        start,
        end,
        slotIndex: w * 3 + p,
        label: `${fmtShort(start)}-${fmtShort(end)}`,
        periodLabel: pc.label,
        periodIndex: p,
        isActive: now >= start && now < end,
      };
    })
  ).flat();
}

// ── EditPeriodModal ────────────────────────────────────────────────────────────

interface EditPeriodProps {
  config: RotationConfig;
  period: Period;
  onClose: () => void;
  onSaved: () => void;
}

function EditPeriodModal({ config, period, onClose, onSaved }: EditPeriodProps) {
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
        const newSlots = Array.from({ length: 9 }, (_, i) => role.slots[i] ?? []);
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
            <div key={role.id} className="flex items-center gap-3">
              <label className="text-sm font-bold text-text w-20 shrink-0 text-right">
                {role.name}
              </label>
              <input
                value={values[role.id] ?? ""}
                onChange={(e) => setValues((prev) => ({ ...prev, [role.id]: e.target.value }))}
                placeholder="שם1, שם2, שם3"
                className="input text-sm flex-1"
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

// ── RotationTab ───────────────────────────────────────────────────────────────

export default function RotationTab() {
  const [config, setConfig] = useState<RotationConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [editSlot, setEditSlot] = useState<number | null>(null);
  const [showSettings, setShowSettings] = useState(false);

  const load = async () => {
    setLoading(true);
    setError("");
    try {
      setConfig(await getRotation());
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  if (loading) return <div className="fade-in text-center text-text-dim py-20">טוען...</div>;
  if (error || !config) return <div className="fade-in card border-danger/30 text-danger">{error || "שגיאה"}</div>;

  const periods = computePeriods(config.start_date);
  const activePeriod = periods.find((p) => p.isActive);

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

      {/* Legend */}
      <div className="flex gap-3 flex-wrap">
        {PERIOD_CONFIG.map((pc, i) => (
          <span key={i} className={`text-xs font-semibold px-3 py-1 rounded-full border ${PERIOD_COLORS[i]}`}>
            {pc.label}
          </span>
        ))}
      </div>

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
                          {names.map((name) => (
                            <div
                              key={name}
                              className={`text-xs px-1.5 py-0.5 rounded-lg border font-medium
                                ${PERIOD_COLORS[p.periodIndex]}`}
                            >
                              {name}
                            </div>
                          ))}
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
          onClose={() => setEditSlot(null)}
          onSaved={() => { setEditSlot(null); load(); }}
        />
      )}

      {/* Settings modal (role management + start date) */}
      {showSettings && (
        <EditRotationModal
          config={config}
          onClose={() => setShowSettings(false)}
          onSaved={() => { setShowSettings(false); load(); }}
        />
      )}
    </div>
  );
}
