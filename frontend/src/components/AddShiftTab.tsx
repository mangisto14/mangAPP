import { useEffect, useState } from "react";
import { Plus, Trash2, CheckCircle, XCircle, Sparkles, AlertTriangle } from "lucide-react";
import { getGuards, addShifts, getSuggest } from "../api";
import type { Guard, StagedShift, Suggestion } from "../types";

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

  useEffect(() => {
    getGuards().then(setGuards).catch(console.error);
    getSuggest(3).then(setSuggestions).catch(console.error);
  }, []);

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
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs text-text-dim mb-1 block">תאריך</label>
            <input
              type="date"
              value={date}
              onChange={(e) => setDate(e.target.value)}
              className="input text-sm"
            />
          </div>
          <div>
            <label className="text-xs text-text-dim mb-1 block">שעת התחלה</label>
            <input
              type="time"
              value={time}
              step={1800}
              onChange={(e) => setTime(e.target.value)}
              className="input text-sm"
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
          <label className="text-xs text-text-dim mb-2 block">
            בחר שומרים ({selected.size} נבחרו)
          </label>
          {guards.length === 0 && (
            <p className="text-text-dim text-sm">אין שומרים – הוסף בלשונית 👥</p>
          )}
          <div className="grid grid-cols-2 gap-2 max-h-56 overflow-y-auto">
            {guards.map((g) => (
              <label
                key={g.id}
                className={`flex items-center gap-2 p-2 rounded-xl cursor-pointer border transition-all
                  ${
                    selected.has(g.name)
                      ? "bg-primary/10 border-primary/40"
                      : "bg-bg-base border-bg-border hover:border-bg-border/80"
                  }`}
              >
                <input
                  type="checkbox"
                  checked={selected.has(g.name)}
                  onChange={() => toggleGuard(g.name)}
                  className="w-4 h-4 accent-primary"
                />
                <div className="min-w-0">
                  <div className="text-sm font-medium text-text truncate flex items-center gap-1">
                    {g.name}
                    {g.overloaded && (
                      <AlertTriangle size={12} className="text-warning flex-shrink-0" />
                    )}
                  </div>
                  <div className="flex gap-1 mt-0.5">
                    <span className="pill-past">✅ {g.past}</span>
                    <span className="pill-future">🕐 {g.future}</span>
                  </div>
                </div>
              </label>
            ))}
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
