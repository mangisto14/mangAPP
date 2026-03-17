import { useEffect, useMemo, useState } from "react";
import { Plus, Trash2, CheckCircle, XCircle, Sparkles, AlertTriangle } from "lucide-react";
import { getGuards, addShifts, getSuggest } from "../api";
import type { Guard, StagedShift, Suggestion } from "../types";
import { getRotation } from "../features/rotation/api";
import { computePeriods } from "../features/rotation/utils";
import type { RotationConfig } from "../features/rotation/types";
import { getAbsences, getAbsencesActiveOn } from "../features/absences/api";
import type { AbsenceStatus } from "../features/absences/types";

function toLocalIso(date: string, time: string) {
  return `${date}T${time}:00`;
}

function addMinutes(iso: string, minutes: number): string {
  const d = new Date(iso);
  d.setMinutes(d.getMinutes() + minutes);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}:00`;
}

function formatLabel(iso: string) {
  const d = new Date(iso);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${pad(d.getDate())}/${pad(d.getMonth() + 1)} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

const DURATIONS = [
  { label: "30 דק׳", value: 30 },
  { label: "45 דק׳", value: 45 },
  { label: "1 ש׳", value: 60 },
  { label: "1.5 ש׳", value: 90 },
  { label: "2 ש׳", value: 120 },
  { label: "3 ש׳", value: 180 },
  { label: "4 ש׳", value: 240 },
];

interface Props {
  onSaved: () => void;
}

export default function AddShiftTab({ onSaved }: Props) {
  const today = new Date().toISOString().slice(0, 10);
  const nowTime = (() => {
    const d = new Date();
    const m = Math.ceil(d.getMinutes() / 30) * 30;
    d.setMinutes(m, 0, 0);
    return `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
  })();

  const [date, setDate] = useState(today);
  const [time, setTime] = useState(nowTime);
  const [duration, setDuration] = useState(60);
  const [guards, setGuards] = useState<Guard[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [staged, setStaged] = useState<StagedShift[]>([]);
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [showSuggest, setShowSuggest] = useState(false);
  const [saving, setSaving] = useState(false);
  const [toast, setToast] = useState("");
  const [rotation, setRotation] = useState<RotationConfig | null>(null);
  const [absences, setAbsences] = useState<AbsenceStatus[]>([]);
  const [activeOnAbsences, setActiveOnAbsences] = useState<{ name: string; reason: string | null }[]>([]);

  useEffect(() => {
    getGuards().then(setGuards).catch(console.error);
    getSuggest(3).then(setSuggestions).catch(console.error);
    getRotation().then(setRotation).catch(console.error);
    getAbsences().then(setAbsences).catch(console.error);
  }, []);

  // כשהתאריך משתנה: רענן יציאות נוכחיות (לצבע כתום) + חופשות שחופפות לתאריך (לצבע אדום)
  useEffect(() => {
    getAbsences().then(setAbsences).catch(console.error);
    if (date) getAbsencesActiveOn(date).then(setActiveOnAbsences).catch(console.error);
  }, [date]);

  // Names from rotation slots for the selected date (lowercased)
  const rotationNamesForDate = useMemo(() => {
    if (!rotation || !date) return new Set<string>();
    const periods = computePeriods(rotation.start_date, 60);
    const target = new Date(date + "T00:00:00");
    const period = periods.find((p) => target >= p.start && target < p.end);
    if (!period) return new Set<string>();
    const names = new Set<string>();
    rotation.roles.forEach((role) => {
      const idx = period.slotIndex % (role.slots.length || 1);
      (role.slots[idx] ?? []).forEach((n) => names.add(n.trim().toLowerCase()));
    });
    return names;
  }, [rotation, date]);

  // Names of soldiers whose rotation period STARTS on the selected date (יוצאים לסבב היום)
  const rotationStartingNames = useMemo(() => {
    if (!rotation || !date) return new Set<string>();
    const periods = computePeriods(rotation.start_date, 60);
    const target = new Date(date + "T00:00:00");
    const startPeriod = periods.find(
      (p) => p.start.getFullYear() === target.getFullYear() &&
             p.start.getMonth() === target.getMonth() &&
             p.start.getDate() === target.getDate()
    );
    if (!startPeriod) return new Set<string>();
    const names = new Set<string>();
    rotation.roles.forEach((role) => {
      const idx = startPeriod.slotIndex % (role.slots.length || 1);
      (role.slots[idx] ?? []).forEach((n) => names.add(n.trim().toLowerCase()));
    });
    return names;
  }, [rotation, date]);

  // Names of soldiers whose rotation period ENDS on the selected date (חוזרים מסבב היום)
  const rotationReturningNames = useMemo(() => {
    if (!rotation || !date) return new Set<string>();
    const periods = computePeriods(rotation.start_date, 60);
    const target = new Date(date + "T00:00:00");
    const exitPeriod = periods.find(
      (p) => p.end.getFullYear() === target.getFullYear() &&
             p.end.getMonth() === target.getMonth() &&
             p.end.getDate() === target.getDate()
    );
    if (!exitPeriod) return new Set<string>();
    const names = new Set<string>();
    rotation.roles.forEach((role) => {
      const idx = exitPeriod.slotIndex % (role.slots.length || 1);
      (role.slots[idx] ?? []).forEach((n) => names.add(n.trim().toLowerCase()));
    });
    return names;
  }, [rotation, date]);

  const ABSENT_REASONS = ["חופשה", "מחלה"];

  // אדום: חופשות/מחלות שחופפות לתאריך הנבחר (כולל שנכנסו לפני התאריך)
  const absentNames = useMemo(
    () =>
      new Set(
        activeOnAbsences
          .filter((a) => a.reason && ABSENT_REASONS.includes(a.reason))
          .map((a) => a.name.toLowerCase())
      ),
    [activeOnAbsences]
  );

  // כתום: יצא מסיבה אחרת (רופא, אישי, אחר, ללא סיבה)
  const tempOutNames = useMemo(
    () =>
      new Set(
        absences
          .filter((a) => a.is_out && (!a.reason || !ABSENT_REASONS.includes(a.reason)))
          .map((a) => a.name.toLowerCase())
      ),
    [absences]
  );

  type GuardStatus = "rotation-available" | "rotation-start" | "rotation-returning" | "rotation-absent" | "rotation-temp" | "absent" | "temp-out" | "default";
  function guardStatus(name: string): GuardStatus {
    const lower = name.toLowerCase();
    const inRotation = [...rotationNamesForDate].some(
      (r) => lower.startsWith(r) || r.startsWith(lower)
    );
    const isStarting = [...rotationStartingNames].some(
      (r) => lower.startsWith(r) || r.startsWith(lower)
    );
    const isReturning = [...rotationReturningNames].some(
      (r) => lower.startsWith(r) || r.startsWith(lower)
    );
    const isAbsent = absentNames.has(lower);
    const isTempOut = tempOutNames.has(lower);
    if (inRotation && isStarting) return "rotation-start";   // יום יציאה לסבב
    if (inRotation && !isAbsent && !isTempOut) return "rotation-available"; // בחופש סבב
    if (inRotation && isAbsent) return "rotation-absent";
    if (inRotation && isTempOut) return "rotation-temp";
    if (isReturning) return "rotation-returning";            // יום חזרה מסבב
    if (isAbsent) return "absent";
    if (isTempOut) return "temp-out";
    return "default";
  }

  const STATUS_ORDER: Record<GuardStatus, number> = {
    "default": 0,             // זמין
    "rotation-returning": 1,  // חוזר מסבב היום
    "temp-out": 2,            // יצא זמנית
    "rotation-available": 3,  // בחופש סבב
    "rotation-start": 4,      // יוצא לסבב היום
    "rotation-temp": 5,
    "rotation-absent": 6,
    "absent": 7,
  };

  const sortedGuards = useMemo(
    () => [...guards].sort((a, b) => STATUS_ORDER[guardStatus(a.name)] - STATUS_ORDER[guardStatus(b.name)]),
    [guards, rotationNamesForDate, absentNames]
  );

  const showToast = (msg: string) => {
    setToast(msg);
    setTimeout(() => setToast(""), 3000);
  };

  const toggleGuard = (name: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      next.has(name) ? next.delete(name) : next.add(name);
      return next;
    });
  };

  const handleAdd = () => {
    if (selected.size === 0) {
      showToast("יש לבחור לפחות שומר אחד");
      return;
    }
    const startIso = toLocalIso(date, time);
    const endIso = addMinutes(startIso, duration);
    const shift: StagedShift = {
      start_time: startIso,
      end_time: endIso,
      names: Array.from(selected),
    };
    setStaged((prev) => [...prev, shift]);

    // Auto-advance time
    const newTime = endIso.slice(11, 16);
    const newDate = endIso.slice(0, 10);
    setDate(newDate);
    setTime(newTime);
    setSelected(new Set());
    showToast("משמרת נוספה לאישור");
  };

  const removeStaged = (idx: number) => {
    setStaged((prev) => prev.filter((_, i) => i !== idx));
  };

  const handleConfirm = async () => {
    if (staged.length === 0) return;
    setSaving(true);
    try {
      await addShifts(staged);
      setStaged([]);
      showToast(`✅ ${staged.length} משמרות נשמרו`);
      await Promise.all([
        getGuards().then(setGuards),
        getSuggest(3).then(setSuggestions),
      ]);
      onSaved();
    } catch (e) {
      showToast(`שגיאה: ${(e as Error).message}`);
    } finally {
      setSaving(false);
    }
  };

  const applySuggestion = (suggestion: Suggestion) => {
    setSelected(new Set([suggestion.name]));
    setShowSuggest(false);
  };

  const overloadedSelected = Array.from(selected).filter((name) => {
    const g = guards.find((g) => g.name === name);
    return g?.overloaded;
  });

  return (
    <div className="fade-in space-y-4">
      {/* Toast */}
      {toast && (
        <div className="fixed top-20 right-4 left-4 max-w-sm mx-auto z-50">
          <div className="card border-primary/40 bg-primary/10 text-text text-sm text-center font-medium slide-in">
            {toast}
          </div>
        </div>
      )}

      {/* ── Suggest Panel ──────────────────────────────────────── */}
      <div className="card border-warning/20 bg-warning/5">
        <button
          onClick={() => setShowSuggest((v) => !v)}
          className="w-full flex items-center justify-between"
        >
          <span className="flex items-center gap-2 font-bold text-warning">
            <Sparkles size={16} />
            מי מגיע לו המשמרת הבאה?
          </span>
          <span className="text-text-dim text-sm">{showSuggest ? "▲" : "▼"}</span>
        </button>

        {showSuggest && (
          <div className="mt-3 space-y-2 slide-in">
            {suggestions.length === 0 && (
              <p className="text-text-dim text-sm">אין שומרים רשומים</p>
            )}
            {suggestions.map((s, i) => (
              <button
                key={s.name}
                onClick={() => applySuggestion(s)}
                className="w-full flex items-center justify-between p-3 rounded-xl
                           bg-bg-base hover:bg-bg-hover border border-bg-border hover:border-warning/40
                           transition-all text-right"
              >
                <div className="flex items-center gap-2">
                  <span className="text-warning font-bold text-lg w-6">
                    {i === 0 ? "🥇" : i === 1 ? "🥈" : "🥉"}
                  </span>
                  <div>
                    <div className="font-bold text-text">{s.name}</div>
                    <div className="text-xs text-text-dim">
                      {s.total === 0
                        ? "אף משמרת עדיין"
                        : `${s.past} עבר · ${s.future} עתידי`}
                      {s.last_past_date &&
                        ` · אחרון: ${new Date(s.last_past_date).toLocaleDateString("he-IL")}`}
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-1">
                  {s.overloaded && (
                    <span className="overload-badge">
                      <AlertTriangle size={10} />
                      עמוס
                    </span>
                  )}
                  <span className="text-xs text-primary-light font-semibold">בחר →</span>
                </div>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* ── Shift Builder ──────────────────────────────────────── */}
      <div className="card space-y-4">
        <h2 className="font-bold text-text">הגדרת משמרת</h2>

        {/* Date + Time */}
        <div className="flex gap-3">
          <div style={{ width: "calc(100% - 7.5rem)" }}>
            <label className="text-xs text-text-dim mb-1 block">תאריך</label>
            <input
              type="date"
              value={date}
              onChange={(e) => setDate(e.target.value)}
              className="input text-sm w-full py-1.5"
            />
          </div>
          <div style={{ width: "7rem", flexShrink: 0 }}>
            <label className="text-xs text-text-dim mb-1 block">שעה</label>
            <input
              type="time"
              value={time}
              step={1800}
              onChange={(e) => setTime(e.target.value)}
              className="input text-sm w-full py-1.5"
            />
          </div>
        </div>

        {/* Duration */}
        <div>
          <label className="text-xs text-text-dim mb-1 block">משך</label>
          <div className="flex flex-wrap gap-2">
            {DURATIONS.map((d) => (
              <button
                key={d.value}
                onClick={() => setDuration(d.value)}
                className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
                  duration === d.value
                    ? "bg-primary text-white"
                    : "bg-bg-base text-text-muted hover:text-text border border-bg-border"
                }`}
              >
                {d.label}
              </button>
            ))}
          </div>
        </div>

        {/* Guards Checkboxes */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <label className="text-xs text-text-dim">
              בחר שומרים ({selected.size} נבחרו)
            </label>
            {rotation && (
              <div className="flex items-center gap-2 text-[10px] text-text-dim">
                <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-success inline-block"/>זמין</span>
                <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-warning inline-block"/>חוזר/יצא</span>
                <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-danger inline-block"/>בחופש/נעדר</span>
              </div>
            )}
          </div>
          {guards.length === 0 && (
            <p className="text-text-dim text-sm">אין שומרים – הוסף בלשונית 👥</p>
          )}
          <div className="grid grid-cols-2 gap-2 max-h-56 overflow-y-auto">
            {sortedGuards.map((g) => {
              const status = guardStatus(g.name);
              const isSelected = selected.has(g.name);
              const statusClass =
                isSelected
                  ? "bg-primary/10 border-primary/40"
                  : status === "default"
                  ? "bg-success/10 border-success/40"
                  : status === "rotation-returning"
                  ? "bg-warning/10 border-warning/40"
                  : status === "rotation-available" || status === "rotation-start" || status === "rotation-absent" || status === "absent"
                  ? "bg-danger/10 border-danger/40"
                  : status === "rotation-temp" || status === "temp-out"
                  ? "bg-warning/10 border-warning/40"
                  : "bg-bg-base border-bg-border hover:border-bg-border/80";
              return (
                <label
                  key={g.id}
                  className={`flex items-center gap-2 p-2 rounded-xl cursor-pointer border transition-all ${statusClass}`}
                >
                  <input
                    type="checkbox"
                    checked={isSelected}
                    onChange={() => toggleGuard(g.name)}
                    className="w-4 h-4 accent-primary"
                  />
                  <div className="min-w-0">
                    <div className="text-sm font-medium text-text truncate flex items-center gap-1">
                      {g.name}
                      {g.overloaded && (
                        <AlertTriangle size={12} className="text-warning flex-shrink-0" />
                      )}
                      {status === "default" && (
                        <span className="text-success text-[10px] font-bold">זמין</span>
                      )}
                      {status === "rotation-start" && (
                        <span className="text-danger text-[10px] font-bold">יוצא לסבב</span>
                      )}
                      {status === "rotation-available" && (
                        <span className="text-danger text-[10px] font-bold">בחופש</span>
                      )}
                      {status === "rotation-returning" && (
                        <span className="text-warning text-[10px] font-bold">חוזר מסבב</span>
                      )}
                      {(status === "absent" || status === "rotation-absent" || status === "rotation-temp") && (
                        <span className="text-danger text-[10px] font-bold">נעדר</span>
                      )}
                      {status === "temp-out" && (
                        <span className="text-warning text-[10px] font-bold">יצא</span>
                      )}
                    </div>
                    <div className="flex gap-1 mt-0.5">
                      <span className="pill-past">✅ {g.past}</span>
                      <span className="pill-future">🕐 {g.future}</span>
                    </div>
                  </div>
                </label>
              );
            })}
          </div>
        </div>

        {/* Overload warning */}
        {overloadedSelected.length > 0 && (
          <div className="flex items-start gap-2 bg-warning/10 border border-warning/30 rounded-xl p-3">
            <AlertTriangle size={16} className="text-warning flex-shrink-0 mt-0.5" />
            <div className="text-sm text-warning">
              <strong>שים לב:</strong>{" "}
              {overloadedSelected.join(", ")} משובץ/ים יותר מדי — יש להם {" "}
              {guards.find((g) => g.name === overloadedSelected[0])?.future}+ משמרות עתידיות
            </div>
          </div>
        )}

        <button onClick={handleAdd} className="btn-primary w-full flex items-center justify-center gap-2">
          <Plus size={16} />
          הוסף לרשימת אישור
        </button>
      </div>

      {/* ── Staging Area ──────────────────────────────────────── */}
      {staged.length > 0 && (
        <div className="card space-y-3 slide-in">
          <h3 className="font-bold text-text flex items-center gap-2">
            ⏳ ממתין לאישור
            <span className="bg-primary/20 text-primary-light text-xs font-bold px-2 py-0.5 rounded-full">
              {staged.length}
            </span>
          </h3>
          <div className="space-y-2 max-h-48 overflow-y-auto">
            {staged.map((s, i) => (
              <div
                key={i}
                className="flex items-center justify-between bg-bg-base rounded-xl px-3 py-2 border border-bg-border"
              >
                <div className="text-sm">
                  <span className="text-text-muted font-mono">
                    {formatLabel(s.start_time)}→{formatLabel(s.end_time)}
                  </span>
                  <span className="text-text mr-2">{s.names.join(", ")}</span>
                </div>
                <button
                  onClick={() => removeStaged(i)}
                  className="text-text-dim hover:text-danger transition-colors"
                >
                  <Trash2 size={14} />
                </button>
              </div>
            ))}
          </div>
          <div className="flex gap-2">
            <button
              onClick={handleConfirm}
              disabled={saving}
              className="btn-primary flex-1 flex items-center justify-center gap-2"
            >
              <CheckCircle size={16} />
              {saving ? "שומר..." : `אשר הכל (${staged.length})`}
            </button>
            <button
              onClick={() => setStaged([])}
              className="btn-ghost flex items-center gap-1"
            >
              <XCircle size={16} />
              בטל
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
