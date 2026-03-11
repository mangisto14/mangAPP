import { useEffect, useState } from "react";
import { ChevronRight, ChevronLeft, Pencil } from "lucide-react";
import { getRotation } from "./api";
import type { RotationConfig, RotationPeriod } from "./types";
import EditRotationModal from "./EditRotationModal";

// ── Helpers ──────────────────────────────────────────────────────────────────

function addDays(d: Date, n: number): Date {
  const r = new Date(d);
  r.setDate(r.getDate() + n);
  return r;
}

function fmtShort(d: Date): string {
  return `${d.getDate()}/${d.getMonth() + 1}`;
}

/** Build all periods for a given week offset (0 = current week window) */
function buildPeriods(config: RotationConfig, weekOffset: number): RotationPeriod[] {
  const { start_date, period_days } = config;
  const origin = new Date(start_date + "T00:00:00");
  const now = new Date();

  // Window: 7 periods per "page" (configurable), shifted by weekOffset
  const windowSize = 7;
  const windowStart = addDays(now, weekOffset * windowSize);

  // Find the first period that overlaps our window
  const elapsedDays = Math.floor((windowStart.getTime() - origin.getTime()) / 86400000);
  const firstPeriodNum = Math.max(0, Math.floor(elapsedDays / period_days));

  const periods: RotationPeriod[] = [];
  for (let i = firstPeriodNum; i < firstPeriodNum + windowSize; i++) {
    const start = addDays(origin, i * period_days);
    const end = addDays(start, period_days);
    const slotIndex = i % 3;
    const isActive = now >= start && now < end;
    periods.push({
      start,
      end,
      slotIndex,
      label: `${fmtShort(start)}-${fmtShort(end)}`,
      isActive,
    });
  }
  return periods;
}

// ── Component ─────────────────────────────────────────────────────────────────

export default function RotationTab() {
  const [config, setConfig] = useState<RotationConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [weekOffset, setWeekOffset] = useState(0);
  const [showEdit, setShowEdit] = useState(false);

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

  const periods = buildPeriods(config, weekOffset);
  const activePeriod = periods.find((p) => p.isActive);

  // Window label
  const windowLabel = `${fmtShort(periods[0].start)} – ${fmtShort(periods[periods.length - 1].end)}`;

  const SLOT_COLORS = [
    "bg-primary/10 border-primary/25 text-primary-light",
    "bg-success/10 border-success/25 text-success",
    "bg-warning/10 border-warning/25 text-warning",
  ];

  return (
    <div className="fade-in space-y-4">
      {/* Header toolbar */}
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <button
            onClick={() => setWeekOffset((o) => o - 1)}
            className="p-2 rounded-xl bg-bg-card border border-bg-border hover:border-primary/40
                       text-text-dim hover:text-text transition-colors"
          >
            <ChevronRight size={18} />
          </button>
          <span className="text-sm font-semibold text-text-muted min-w-[110px] text-center">
            {windowLabel}
          </span>
          <button
            onClick={() => setWeekOffset((o) => o + 1)}
            className="p-2 rounded-xl bg-bg-card border border-bg-border hover:border-primary/40
                       text-text-dim hover:text-text transition-colors"
          >
            <ChevronLeft size={18} />
          </button>
        </div>

        <div className="flex items-center gap-2">
          {weekOffset !== 0 && (
            <button
              onClick={() => setWeekOffset(0)}
              className="text-xs text-primary-light bg-primary/10 border border-primary/20
                         px-3 py-1.5 rounded-full font-semibold"
            >
              עכשיו
            </button>
          )}
          <button
            onClick={() => setShowEdit(true)}
            className="flex items-center gap-1.5 bg-bg-card border border-bg-border px-3 py-1.5
                       rounded-xl text-sm font-semibold text-text-dim hover:text-text
                       hover:border-primary/40 transition-all"
          >
            <Pencil size={14} />
            ערוך
          </button>
        </div>
      </div>

      {/* Active period badge */}
      {activePeriod && (
        <div className="text-xs font-semibold text-primary-light bg-primary/10 border border-primary/20
                        px-3 py-1.5 rounded-xl inline-flex items-center gap-2">
          <span className="w-2 h-2 bg-primary rounded-full animate-pulse" />
          תקופה פעילה: {activePeriod.label} · קבוצה {activePeriod.slotIndex + 1}
        </div>
      )}

      {/* Legend */}
      <div className="flex gap-3 flex-wrap">
        {[0, 1, 2].map((i) => (
          <span key={i} className={`text-xs font-semibold px-3 py-1 rounded-full border ${SLOT_COLORS[i]}`}>
            קבוצה {i + 1}
          </span>
        ))}
      </div>

      {/* Rotation table — horizontal scroll */}
      <div className="overflow-x-auto -mx-4 px-4">
        <table className="w-full text-sm border-collapse" style={{ minWidth: "600px" }}>
          <thead>
            <tr>
              <th className="text-right py-2 px-3 text-text-dim font-semibold text-xs w-20 sticky right-0
                             bg-bg-deep z-10">
                תפקיד
              </th>
              {periods.map((p, pi) => (
                <th
                  key={pi}
                  className={`text-center py-2 px-2 text-xs font-semibold whitespace-nowrap
                    ${p.isActive
                      ? "text-primary bg-primary/10 rounded-t-lg border-t border-x border-primary/25"
                      : "text-text-dim"
                    }`}
                >
                  {p.label}
                  <div className={`text-[10px] mt-0.5 font-normal ${p.isActive ? "text-primary-light" : "text-text-dim/60"}`}>
                    קב׳ {p.slotIndex + 1}
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
                {periods.map((p, pi) => {
                  const names = role.slots[p.slotIndex] ?? [];
                  return (
                    <td
                      key={pi}
                      className={`py-2 px-2 text-center align-top
                        ${p.isActive
                          ? "bg-primary/5 border-x border-primary/25"
                          : ""
                        }`}
                    >
                      {names.length === 0 ? (
                        <span className="text-text-dim/40 text-xs">—</span>
                      ) : (
                        <div className="space-y-0.5">
                          {names.map((name) => (
                            <div
                              key={name}
                              className={`text-xs px-1.5 py-0.5 rounded-lg border font-medium
                                ${SLOT_COLORS[p.slotIndex]}`}
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

      {/* Edit modal */}
      {showEdit && (
        <EditRotationModal
          config={config}
          onClose={() => setShowEdit(false)}
          onSaved={() => { setShowEdit(false); load(); }}
        />
      )}
    </div>
  );
}
