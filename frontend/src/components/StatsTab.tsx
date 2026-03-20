import { useEffect, useState } from "react";
import { AlertTriangle, Download, ChevronDown, ChevronUp } from "lucide-react";
import { getStats } from "../api";
import { getShifts } from "../api";
import type { Stats, Shift } from "../types";
import { SkeletonStatCards } from "./Skeleton";

const MEDALS = ["🥇", "🥈", "🥉"];
const RANK_BG = [
  "border-yellow-500/30 bg-yellow-500/5",
  "border-slate-400/30 bg-slate-400/5",
  "border-orange-700/30 bg-orange-700/5",
];

const HE_MONTHS = ["ינ׳","פב׳","מר׳","אפ׳","מי׳","יו׳","יל׳","אג׳","ספ׳","אוק׳","נו׳","דצ׳"];

// ── Weekly / Monthly bucket helpers ──────────────────────────────────────────

function getWeeklyBuckets(shifts: Shift[], n = 8) {
  const now = new Date();
  // Align to start of current week (Sunday)
  const startOfThisWeek = new Date(now);
  startOfThisWeek.setDate(now.getDate() - now.getDay());
  startOfThisWeek.setHours(0, 0, 0, 0);

  return Array.from({ length: n }, (_, i) => {
    const weekStart = new Date(startOfThisWeek);
    weekStart.setDate(startOfThisWeek.getDate() - (n - 1 - i) * 7);
    const weekEnd = new Date(weekStart);
    weekEnd.setDate(weekStart.getDate() + 7);
    const label = `${weekStart.getDate()}/${weekStart.getMonth() + 1}`;
    const count = shifts.filter((s) => {
      const d = new Date(s.start_time);
      return d >= weekStart && d < weekEnd;
    }).length;
    return { label, count };
  });
}

function getMonthlyBuckets(shifts: Shift[], n = 6) {
  const now = new Date();
  return Array.from({ length: n }, (_, i) => {
    const offset = n - 1 - i;
    const month = new Date(now.getFullYear(), now.getMonth() - offset, 1);
    const nextMonth = new Date(now.getFullYear(), now.getMonth() - offset + 1, 1);
    const label = HE_MONTHS[month.getMonth()];
    const count = shifts.filter((s) => {
      const d = new Date(s.start_time);
      return d >= month && d < nextMonth;
    }).length;
    return { label, count };
  });
}

// ── Monthly CSV export ────────────────────────────────────────────────────────

