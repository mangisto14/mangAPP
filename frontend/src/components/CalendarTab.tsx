import { useEffect, useState } from "react";
import { ChevronRight, ChevronLeft } from "lucide-react";
import { getShifts } from "../api";
import type { Shift } from "../types";
import { SkeletonShiftCards } from "./Skeleton";

const HE_DAYS = ["ראשון", "שני", "שלישי", "רביעי", "חמישי", "שישי", "שבת"];

function addDays(d: Date, n: number): Date {
  const r = new Date(d);
  r.setDate(r.getDate() + n);
  return r;
}

function toYMD(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

function fmtTime(iso: string): string {
  const d = new Date(iso);
  return `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
}

function getWeekStart(d: Date): Date {
  const s = new Date(d);
  s.setDate(s.getDate() - s.getDay()); // Sunday
  s.setHours(0, 0, 0, 0);
  return s;
}

// ── Shift Card ─────────────────────────────────────────────────────────────────
function ShiftCard({ shift }: { shift: Shift }) {
  const isPast = shift.is_past;
  return (
    <div
      className={`text-xs rounded-lg px-2 py-1.5 border transition-all
        ${isPast
          ? "bg-bg-base border-bg-border text-text-dim"
          : "bg-primary/10 border-primary/25 text-text"
        }`}
    >
      <div className="font-bold tabular-nums text-primary-light">
        {fmtTime(shift.start_time)}–{fmtTime(shift.end_time)}
      </div>
      <div className="truncate mt-0.5">{shift.names.join(", ")}</div>
    </div>
  );
}

// ── Day Column ─────────────────────────────────────────────────────────────────
function DayColumn({
  date,
  dayName,
  shifts,
  isToday,
}: {
  date: Date;
  dayName: string;
  shifts: Shift[];
  isToday: boolean;
}) {
  const dd = date.getDate();
  const mm = date.getMonth() + 1;

  return (
    <div className={`flex-1 min-w-[90px] flex flex-col gap-1.5`}>
      {/* Header */}
      <div
        className={`text-center py-2 rounded-xl sticky top-0 z-10
          ${isToday
            ? "bg-primary text-white font-bold shadow-md"
            : "bg-bg-base text-text-muted font-semibold border border-bg-border"
          }`}
      >
        <div className="text-xs">{dayName}</div>
        <div className="text-sm font-bold">{dd}/{mm}</div>
      </div>

      {/* Shifts */}
      <div className="space-y-1.5 min-h-[60px]">
        {shifts.length === 0 ? (
          <div className="text-center text-text-dim/30 text-xs py-3">—</div>
        ) : (
          shifts.map((s) => <ShiftCard key={s.id} shift={s} />)
        )}
      </div>
    </div>
  );
}

// ── CalendarTab ────────────────────────────────────────────────────────────────
export default function CalendarTab() {
  const [weekStart, setWeekStart] = useState<Date>(() => getWeekStart(new Date()));
  const [shifts, setShifts] = useState<Shift[]>([]);
  const [loading, setLoading] = useState(true);

  const weekEnd = addDays(weekStart, 7);
  const from = toYMD(weekStart);
  const to = toYMD(addDays(weekStart, 6));

  useEffect(() => {
    setLoading(true);
    getShifts("all", from, to)
      .then(setShifts)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [from, to]);

  const today = toYMD(new Date());

  // Build a map date→shifts
  const byDate: Record<string, Shift[]> = {};
  for (const s of shifts) {
    const d = s.start_time.slice(0, 10);
    if (!byDate[d]) byDate[d] = [];
    byDate[d].push(s);
  }

  const days = Array.from({ length: 7 }, (_, i) => addDays(weekStart, i));

  const prevWeek = () => setWeekStart((d) => addDays(d, -7));
  const nextWeek = () => setWeekStart((d) => addDays(d, 7));
  const goToday  = () => setWeekStart(getWeekStart(new Date()));

  const isCurrentWeek = toYMD(weekStart) === toYMD(getWeekStart(new Date()));

  // Total shifts this week
  const totalThisWeek = shifts.length;
  const futureThisWeek = shifts.filter((s) => !s.is_past).length;

  return (
    <div className="fade-in space-y-4">
      {/* Navigation */}
      <div className="flex items-center justify-between gap-3">
        <button
          onClick={prevWeek}
          className="p-2 rounded-xl bg-bg-card border border-bg-border text-text-dim hover:text-text hover:border-primary/40 transition-all min-h-[44px] min-w-[44px] flex items-center justify-center"
          aria-label="שבוע קודם"
        >
          <ChevronRight size={18} />
        </button>

        <div className="text-center flex-1">
          <p className="font-bold text-text text-sm">
            {from.split("-").reverse().join("/")} – {to.split("-").reverse().join("/")}
          </p>
          {!isCurrentWeek && (
            <button
              onClick={goToday}
              className="text-xs text-primary-light hover:underline mt-0.5"
            >
              חזור להיום
            </button>
          )}
        </div>

        <button
          onClick={nextWeek}
          className="p-2 rounded-xl bg-bg-card border border-bg-border text-text-dim hover:text-text hover:border-primary/40 transition-all min-h-[44px] min-w-[44px] flex items-center justify-center"
          aria-label="שבוע הבא"
        >
          <ChevronLeft size={18} />
        </button>
      </div>

      {/* Summary pills */}
      <div className="flex gap-2 flex-wrap">
        <span className="text-xs bg-bg-card border border-bg-border text-text-muted px-3 py-1 rounded-full">
          {totalThisWeek} משמרות השבוע
        </span>
        {futureThisWeek > 0 && (
          <span className="pill-future">
            🕐 {futureThisWeek} עתידיות
          </span>
        )}
      </div>

      {/* Calendar grid */}
      {loading ? (
        <SkeletonShiftCards />
      ) : (
        <div className="overflow-x-auto -mx-4 px-4">
          <div className="flex gap-2 pb-2" style={{ minWidth: "640px" }}>
            {days.map((day) => {
              const ymd = toYMD(day);
              return (
                <DayColumn
                  key={ymd}
                  date={day}
                  dayName={HE_DAYS[day.getDay()]}
                  shifts={byDate[ymd] ?? []}
                  isToday={ymd === today}
                />
              );
            })}
          </div>
        </div>
      )}

      {!loading && shifts.length === 0 && (
        <div className="card text-center text-text-dim py-10">
          אין משמרות לשבוע זה
        </div>
      )}
    </div>
  );
}
