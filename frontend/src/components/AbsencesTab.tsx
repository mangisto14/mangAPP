import { useEffect, useState, useCallback } from "react";
import type { AbsenceStatus } from "../types";
import { getAbsences, markLeave, markReturn, resetAbsence } from "../api";

function elapsed(leftAt: string): { days: number; h: string; m: string; s: string } {
  const diff = Math.floor((Date.now() - new Date(leftAt).getTime()) / 1000);
  const days = Math.floor(diff / 86400);
  const h = String(Math.floor((diff % 86400) / 3600)).padStart(2, "0");
  const m = String(Math.floor((diff % 3600) / 60)).padStart(2, "0");
  const s = String(diff % 60).padStart(2, "0");
  return { days, h, m, s };
}

function Clock({ leftAt }: { leftAt: string }) {
  const [, setTick] = useState(0);
  useEffect(() => {
    const id = setInterval(() => setTick((t) => t + 1), 1000);
    return () => clearInterval(id);
  }, []);
  const { days, h, m, s } = elapsed(leftAt);
  return (
    <span className="font-mono text-base font-bold text-warning tabular-nums">
      {days > 0 && <span className="text-xs font-semibold text-warning/80 ml-1">{days}י׳ </span>}
      {h}:{m}:{s}
    </span>
  );
}

export default function AbsencesTab() {
  const [absences, setAbsences] = useState<AbsenceStatus[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<number | null>(null);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    try {
      setAbsences(await getAbsences());
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  async function action(fn: () => Promise<unknown>, guardId: number) {
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

  if (loading) {
    return <p className="text-center text-text-dim mt-10">טוען...</p>;
  }

  return (
    <div className="space-y-5 fade-in">
      {error && (
        <div className="card border-danger/40 bg-danger/10 text-danger text-sm">{error}</div>
      )}

      {/* Outside */}
      <div className="card">
        <h2 className="font-bold text-base mb-3 flex items-center gap-2">
          <span className="text-warning">🚪</span> מחוץ למסגרת
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
            {out.map((a) => (
              <li
                key={a.guard_id}
                className="flex items-center justify-between gap-2 bg-bg-base rounded-xl px-3 py-2.5 slide-in"
              >
                <div className="flex flex-col gap-0.5">
                  <span className="font-semibold text-text">{a.name}</span>
                  {a.left_at && <Clock leftAt={a.left_at} />}
                </div>
                <div className="flex gap-2 shrink-0">
                  <button
                    className="btn-ghost text-xs px-2 py-1"
                    disabled={busy === a.guard_id}
                    onClick={() => action(() => resetAbsence(a.guard_id), a.guard_id)}
                  >
                    🔄 אפס שעון
                  </button>
                  <button
                    className="btn-primary text-xs px-3 py-1.5"
                    disabled={busy === a.guard_id}
                    onClick={() => action(() => markReturn(a.guard_id), a.guard_id)}
                  >
                    חזר ✅
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Inside */}
      <div className="card">
        <h2 className="font-bold text-base mb-3 flex items-center gap-2">
          <span className="text-success">🏠</span> במסגרת
        </h2>
        {inside.length === 0 ? (
          <p className="text-text-dim text-sm text-center py-4">אין שומרים במסגרת</p>
        ) : (
          <ul className="space-y-2">
            {inside.map((a) => (
              <li
                key={a.guard_id}
                className="flex items-center justify-between gap-2 bg-bg-base rounded-xl px-3 py-2"
              >
                <span className="font-medium text-text">{a.name}</span>
                <button
                  className="btn-danger text-xs px-3 py-1.5"
                  disabled={busy === a.guard_id}
                  onClick={() => action(() => markLeave(a.guard_id), a.guard_id)}
                >
                  יצא 🚪
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