function exportMonthlyReport(shifts: Shift[]) {
  // One row per guard per shift, sorted by date
  const sorted = [...shifts].sort(
    (a, b) => new Date(a.start_time).getTime() - new Date(b.start_time).getTime()
  );

  const HE_DAY: Record<string, string> = {
    Sunday: "ראשון", Monday: "שני", Tuesday: "שלישי", Wednesday: "רביעי",
    Thursday: "חמישי", Friday: "שישי", Saturday: "שבת",
  };

  const rows = ["חודש,יום,תאריך,שם,שעות"];
  for (const s of sorted) {
    const d = new Date(s.start_time);
    const month = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
    const dayName = HE_DAY[d.toLocaleDateString("en-US", { weekday: "long" })] ?? "";
    const date = `${String(d.getDate()).padStart(2, "0")}/${String(d.getMonth() + 1).padStart(2, "0")}/${d.getFullYear()}`;
    const hrs = (new Date(s.end_time).getTime() - new Date(s.start_time).getTime()) / 3_600_000;
    for (const name of s.names) {
      rows.push(`${month},${dayName},${date},${name},${hrs.toFixed(1)}`);
    }
  }

  const blob = new Blob(["\ufeff" + rows.join("\n")], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `monthly-report-${new Date().toISOString().slice(0, 7)}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

// ── Mini bar chart ────────────────────────────────────────────────────────────

function BarChart({ buckets }: { buckets: { label: string; count: number }[] }) {
  const max = Math.max(...buckets.map((b) => b.count), 1);
  return (
    <div className="flex items-end gap-1 h-20 w-full">
      {buckets.map((b, i) => {
        const pct = Math.round((b.count / max) * 100);
        const isLast = i === buckets.length - 1;
        return (
          <div key={i} className="flex-1 flex flex-col items-center gap-1">
            <span className="text-[9px] text-text-dim tabular-nums">
              {b.count > 0 ? b.count : ""}
            </span>
            <div className="w-full flex items-end" style={{ height: 44 }}>
              <div
                style={{ height: `${Math.max(pct, 4)}%` }}
                className={`w-full rounded-t transition-all ${
                  isLast ? "bg-primary/70" : "bg-primary/30"
                }`}
              />
            </div>
            <span className="text-[9px] text-text-dim leading-tight text-center">{b.label}</span>
          </div>
        );
      })}
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

export default function StatsTab() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [shifts, setShifts] = useState<Shift[]>([]);
  const [loading, setLoading] = useState(true);
  const [chartView, setChartView] = useState<"weekly" | "monthly">("weekly");
  const [showInactive, setShowInactive] = useState(false);

  useEffect(() => {
    Promise.all([getStats(), getShifts("past")])
      .then(([s, sh]) => { setStats(s); setShifts(sh); })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <SkeletonStatCards />;
  if (!stats) return <div className="card text-danger">שגיאה בטעינת נתונים</div>;

  const maxTotal = Math.max(...stats.guards.map((g) => g.total), 1);
  const overloaded = stats.guards.filter((g) => g.overloaded);
  const inactive = stats.guards.filter((g) => g.future === 0);

  const buckets =
    chartView === "weekly"
      ? getWeeklyBuckets(shifts, 8)
      : getMonthlyBuckets(shifts, 6);

  return (
    <div className="fade-in space-y-4">
      {/* ── Summary ──────────────────────────────────────────── */}
      <div className="grid grid-cols-2 gap-3">
        {[
          { label: "סה״כ משמרות", value: stats.total_shifts, color: "text-primary-light" },
          { label: "שומרים פעילים", value: stats.active_guards, color: "text-success" },
          { label: "בוצעו", value: stats.total_past, color: "text-text-muted" },
          { label: "עתידיות", value: stats.total_future, color: "text-warning" },
        ].map((m) => (
          <div key={m.label} className="card text-center">
            <div className={`text-3xl font-black ${m.color}`}>{m.value}</div>
            <div className="text-xs text-text-dim mt-1">{m.label}</div>
          </div>
        ))}
      </div>

      {/* ── Trend chart ──────────────────────────────────────── */}
      <div className="card space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="font-bold text-text">מגמת משמרות</h2>
          <div className="flex gap-1">
            {(["weekly", "monthly"] as const).map((v) => (
              <button
                key={v}
                onClick={() => setChartView(v)}
                className={`px-3 py-1 rounded-full text-xs font-semibold transition-all ${
                  chartView === v
                    ? "bg-primary text-white"
                    : "bg-bg-base text-text-muted hover:text-text"
                }`}
              >
                {v === "weekly" ? "שבועי" : "חודשי"}
              </button>
            ))}
          </div>
        </div>
        <BarChart buckets={buckets} />
        <p className="text-[10px] text-text-dim text-center">
          {chartView === "weekly" ? "8 שבועות אחרונים" : "6 חודשים אחרונים"}
        </p>
      </div>

      {/* ── Monthly export ───────────────────────────────────── */}
      <div className="card flex items-center justify-between gap-3">
        <div>
          <p className="font-semibold text-text text-sm">דוח חודשי לייצוא</p>
          <p className="text-xs text-text-dim mt-0.5">CSV עם תאריך ושעות לכל משמרת לכל שומר</p>
        </div>
        <button
          onClick={() => exportMonthlyReport(shifts)}
          className="flex items-center gap-1.5 bg-success/10 hover:bg-success/20 text-success
                     border border-success/30 px-3 py-1.5 rounded-xl text-sm font-semibold transition-all shrink-0"
        >
          <Download size={14} />
          ייצוא CSV
        </button>
      </div>

      {/* ── Overload Alert ─────────────────────────────────────── */}
      {overloaded.length > 0 && (
        <div className="card border-warning/40 bg-warning/5 slide-in">
          <div className="flex items-center gap-2 mb-2">
            <AlertTriangle size={16} className="text-warning" />
            <span className="font-bold text-warning text-sm">
              {overloaded.length} שומר/ים עם עומס יתר (מעל {stats.overload_threshold} משמרות עתידיות)
            </span>
          </div>
          <div className="flex flex-wrap gap-2">
            {overloaded.map((g) => (
              <span key={g.name} className="overload-badge">
                {g.name} · {g.future} ⏳
              </span>
            ))}
          </div>
        </div>
      )}

      {/* ── Inactive guards ──────────────────────────────────── */}
      {inactive.length > 0 && (
        <div className="card border-text-dim/20 bg-bg-base">
          <button
            onClick={() => setShowInactive((v) => !v)}
            className="w-full flex items-center justify-between gap-2"
          >
            <div className="flex items-center gap-2">
              <span className="text-lg">😴</span>
              <div className="text-right">
                <p className="font-semibold text-text text-sm">
                  {inactive.length} שומרים ללא משמרת עתידית
                </p>
                <p className="text-xs text-text-dim">לחץ לפירוט</p>
              </div>
            </div>
            {showInactive ? (
              <ChevronUp size={16} className="text-text-dim shrink-0" />
            ) : (
              <ChevronDown size={16} className="text-text-dim shrink-0" />
            )}
          </button>
          {showInactive && (
            <div className="mt-3 flex flex-wrap gap-2 slide-in">
              {inactive.map((g) => (
                <span
                  key={g.name}
                  className="text-xs bg-bg-border text-text-muted px-2.5 py-1 rounded-full"
                >
                  {g.name}
                  {g.total === 0 ? " · חדש" : ` · ${g.past} עבר`}
                </span>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── Guard Rankings ─────────────────────────────────────── */}
      <div className="card space-y-3">
        <h2 className="font-bold text-text">דירוג שומרים</h2>
        {stats.guards.length === 0 && (
          <p className="text-text-dim text-sm text-center py-4">אין נתונים</p>
        )}
        <div className="space-y-2 max-h-[460px] overflow-y-auto">
          {stats.guards.map((g, i) => {
            const barWidth = Math.round((g.total / maxTotal) * 100);
            const pastPct = g.total > 0 ? Math.round((g.past / g.total) * 100) : 0;
            const futurePct = 100 - pastPct;
            return (
              <div
                key={g.name}
                className={`p-3 rounded-xl border transition-all ${
                  i < 3 ? RANK_BG[i] : "border-bg-border bg-bg-base"
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <span className="text-lg w-7 text-center">
                      {i < 3 ? MEDALS[i] : `${i + 1}.`}
                    </span>
                    <div>
                      <span className="font-bold text-text">{g.name}</span>
                      {g.overloaded && (
                        <span className="overload-badge mr-2">
                          <AlertTriangle size={10} />
                          עמוס
                        </span>
                      )}
                    </div>
                  </div>
                  <div className="flex gap-1.5">
                    <span className="pill-past">✅ {g.past}</span>
                    <span className="pill-future">🕐 {g.future}</span>
                    <span className="text-xs bg-bg-hover text-text-muted px-2 py-0.5 rounded-full font-semibold">
                      {g.total}
                    </span>
                  </div>
                </div>
                {/* Stacked bar */}
                <div className="h-2 bg-bg-deep rounded-full overflow-hidden">
                  <div
                    style={{ width: `${barWidth}%` }}
                    className="h-full flex rounded-full overflow-hidden"
                  >
                    <div style={{ width: `${pastPct}%` }} className="bg-success/60 h-full" />
                    <div style={{ width: `${futurePct}%` }} className="bg-warning/60 h-full" />
                  </div>
                </div>
              </div>
            );
          })}
        </div>
        <div className="flex gap-4 text-xs text-text-dim justify-center">
          <span className="flex items-center gap-1">
            <span className="w-3 h-3 rounded-full bg-success/60 inline-block" />
            עבר
          </span>
          <span className="flex items-center gap-1">
            <span className="w-3 h-3 rounded-full bg-warning/60 inline-block" />
            עתידי
          </span>
        </div>
      </div>
    </div>
  );
}
