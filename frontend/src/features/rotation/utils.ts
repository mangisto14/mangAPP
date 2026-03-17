// ── Shared rotation period utilities ──────────────────────────────────────────

// צבעים לפי סוג תקופה: א-ג=כחול, ג-ה=כתום, ו-א=ירוק
export const PERIOD_COLORS = [
  "bg-primary/10 border-primary/25 text-primary-light",
  "bg-warning/10 border-warning/25 text-warning",
  "bg-success/10 border-success/25 text-success",
];

export const PERIOD_CONFIG = [
  { label: "א-ג", startDow: 0, days: 2 },
  { label: "ג-ה", startDow: 2, days: 2 },
  { label: "ו-א", startDow: 5, days: 2 },
] as const;

export interface Period {
  start: Date;
  end: Date;
  slotIndex: number;   // 0-based, maps to role.slots[slotIndex % slots.length]
  label: string;
  periodLabel: string;
  periodIndex: number; // 0 | 1 | 2
  isActive: boolean;
}

export function addDays(d: Date, n: number): Date {
  const r = new Date(d);
  r.setDate(r.getDate() + n);
  return r;
}

export function fmtShort(d: Date): string {
  return `${d.getDate()}/${d.getMonth() + 1}`;
}

/**
 * Compute `count` periods starting from the 3-week cycle that contains today.
 * slotIndex = flat position (0, 1, 2, …); use modulo against role.slots.length.
 */
export function computePeriods(startDate: string, count: number): Period[] {
  const origin = new Date(startDate + "T00:00:00");
  const now = new Date();

  // Cycle anchor = first Sunday on/after origin
  const originDow = origin.getDay();
  const daysToSunday = originDow === 0 ? 0 : 7 - originDow;
  const anchor = addDays(origin, daysToSunday);

  // Which 3-week cycle (21 days) contains today?
  const daysSinceAnchor = Math.floor(
    (now.getTime() - anchor.getTime()) / 86400000
  );
  const cycleNumber = Math.max(0, Math.floor(daysSinceAnchor / 21));
  const cycleStart = addDays(anchor, cycleNumber * 21);

  const periods: Period[] = [];
  for (let i = 0; i < count; i++) {
    const w = Math.floor(i / 3);
    const p = i % 3;
    const pc = PERIOD_CONFIG[p];
    const start = addDays(addDays(cycleStart, w * 7), pc.startDow);
    const end = addDays(start, 2);
    periods.push({
      start,
      end,
      slotIndex: i,
      label: `${fmtShort(start)}-${fmtShort(end)}`,
      periodLabel: pc.label,
      periodIndex: p,
      isActive: now >= start && now < end,
    });
  }
  return periods;
}

/**
 * Given a date string "YYYY-MM-DD" and a rotation start_date,
 * find the rotation slot index (wrapped to slotsLen) that covers that date.
 * Returns null if the date falls outside the computed periods.
 */
export function slotIndexForDate(
  dateStr: string,
  startDate: string,
  slotsLen: number,
  periodCount = 60
): number | null {
  const target = new Date(dateStr + "T00:00:00");
  const periods = computePeriods(startDate, periodCount);
  const period = periods.find((p) => target >= p.start && target < p.end);
  if (!period) return null;
  return period.slotIndex % slotsLen;
}
