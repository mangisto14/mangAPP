import { useEffect, useState } from "react";

const API = (import.meta.env.VITE_API_URL ?? "") + "/api/schedule";

type RowData = { role: string; cells: string[][] };
type Schedule = { periods: string[]; rows: RowData[] };

const ROLE_COLORS: Record<string, string> = {
  "קצינים":  "bg-blue-500/10 border-blue-500/20 text-blue-300",
  "מפקדים":  "bg-purple-500/10 border-purple-500/20 text-purple-300",
  "פקחים":   "bg-emerald-500/10 border-emerald-500/20 text-emerald-300",
  "נהגים":   "bg-amber-500/10 border-amber-500/20 text-amber-300",
  "מטהרים":  "bg-rose-500/10 border-rose-500/20 text-rose-300",
  "עתודאים": "bg-sky-500/10 border-sky-500/20 text-sky-300",
};

function saveSchedule(schedule: Schedule) {
  return fetch(API, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(schedule),
  });
}

// ── Cell edit modal ────────────────────────────────────────────────────────────
function CellModal({
  names,
  onSave,
  onClose,
}: {
  names: string[];
  onSave: (names: string[]) => void;
  onClose: () => void;
}) {
  const [text, setText] = useState(names.join(", "));
  return (
    <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center px-4" onClick={onClose}>
      <div
        className="bg-bg-card border border-bg-border rounded-2xl p-5 w-full max-w-sm space-y-4"
        onClick={(e) => e.stopPropagation()}
        dir="rtl"
      >
        <div className="flex items-center justify-between">
          <h3 className="font-bold text-text">עריכת משבצת</h3>
          <button onClick={onClose} className="text-text-dim hover:text-text px-1">✕</button>
        </div>
        <div>
          <p className="text-xs text-text-dim mb-1">שמות מופרדים בפסיק</p>
          <textarea
            className="input w-full resize-none"
            rows={3}
            value={text}
            onChange={(e) => setText(e.target.value)}
            autoFocus
          />
        </div>
        <div className="flex gap-2">
          <button
            className="btn-primary flex-1"
            onClick={() => {
              const parsed = text.split(",").map((s) => s.trim()).filter(Boolean);
              onSave(parsed);
            }}
          >
            שמור
          </button>
          <button className="btn-secondary flex-1" onClick={onClose}>ביטול</button>
        </div>
      </div>
    </div>
  );
}

// ── Column header inline edit ──────────────────────────────────────────────────
function PeriodHeader({
  value,
  onSave,
}: {
  value: string;
  onSave: (v: string) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [text, setText] = useState(value);

  if (editing) {
    return (
      <input
        className="border border-primary rounded px-1 py-0.5 text-xs text-center bg-bg-deep text-text w-24"
        value={text}
        autoFocus
        onChange={(e) => setText(e.target.value)}
        onBlur={() => { onSave(text); setEditing(false); }}
        onKeyDown={(e) => {
          if (e.key === "Enter") { onSave(text); setEditing(false); }
          if (e.key === "Escape") setEditing(false);
        }}
      />
    );
  }
  return (
    <span
      className="cursor-pointer hover:text-primary transition-colors"
      title="לחץ לעריכת כותרת"
      onClick={() => setEditing(true)}
    >
      {value}
    </span>
  );
}

// ── Main component ─────────────────────────────────────────────────────────────
export default function ScheduleTab() {
  const [schedule, setSchedule] = useState<Schedule | null>(null);
  const [loading, setLoading] = useState(true);
  const [editCell, setEditCell] = useState<{ ri: number; ci: number } | null>(null);

  useEffect(() => {
    fetch(API)
      .then((r) => r.json())
      .then((data) => { setSchedule(data); setLoading(false); })
      .catch(() => setLoading(false));
  }, []);

  function update(next: Schedule) {
    setSchedule(next);
    saveSchedule(next);
  }

  function handlePeriodSave(ci: number, value: string) {
    if (!schedule) return;
    const periods = [...schedule.periods];
    periods[ci] = value;
    update({ ...schedule, periods });
  }

  function handleCellSave(ri: number, ci: number, names: string[]) {
    if (!schedule) return;
    const rows = schedule.rows.map((row, r) =>
      r === ri
        ? { ...row, cells: row.cells.map((c, c2) => (c2 === ci ? names : c)) }
        : row
    );
    update({ ...schedule, rows });
    setEditCell(null);
  }

  function addColumn() {
    if (!schedule) return;
    const periods = [...schedule.periods, "תאריך"];
    const rows = schedule.rows.map((row) => ({
      ...row,
      cells: [...row.cells, []],
    }));
    update({ ...schedule, periods, rows });
  }

  if (loading) return <p className="text-center text-text-dim py-10">טוען...</p>;
  if (!schedule) return <p className="text-center text-red-400 py-10">שגיאה בטעינת הלוח</p>;

  return (
    <div className="fade-in space-y-3" dir="rtl">
      <div className="flex items-center justify-between">
        <h2 className="text-base font-bold text-text">לוח סבב – מרץ 2026</h2>
        <button className="btn-secondary text-xs px-3 py-1.5" onClick={addColumn}>
          + עמודה
        </button>
      </div>

      <div className="overflow-x-auto rounded-xl border border-bg-border">
        <table className="min-w-max w-full text-xs border-collapse">
          <thead>
            <tr className="bg-bg-card">
              <th className="sticky right-0 z-10 bg-bg-card border border-bg-border px-3 py-2 text-right font-bold text-text-muted min-w-[80px]">
                תפקיד
              </th>
              {schedule.periods.map((p, ci) => (
                <th
                  key={ci}
                  className="border border-bg-border px-3 py-2 text-center font-bold text-primary-light whitespace-nowrap min-w-[110px]"
                >
                  <PeriodHeader value={p} onSave={(v) => handlePeriodSave(ci, v)} />
                </th>
              ))}
            </tr>
          </thead>

          <tbody>
            {schedule.rows.map((row, ri) => (
              <tr key={row.role} className={ri % 2 === 0 ? "bg-bg-deep" : "bg-bg-base"}>
                <td className="sticky right-0 z-10 border border-bg-border px-3 py-2 font-bold text-text bg-inherit">
                  <span
                    className={`inline-block px-2 py-0.5 rounded-md border text-xs font-bold ${ROLE_COLORS[row.role] ?? ""}`}
                  >
                    {row.role}
                  </span>
                </td>

                {row.cells.map((names, ci) => (
                  <td
                    key={ci}
                    className="border border-bg-border px-2 py-1.5 text-center align-top cursor-pointer hover:bg-primary/10 transition-colors"
                    onClick={() => setEditCell({ ri, ci })}
                    title="לחץ לעריכה"
                  >
                    <div className="flex flex-col gap-0.5">
                      {names.length > 0 ? (
                        names.map((name, ni) => (
                          <span key={ni} className="text-text text-xs leading-snug">
                            {name}
                          </span>
                        ))
                      ) : (
                        <span className="text-text-dim text-xs">—</span>
                      )}
                    </div>
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {editCell && (
        <CellModal
          names={schedule.rows[editCell.ri].cells[editCell.ci]}
          onSave={(names) => handleCellSave(editCell.ri, editCell.ci, names)}
          onClose={() => setEditCell(null)}
        />
      )}
    </div>
  );
}
