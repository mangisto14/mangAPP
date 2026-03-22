import { useEffect, useState } from "react";
import { X } from "lucide-react";
import { getGuards, updateShift } from "../api";
import type { Guard, Shift } from "../types";

interface Props {
  shift: Shift;
  onClose: () => void;
  onSaved: () => void;
}

function isoToDateStr(iso: string) {
  return iso.slice(0, 10);
}

function isoToTimeStr(iso: string) {
  const d = new Date(iso);
  return `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
}

function toLocalIso(date: string, time: string) {
  return `${date}T${time}:00`;
}

export default function EditShiftModal({ shift, onClose, onSaved }: Props) {
  const [date, setDate] = useState(isoToDateStr(shift.start_time));
  const [startTime, setStartTime] = useState(isoToTimeStr(shift.start_time));
  const [endTime, setEndTime] = useState(isoToTimeStr(shift.end_time));
  const [guards, setGuards] = useState<Guard[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set(shift.names));
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    getGuards().then(setGuards).catch(console.error);
  }, []);

  const toggleGuard = (name: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      next.has(name) ? next.delete(name) : next.add(name);
      return next;
    });
  };

  const handleSave = async () => {
    if (selected.size === 0) { setError("יש לבחור לפחות שומר אחד"); return; }
    setSaving(true);
    setError("");
    try {
      await updateShift(
        shift.id,
        toLocalIso(date, startTime),
        toLocalIso(date, endTime),
        Array.from(selected),
      );
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
        className="w-full bg-bg-card border-t border-bg-border rounded-t-2xl pb-8 slide-in max-w-2xl mx-auto
                   max-h-[85vh] flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-bg-border shrink-0">
          <h2 className="font-bold text-text text-lg">עריכת משמרת</h2>
          <button onClick={onClose} className="text-text-dim hover:text-text p-1">
            <X size={20} />
          </button>
        </div>

        <div className="overflow-y-auto flex-1 p-5 space-y-5">
          {/* Date */}
          <div>
            <label className="text-xs text-text-dim mb-1 block">תאריך</label>
            <input
              type="date"
              value={date}
              onChange={(e) => setDate(e.target.value)}
              className="input text-sm w-full"
            />
          </div>

          {/* Times */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs text-text-dim mb-1 block">שעת התחלה</label>
              <input
                type="time"
                value={startTime}
                step={1800}
                onChange={(e) => setStartTime(e.target.value)}
                className="input text-sm w-full"
              />
            </div>
            <div>
              <label className="text-xs text-text-dim mb-1 block">שעת סיום</label>
              <input
                type="time"
                value={endTime}
                step={1800}
                onChange={(e) => setEndTime(e.target.value)}
                className="input text-sm w-full"
              />
            </div>
          </div>

          {/* Guards */}
          <div>
            <label className="text-xs text-text-dim mb-2 block">
              שומרים ({selected.size} נבחרו)
            </label>
            {guards.length === 0 && (
              <p className="text-text-dim text-sm">טוען...</p>
            )}
            <div className="grid grid-cols-2 gap-2 max-h-52 overflow-y-auto">
              {guards.map((g) => {
                const isSelected = selected.has(g.name);
                return (
                  <label
                    key={g.id}
                    className={`flex items-center gap-2 p-2 rounded-xl cursor-pointer border transition-all
                      ${isSelected
                        ? "bg-primary/10 border-primary/40"
                        : "bg-bg-base border-bg-border hover:border-bg-border/80"
                      }`}
                  >
                    <input
                      type="checkbox"
                      checked={isSelected}
                      onChange={() => toggleGuard(g.name)}
                      className="w-4 h-4 accent-primary"
                    />
                    <span className="text-sm font-medium text-text truncate">{g.name}</span>
                  </label>
                );
              })}
            </div>
          </div>

          {error && (
            <div className="text-danger text-sm bg-danger/10 border border-danger/30 rounded-xl p-3">
              {error}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-5 border-t border-bg-border shrink-0">
          <button
            onClick={handleSave}
            disabled={saving}
            className="btn-primary w-full"
          >
            {saving ? "שומר..." : "שמור שינויים"}
          </button>
        </div>
      </div>
    </div>
  );
}
