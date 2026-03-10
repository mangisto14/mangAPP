import { useEffect, useState } from "react";
import { AlertTriangle } from "lucide-react";
import { getStats } from "../api";
import type { Stats } from "../types";

const MEDALS = ["🥇", "🥈", "🥉"];
const RANK_BG = [
  "border-yellow-500/30 bg-yellow-500/5",
  "border-slate-400/30 bg-slate-400/5",
  "border-orange-700/30 bg-orange-700/5",
];

export default function StatsTab() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getStats()
      .then(setStats)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return <div className="text-center text-text-dim py-10 fade-in">טוען...</div>;
  }
  if (!stats) {
    return <div className="card text-danger">שגיאה בטעינת נתונים</div>;
  }

  const maxTotal = Math.max(...stats.guards.map((g) => g.total), 1);
  const overloaded = stats.guards.filter((g) => g.overloaded);

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
                    <div
                      style={{ width: `${pastPct}%` }}
                      className="bg-success/60 h-full"
                    />
                    <div
                      style={{ width: `${futurePct}%` }}
                      className="bg-warning/60 h-full"
                    />
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
