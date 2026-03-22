import { useEffect, useMemo, useState } from "react";
import { X, AlertTriangle } from "lucide-react";
import { getGuards, updateShift } from "../api";
import type { Guard, Shift } from "../types";
import { getRotation } from "../features/rotation/api";
import { computePeriods } from "../features/rotation/utils";
import type { RotationConfig } from "../features/rotation/types";
import { getAbsences, getAbsencesActiveOn } from "../features/absences/api";
import type { AbsenceStatus } from "../features/absences/types";

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

type GuardStatus = "rotation-available" | "rotation-start" | "rotation-returning" | "rotation-absent" | "rotation-temp" | "absent" | "temp-out" | "default";

const STATUS_ORDER: Record<GuardStatus, number> = {
  "default": 0,
  "rotation-returning": 1,
  "temp-out": 2,
  "rotation-available": 3,
  "rotation-start": 4,
  "rotation-temp": 5,
  "rotation-absent": 6,
  "absent": 7,
};

const ABSENT_REASONS = ["חופשה", "מחלה"];

export default function EditShiftModal({ shift, onClose, onSaved }: Props) {
  const [date, setDate] = useState(isoToDateStr(shift.start_time));
  const [startTime, setStartTime] = useState(isoToTimeStr(shift.start_time));
  const [endTime, setEndTime] = useState(isoToTimeStr(shift.end_time));
  const [guards, setGuards] = useState<Guard[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set(shift.names));
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [rotation, setRotation] = useState<RotationConfig | null>(null);
  const [absences, setAbsences] = useState<AbsenceStatus[]>([]);
  const [activeOnAbsences, setActiveOnAbsences] = useState<{ name: string; reason: string | null }[]>([]);

  useEffect(() => {
    getGuards().then(setGuards).catch(console.error);
    getRotation().then(setRotation).catch(console.error);
    getAbsences().then(setAbsences).catch(console.error);
  }, []);

  useEffect(() => {
    getAbsences().then(setAbsences).catch(console.error);
    if (date) getAbsencesActiveOn(date).then(setActiveOnAbsences).catch(console.error);
  }, [date]);

  // Rotation names currently on leave for the selected date
  const rotationNamesForDate = useMemo(() => {
    if (!rotation || !date) return new Set<string>();
    const periods = computePeriods(rotation, 60);
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

  // Guards whose rotation period starts on the selected date
  const rotationStartingNames = useMemo(() => {
    if (!rotation || !date) return new Set<string>();
    const periods = computePeriods(rotation, 60);
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

  // Guards whose rotation period ends on the selected date
  const rotationReturningNames = useMemo(() => {
    if (!rotation || !date) return new Set<string>();
    const periods = computePeriods(rotation, 60);
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

  const absentNames = useMemo(
    () => new Set(
      activeOnAbsences
        .filter((a) => a.reason && ABSENT_REASONS.includes(a.reason))
        .map((a) => a.name.toLowerCase())
    ),
    [activeOnAbsences]
  );

  const tempOutNames = useMemo(
    () => new Set(
      absences
        .filter((a) => a.is_out && (!a.reason || !ABSENT_REASONS.includes(a.reason)))
        .map((a) => a.name.toLowerCase())
    ),
    [absences]
  );

  function guardStatus(name: string): GuardStatus {
    const lower = name.toLowerCase();
    const inRotation = [...rotationNamesForDate].some((r) => lower.startsWith(r) || r.startsWith(lower));
    const isStarting = [...rotationStartingNames].some((r) => lower.startsWith(r) || r.startsWith(lower));
    const isReturning = [...rotationReturningNames].some((r) => lower.startsWith(r) || r.startsWith(lower));
    const isAbsent = absentNames.has(lower);
    const isTempOut = tempOutNames.has(lower);
    if (inRotation && isStarting) return "rotation-start";
    if (inRotation && !isAbsent && !isTempOut) return "rotation-available";
    if (inRotation && isAbsent) return "rotation-absent";
    if (inRotation && isTempOut) return "rotation-temp";
    if (isReturning) return "rotation-returning";
    if (isAbsent) return "absent";
    if (isTempOut) return "temp-out";
    return "default";
  }

  const sortedGuards = useMemo(
    () => [...guards].sort((a, b) => STATUS_ORDER[guardStatus(a.name)] - STATUS_ORDER[guardStatus(b.name)]),
    [guards, rotationNamesForDate, absentNames]
  );

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
          {/* Date + Start time */}
          <div className="grid gap-2 overflow-hidden" style={{ gridTemplateColumns: "3fr 2fr" }}>
            <div className="min-w-0 overflow-hidden">
              <label className="text-xs text-text-dim mb-1 block">תאריך</label>
              <input
                type="date"
                value={date}
                onChange={(e) => setDate(e.target.value)}
                className="input text-sm w-full py-1.5 min-w-0"
              />
            </div>
            <div className="min-w-0 overflow-hidden">
              <label className="text-xs text-text-dim mb-1 block">שעת התחלה</label>
              <input
                type="time"
                value={startTime}
                step={1800}
                onChange={(e) => setStartTime(e.target.value)}
                className="input text-sm w-full py-1.5 min-w-0"
              />
            </div>
          </div>

          {/* End time */}
          <div className="grid gap-2 overflow-hidden" style={{ gridTemplateColumns: "3fr 2fr" }}>
            <div />
            <div className="min-w-0 overflow-hidden">
              <label className="text-xs text-text-dim mb-1 block">שעת סיום</label>
              <input
                type="time"
                value={endTime}
                step={1800}
                onChange={(e) => setEndTime(e.target.value)}
                className="input text-sm w-full py-1.5 min-w-0"
              />
            </div>
          </div>

          {/* Guards */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-xs text-text-dim">
                שומרים ({selected.size} נבחרו)
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
              <p className="text-text-dim text-sm">טוען...</p>
            )}
            <div className="grid grid-cols-2 gap-2 max-h-52 overflow-y-auto">
              {sortedGuards.map((g) => {
                const status = guardStatus(g.name);
                const isSelected = selected.has(g.name);
                const statusClass = isSelected
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
                        {g.overloaded && <AlertTriangle size={12} className="text-warning flex-shrink-0" />}
                        {status === "default" && <span className="text-success text-[10px] font-bold">זמין</span>}
                        {status === "rotation-start" && <span className="text-danger text-[10px] font-bold">יוצא לסבב</span>}
                        {status === "rotation-available" && <span className="text-danger text-[10px] font-bold">בחופש</span>}
                        {status === "rotation-returning" && <span className="text-warning text-[10px] font-bold">חוזר מסבב</span>}
                        {(status === "absent" || status === "rotation-absent" || status === "rotation-temp") && <span className="text-danger text-[10px] font-bold">נעדר</span>}
                        {status === "temp-out" && <span className="text-warning text-[10px] font-bold">יצא</span>}
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
