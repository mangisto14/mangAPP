import type { RotationPeriodRange } from "./types";

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
  slotIndex: number;
  label: string;
  periodLabel: string;
  periodIndex: number;
  isActive: boolean;
}

interface ComputePeriodsInput {
  start_date: string;
  periods?: RotationPeriodRange[];
}

export function addDays(d: Date, n: number): Date {
  const r = new Date(d);
  r.setDate(r.getDate() + n);
  return r;
}

export function fmtShort(d: Date): string {
  return `${d.getDate()}/${d.getMonth() + 1}`;
}

function dayLabelHe(d: Date): string {
  const labels = ["א", "ב", "ג", "ד", "ה", "ו", "ש"];
  return labels[d.getDay()] ?? "";
}

function buildPeriodLabel(start: Date, end: Date): string {
  return `${dayLabelHe(start)}-${dayLabelHe(end)}`;
}

function legacyPeriods(startDate: string, count: number): Period[] {
  const origin = new Date(startDate + "T00:00:00");
  const now = new Date();

  const originDow = origin.getDay();
  const daysToSunday = originDow === 0 ? 0 : 7 - originDow;
  const anchor = addDays(origin, daysToSunday);

  const daysSinceAnchor = Math.floor((now.getTime() - anchor.getTime()) / 86400000);
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
      periodLabel: buildPeriodLabel(start, end),
      periodIndex: p,
      isActive: now >= start && now < end,
    });
  }
  return periods;
}

export function computePeriods(input: ComputePeriodsInput, count: number): Period[] {
  const base = legacyPeriods(input.start_date, count);
  const now = new Date();
  if (!input.periods || input.periods.length === 0) return base;

  const overrides = new Map<number, RotationPeriodRange>();
  input.periods.forEach((p) => overrides.set(p.slot_num, p));

  return base.map((period, idx) => {
    const ov = overrides.get(idx);
    if (!ov) return period;
    const start = new Date(ov.start_date + "T00:00:00");
    const end = new Date(ov.end_date + "T00:00:00");
    const periodIndex = idx % 3;
    return {
      start,
      end,
      slotIndex: idx,
      label: `${fmtShort(start)}-${fmtShort(end)}`,
      periodLabel: buildPeriodLabel(start, end),
      periodIndex,
      isActive: now >= start && now < end,
    };
  });
}

export function slotIndexForDate(
  dateStr: string,
  input: ComputePeriodsInput,
  slotsLen: number,
  periodCount = 60
): number | null {
  const target = new Date(dateStr + "T00:00:00");
  const periods = computePeriods(input, periodCount);
  const period = periods.find((p) => target >= p.start && target < p.end);
  if (!period) return null;
  return period.slotIndex % slotsLen;
}
