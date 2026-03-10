import { useCallback, useEffect, useState } from "react";
import Clock from "./Clock";
import { getAbsences, markLeave, markReturn, resetAbsence } from "./api";
import type { AbsenceStatus } from "./types";

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

  useEffect(() => {
    load();
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

  if (loading) {
    return <p className="text-center text-text-dim mt-10">טוען...</p>;
  }

  return (
    <div className="space-y-5 fade-in">
      {error && (
        <div className="card border-danger/40 bg-danger/10 text-danger text-sm">
          {error}
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
          <p className="text-text-dim text-sm text-center py-4">
            אין יוצאים כרגע
          </p>
        ) : (
          <ul className="space-y-3">
            {out.map((a) => (
              <li
                key={a.guard_id}
                className="flex items-center justify-between gap-2 bg-bg-base rounded-xl px-3 py-3 slide-in"
              >
                <div className="flex flex-col gap-0.5 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-text truncate">
                      {a.name}
                    </span>
                    {a.total_exits > 0 && (
                      <span className="shrink-0 text-xs bg-bg-border text-text-muted px-1.5 py-0.5 rounded-full">
                        {a.total_exits} יציאות
                      </span>
                    )}
                  </div>
                  {a.left_at && <Clock leftAt={a.left_at} />}
                </div>
                <div className="flex gap-2 shrink-0">
                  <button
                    className="btn-ghost text-xs px-2 py-1"
                    disabled={busy === a.guard_id}
                    onClick={() =>
                      doAction(() => resetAbsence(a.guard_id), a.guard_id)
                    }
                  >
                    🔄
                  </button>
                  <button
                    className="btn-primary text-xs px-3 py-1.5"
                    disabled={busy === a.guard_id}
                    onClick={() =>
                      doAction(() => markReturn(a.guard_id), a.guard_id)
                    }
                  >
                    חזר ✅
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* ── במסגרת ── */}
      <div className="card">
        <h2 className="font-bold text-base mb-3 flex items-center gap-2">
          <span>🏠</span> במסגרת
          <span className="bg-success/20 text-success text-xs font-bold px-2 py-0.5 rounded-full">
            {inside.length}
          </span>
        </h2>

        {inside.length === 0 ? (
          <p className="text-text-dim text-sm text-center py-4">
            אין שומרים במסגרת
          </p>
        ) : (
          <ul className="space-y-2">
            {inside.map((a) => (
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
                  onClick={() =>
                    doAction(() => markLeave(a.guard_id), a.guard_id)
                  }
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
