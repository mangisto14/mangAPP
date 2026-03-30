import { useEffect, useRef, useState } from "react";
import { Pencil, Settings, PlusCircle, MinusCircle, RefreshCw, ChevronDown, CalendarDays, FileDown, FileUp, Copy } from "lucide-react";
import * as XLSX from "xlsx-js-style";
import {
  getRotation,
  updateRotationSlots,
  syncRotationGuards,
  syncScheduleGuards,
  updateRotationPeriod,
} from "./api";
import type { SyncResult } from "./api";
import { getGuards } from "../../api";
import type { Guard } from "../../types";
import type { RotationConfig } from "./types";
import { computePeriods, PERIOD_CONFIG, PERIOD_COLORS } from "./utils";
import { SkeletonRotation } from "../../components/Skeleton";
import type { Period } from "./utils";
import EditRotationModal from "./EditRotationModal";
import GuardAutocomplete from "./GuardAutocomplete";
import { useReadOnly } from "../../hooks/useReadOnly";

// ── Helpers ───────────────────────────────────────────────────────────────────

// ── EditPeriodModal ────────────────────────────────────────────────────────────

interface EditPeriodProps {
  config: RotationConfig;
  period: Period;
  guardNames: string[];
  guards: Guard[];
  onClose: () => void;
  onSaved: () => void;
}

function EditPeriodModal({ config, period, guardNames, guards, onClose, onSaved }: EditPeriodProps) {
  const [values, setValues] = useState<Record<number, string>>(
    Object.fromEntries(
      config.roles.map((r) => [r.id, (r.slots[period.slotIndex] ?? []).join(", ")])
    )
  );
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const handleSave = async () => {
    setSaving(true);
    setError("");
    try {
      for (const role of config.roles) {
        const needed = Math.max(9, period.slotIndex + 1);
        const newSlots = Array.from({ length: needed }, (_, i) => role.slots[i] ?? []);
        newSlots[period.slotIndex] = (values[role.id] ?? "")
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean);
        await updateRotationSlots(role.id, newSlots);
      }
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
        className="w-full bg-bg-card border-t border-bg-border rounded-t-2xl pb-8 slide-in
                   max-w-2xl mx-auto max-h-[80vh] flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-bg-border shrink-0">
          <h2 className="font-bold text-text text-lg">
            שיבוץ תקופה: {period.label} · {period.periodLabel}
          </h2>
          <button onClick={onClose} className="text-text-dim hover:text-text text-xl px-2">✕</button>
        </div>

        {/* Role inputs */}
        <div className="overflow-y-auto flex-1 p-5 space-y-3">
          {config.roles.map((role) => (
            <div key={role.id} className="flex items-start gap-3">
              <label className="text-sm font-bold text-text w-20 shrink-0 text-right pt-2">
                {role.name}
              </label>
              <GuardAutocomplete
                value={values[role.id] ?? ""}
                onChange={(v) => setValues((prev) => ({ ...prev, [role.id]: v }))}
                guardNames={guardNames}
                guards={guards}
                roleFilter={role.name}
              />
            </div>
          ))}
          {error && (
            <div className="text-danger text-sm bg-danger/10 border border-danger/30 rounded-xl p-3">
              {error}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-5 border-t border-bg-border shrink-0">
          <button onClick={handleSave} disabled={saving} className="btn-primary w-full">
            {saving ? "שומר..." : "💾 שמור שינויים"}
          </button>
        </div>
      </div>
    </div>
  );
}

interface EditPeriodRangeProps {
  config: RotationConfig;
  period: Period;
  onClose: () => void;
  onSaved: () => void;
}

function dateInputValue(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

function EditPeriodRangeModal({ config, period, onClose, onSaved }: EditPeriodRangeProps) {
  const [newPeriodStart, setNewPeriodStart] = useState(dateInputValue(period.start));
  const [newPeriodEnd, setNewPeriodEnd] = useState(dateInputValue(period.end));
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [overlapWarn, setOverlapWarn] = useState("");

  const handleSave = async () => {
    if (!newPeriodStart || !newPeriodEnd) {
      setError("יש להזין תאריך התחלה וסיום");
      return;
    }
    if (newPeriodEnd <= newPeriodStart) {
      setError("תאריך סיום חייב להיות אחרי תאריך ההתחלה");
      return;
    }
    const nextStart = new Date(`${newPeriodStart}T00:00:00`).getTime();
    const nextEnd = new Date(`${newPeriodEnd}T00:00:00`).getTime();
    const overlapping = (config.periods ?? []).find((p) => {
      if (p.slot_num === period.slotIndex) return false;
      const otherStart = new Date(`${p.start_date}T00:00:00`).getTime();
      const otherEnd = new Date(`${p.end_date}T00:00:00`).getTime();
      return nextStart < otherEnd && nextEnd > otherStart;
    });
    if (overlapping && !overlapWarn) {
      // Show warning but allow user to confirm and save anyway
      setOverlapWarn(`הטווח חופף לתקופה ${overlapping.slot_num + 1}: ${overlapping.start_date} עד ${overlapping.end_date}. לחץ שמור שוב לאישור.`);
      return;
    }
    setOverlapWarn("");
    setSaving(true);
    setError("");
    try {
      await updateRotationPeriod(period.slotIndex, newPeriodStart, newPeriodEnd);
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
        className="w-full bg-bg-card border-t border-bg-border rounded-t-2xl pb-8 slide-in
                   max-w-2xl mx-auto max-h-[80vh] flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between p-5 border-b border-bg-border shrink-0">
          <h2 className="font-bold text-text text-lg">עדכון טווח חופשה לתקופה</h2>
          <button onClick={onClose} className="text-text-dim hover:text-text text-xl px-2">✕</button>
        </div>
        <div className="overflow-y-auto flex-1 p-5 space-y-4">
          <div className="card space-y-2">
            <div className="text-xs text-text-dim">טווח נוכחי</div>
            <div className="text-sm font-semibold text-text">{period.label} · {period.periodLabel}</div>
          </div>
          <div>
            <label className="text-xs text-text-dim mb-1 block">תאריך התחלה חדש לתקופה</label>
            <input
              type="date"
              value={newPeriodStart}
              onChange={(e) => setNewPeriodStart(e.target.value)}
              className="input text-sm w-full"
            />
          </div>
          <div>
            <label className="text-xs text-text-dim mb-1 block">תאריך סיום חדש לתקופה</label>
            <input
              type="date"
              value={newPeriodEnd}
              onChange={(e) => setNewPeriodEnd(e.target.value)}
              className="input text-sm w-full"
            />
          </div>
          <div className="text-xs text-text-dim bg-primary/10 border border-primary/20 rounded-xl px-3 py-2">
            השינוי נשמר בנפרד לתקופה זו בלבד.
          </div>
          {overlapWarn && (
            <div className="text-warning text-sm bg-warning/10 border border-warning/30 rounded-xl p-3">
              ⚠ {overlapWarn}
            </div>
          )}
          {error && (
            <div className="text-danger text-sm bg-danger/10 border border-danger/30 rounded-xl p-3">
              {error}
            </div>
          )}
        </div>
        <div className="p-5 border-t border-bg-border shrink-0">
          <button onClick={handleSave} disabled={saving} className="btn-primary w-full">
            {saving ? "שומר..." : overlapWarn ? "שמור בכל זאת" : "אישור ועדכון טווח"}
          </button>
        </div>
      </div>
    </div>
  );
}

interface DuplicatePeriodModalProps {
  config: RotationConfig;
  sourcePeriod: Period;
  periods: Period[];
  onClose: () => void;
  onSaved: () => void;
}

function DuplicatePeriodModal({ config, sourcePeriod, periods, onClose, onSaved }: DuplicatePeriodModalProps) {
  const targetPeriods = periods.filter((p) => p.slotIndex !== sourcePeriod.slotIndex);
  const [selectedTargets, setSelectedTargets] = useState<number[]>([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const toggleTarget = (slotIndex: number) => {
    setSelectedTargets((prev) =>
      prev.includes(slotIndex) ? prev.filter((n) => n !== slotIndex) : [...prev, slotIndex]
    );
  };

  const handleSave = async () => {
    if (selectedTargets.length === 0) {
      setError("יש לבחור לפחות תקופת יעד אחת");
      return;
    }

    const targetLabels = targetPeriods
      .filter((p) => selectedTargets.includes(p.slotIndex))
      .map((p) => `${p.slotIndex + 1} (${p.periodLabel})`)
      .join(", ");

    const ok = window.confirm(
      `לשכפל את תקופה ${sourcePeriod.slotIndex + 1} (${sourcePeriod.periodLabel}) לתקופות: ${targetLabels}?`
    );
    if (!ok) return;

    setSaving(true);
    setError("");
    try {
      for (const role of config.roles) {
        const needed = Math.max(
          9,
          sourcePeriod.slotIndex + 1,
          ...selectedTargets.map((slot) => slot + 1)
        );
        const newSlots = Array.from({ length: needed }, (_, i) => role.slots[i] ?? []);
        const sourceNames = role.slots[sourcePeriod.slotIndex] ?? [];
        for (const targetSlot of selectedTargets) {
          newSlots[targetSlot] = [...sourceNames];
        }
        await updateRotationSlots(role.id, newSlots);
      }
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
        className="w-full bg-bg-card border-t border-bg-border rounded-t-2xl pb-8 slide-in
                   max-w-2xl mx-auto max-h-[80vh] flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between p-5 border-b border-bg-border shrink-0">
          <h2 className="font-bold text-text text-lg">
            שכפול תקופה {sourcePeriod.slotIndex + 1} · {sourcePeriod.periodLabel}
          </h2>
          <button onClick={onClose} className="text-text-dim hover:text-text text-xl px-2">✕</button>
        </div>

        <div className="overflow-y-auto flex-1 p-5 space-y-4">
          <div className="text-xs text-text-dim bg-primary/10 border border-primary/20 rounded-xl px-3 py-2">
            יועתקו רק השיבוצים לתקופות היעד. טווחי התאריכים לא ישתנו.
          </div>

          <div className="space-y-2">
            {targetPeriods.map((p) => {
              const checked = selectedTargets.includes(p.slotIndex);
              return (
                <label
                  key={p.slotIndex}
                  className={`flex items-center justify-between gap-3 rounded-xl border px-3 py-2 cursor-pointer transition-all
                    ${checked ? "border-primary/40 bg-primary/10" : "border-bg-border bg-bg-base/30 hover:bg-bg-base/60"}`}
                >
                  <div className="text-sm text-text">
                    תקופה {p.slotIndex + 1} · {p.label} · {p.periodLabel}
                  </div>
                  <input
                    type="checkbox"
                    checked={checked}
                    onChange={() => toggleTarget(p.slotIndex)}
                    className="accent-primary w-4 h-4"
                  />
                </label>
              );
            })}
          </div>

          {error && (
            <div className="text-danger text-sm bg-danger/10 border border-danger/30 rounded-xl p-3">
              {error}
            </div>
          )}
        </div>

        <div className="p-5 border-t border-bg-border shrink-0">
          <button onClick={handleSave} disabled={saving} className="btn-primary w-full">
            {saving ? "משכפל..." : "שכפל לתקופות שנבחרו"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── exportToExcel ─────────────────────────────────────────────────────────────

// Excel fill colors per period type (א-ג / ג-ה / ו-א)
const PERIOD_EXCEL_COLORS = [
  { header: "BFDBFE", cell: "EFF6FF" }, // blue  (א-ג)
  { header: "FDE68A", cell: "FFFBEB" }, // amber (ג-ה)
  { header: "BBF7D0", cell: "F0FDF4" }, // green (ו-א)
];


function exportToExcel(config: RotationConfig, periods: Period[]) {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const ws: Record<string, any> = {};
  const merges: { s: { r: number; c: number }; e: { r: number; c: number } }[] = [];

  const thin = { style: "thin", color: { rgb: "CBD5E1" } };
  const border = { top: thin, bottom: thin, left: thin, right: thin };

  const setCell = (r: number, c: number, v: string, s?: object) => {
    ws[XLSX.utils.encode_cell({ c, r })] = { v, t: "s", ...(s ? { s } : {}) };
  };

  const headerStyle = (bgColor: string) => ({
    font: { bold: true, sz: 11 },
    fill: { patternType: "solid", fgColor: { rgb: bgColor } },
    alignment: { horizontal: "center", vertical: "center" },
    border,
  });

  // Header row
  setCell(0, 0, "תפקיד", {
    font: { bold: true, sz: 11 },
    fill: { patternType: "solid", fgColor: { rgb: "E2E8F0" } },
    alignment: { horizontal: "right", vertical: "center" },
    border,
  });
  periods.forEach((p, ci) => {
    setCell(0, ci + 1, p.label, headerStyle(PERIOD_EXCEL_COLORS[p.periodIndex].header));
  });

  // Data rows — one row per guard, role cell merged vertically
  let row = 1;
  for (const [roleIdx, role] of config.roles.entries()) {
    if (roleIdx > 0) row += 1; // empty separator row between roles
    const maxGuards = Math.max(1, ...periods.map((p) => (role.slots[p.slotIndex] ?? []).length));

    setCell(row, 0, role.name, {
      font: { bold: true, sz: 10 },
      fill: { patternType: "solid", fgColor: { rgb: "F1F5F9" } },
      alignment: { horizontal: "right", vertical: "center" },
      border,
    });
    if (maxGuards > 1) {
      merges.push({ s: { r: row, c: 0 }, e: { r: row + maxGuards - 1, c: 0 } });
    }

    periods.forEach((p, ci) => {
      const names = role.slots[p.slotIndex] ?? [];
      const { cell: cellColor } = PERIOD_EXCEL_COLORS[p.periodIndex];
      for (let i = 0; i < maxGuards; i++) {
        setCell(row + i, ci + 1, names[i] ?? "", {
          fill: { patternType: "solid", fgColor: { rgb: cellColor } },
          alignment: { horizontal: "center", vertical: "center" },
          border,
        });
      }
    });

    row += maxGuards;
  }

  ws["!ref"] = XLSX.utils.encode_range({ s: { r: 0, c: 0 }, e: { r: row - 1, c: periods.length } });
  ws["!merges"] = merges;
  ws["!cols"] = [{ wch: 16 }, ...periods.map(() => ({ wch: 20 }))];

  const filename = `סבב_חופשה_${new Date().toISOString().slice(0, 10)}.xlsx`;
  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, ws, "סבב חופשה");

  // Try native share (mobile) → fallback to download (desktop)
  const buf: ArrayBuffer = XLSX.write(wb, { bookType: "xlsx", type: "array" });
  const file = new File([buf], filename, {
    type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  });

  if (navigator.canShare?.({ files: [file] })) {
    navigator.share({ files: [file], title: "סבב חופשה" }).catch(() => {
      XLSX.writeFile(wb, filename);
    });
  } else {
    XLSX.writeFile(wb, filename);
  }
}

// ── importFromExcel ───────────────────────────────────────────────────────────

interface ImportPreview {
  roles: { id: number; name: string; slotsMap: Map<number, string[]> }[];
  // slotIndex → { start, end } parsed from file headers
  periodRanges: Map<number, { start: string; end: string }>;
  matchedPeriods: number;
  totalPeriods: number;
}

// Parse "29/3" → { day:29, month:3 } or null
function parseDayMonth(s: string): { day: number; month: number } | null {
  const parts = s.trim().split("/");
  if (parts.length !== 2) return null;
  const day = parseInt(parts[0], 10);
  const month = parseInt(parts[1], 10);
  if (isNaN(day) || isNaN(month)) return null;
  return { day, month };
}

async function parseImportFile(
  file: File,
  config: RotationConfig
): Promise<ImportPreview> {
  const buf = await file.arrayBuffer();
  const wb = XLSX.read(buf, { type: "array" });
  const ws = wb.Sheets[wb.SheetNames[0]];
  const data: string[][] = XLSX.utils.sheet_to_json(ws, { header: 1, defval: "" }) as string[][];

  if (data.length < 2) throw new Error("הקובץ ריק או לא תקין");

  const headerRow = data[0];

  // Parse "29/3-1/4" → { start: "YYYY-03-29", end: "YYYY-04-01" } using current year
  function parseHeaderRange(label: string): { start: string; end: string } | null {
    const trimmed = label.trim();
    const slashIdx = trimmed.indexOf("/");
    if (slashIdx < 0) return null;
    const dashIdx = trimmed.indexOf("-", slashIdx);
    if (dashIdx < 0) return null;
    const s = parseDayMonth(trimmed.substring(0, dashIdx));
    const e = parseDayMonth(trimmed.substring(dashIdx + 1));
    if (!s || !e) return null;
    const year = new Date().getFullYear();
    const pad = (n: number) => String(n).padStart(2, "0");
    const endYear = e.month < s.month ? year + 1 : year;
    return {
      start: `${year}-${pad(s.month)}-${pad(s.day)}`,
      end: `${endYear}-${pad(e.month)}-${pad(e.day)}`,
    };
  }

  // Always use positional mapping: column 1 → slot 0, column 2 → slot 1, …
  // This is reliable regardless of whether periods exist in DB or not.
  const periodRanges = new Map<number, { start: string; end: string }>();
  const numDataCols = headerRow.length - 1; // exclude role-name column
  const colToSlot: (number | null)[] = headerRow.map((_h, ci) => {
    if (ci === 0) return null;
    return ci - 1; // slot index = column index - 1
  });
  const matchedPeriods = numDataCols;

  // Parse date ranges from each column header
  for (let ci = 1; ci < headerRow.length; ci++) {
    const range = parseHeaderRange(String(headerRow[ci]));
    if (range) periodRanges.set(ci - 1, range);
  }

  const roleMap = new Map(config.roles.map((r) => [r.name.trim(), r]));
  const roleSlots = new Map<number, Map<number, string[]>>(
    config.roles.map((r) => [r.id, new Map()])
  );

  let currentRoleId: number | null = null;
  for (let ri = 1; ri < data.length; ri++) {
    const row = data[ri];
    const roleCell = String(row[0] ?? "").trim();
    if (roleCell) {
      // Try exact match first, then case-insensitive
      const role = roleMap.get(roleCell) ??
        [...roleMap.entries()].find(([k]) => k.toLowerCase() === roleCell.toLowerCase())?.[1];
      currentRoleId = role ? role.id : null;
    }
    if (currentRoleId === null) continue;
    const slotsForRole = roleSlots.get(currentRoleId)!;
    for (let ci = 1; ci < headerRow.length; ci++) {
      const slotIdx = colToSlot[ci];
      if (slotIdx === null) continue;
      const name = String(row[ci] ?? "").trim();
      if (name) {
        if (!slotsForRole.has(slotIdx)) slotsForRole.set(slotIdx, []);
        slotsForRole.get(slotIdx)!.push(name);
      }
    }
  }

  const roles = config.roles.map((r) => ({
    id: r.id,
    name: r.name,
    slotsMap: roleSlots.get(r.id)!,
  }));

  return { roles, periodRanges, matchedPeriods, totalPeriods: periods.length };
}

async function applyImport(preview: ImportPreview, config: RotationConfig) {
  // 1. Write guard names per slot for every role
  for (const { id, slotsMap } of preview.roles) {
    const role = config.roles.find((r) => r.id === id);
    if (!role) continue;
    const maxSlot = Math.max(
      role.slots.length - 1,
      ...Array.from(slotsMap.keys())
    );
    const newSlots = Array.from({ length: maxSlot + 1 }, (_, i) =>
      slotsMap.has(i) ? slotsMap.get(i)! : (role.slots[i] ?? [])
    );
    await updateRotationSlots(id, newSlots);
  }

  // 2. Save period date ranges parsed from file headers (always overwrite from file)
  for (const [slotIdx, { start, end }] of preview.periodRanges.entries()) {
    await updateRotationPeriod(slotIdx, start, end);
  }
}

// ── SyncModal ──────────────────────────────────────────────────────────────────

function SyncModal({ result, onClose }: { result: SyncResult; onClose: () => void }) {
  return (
    <div className="fixed inset-0 z-50 bg-black/60 flex items-end" onClick={onClose}>
      <div
        className="w-full bg-bg-card border-t border-bg-border rounded-t-2xl pb-8 slide-in
                   max-w-2xl mx-auto max-h-[80vh] flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between p-5 border-b border-bg-border shrink-0">
          <h2 className="font-bold text-text text-lg">תוצאות סנכרון סבב ↔ כוח אדם</h2>
          <button onClick={onClose} className="text-text-dim hover:text-text text-xl px-2">✕</button>
        </div>
        <div className="overflow-y-auto flex-1 p-5 space-y-5">

          {/* Updated */}
          <div>
            <h3 className="text-sm font-bold text-text mb-2 flex items-center gap-2">
              <span className="text-success">✓</span>
              {result.updated.length > 0
                ? `${result.updated.length} אנשים עודכנו בכוח האדם`
                : "לא עודכנו תפקידים"}
            </h3>
            {result.updated.length > 0 && (
              <div className="space-y-1">
                {result.updated.map((u) => (
                  <div key={u.name} className="flex items-center gap-2 text-xs bg-success/10 border border-success/25 rounded-xl px-3 py-2">
                    <span className="font-semibold text-text">{u.name}</span>
                    <span className="text-text-dim">{u.old_role ?? "ללא תפקיד"}</span>
                    <span className="text-text-dim">→</span>
                    <span className="text-success font-semibold">{u.new_role}</span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Conflicts */}
          {result.conflicts.length > 0 && (
            <div>
              <h3 className="text-sm font-bold text-warning mb-2 flex items-center gap-2">
                <span>⚠</span> {result.conflicts.length} התנגשויות — שם מופיע בכמה תפקידים
              </h3>
              <div className="space-y-1">
                {result.conflicts.map((c) => (
                  <div key={c.name} className="text-xs bg-warning/10 border border-warning/25 rounded-xl px-3 py-2">
                    <span className="font-semibold text-text">{c.name}</span>
                    <span className="text-warning mr-2">{c.roles.join(", ")}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Unknown in rotation */}
          {result.unknown_in_rotation.length > 0 && (
            <div>
              <h3 className="text-sm font-bold text-text-dim mb-2 flex items-center gap-2">
                <span>❓</span> {result.unknown_in_rotation.length} שמות בסבב שלא קיימים בכוח האדם
              </h3>
              <div className="flex flex-wrap gap-2">
                {result.unknown_in_rotation.map((n) => (
                  <span key={n} className="text-xs bg-bg-base border border-bg-border text-text-dim px-2.5 py-1 rounded-full">
                    {n}
                  </span>
                ))}
              </div>
            </div>
          )}

        </div>
        <div className="p-5 border-t border-bg-border shrink-0">
          <button onClick={onClose} className="btn-primary w-full">סגור</button>
        </div>
      </div>
    </div>
  );
}

// ── RotationTab ───────────────────────────────────────────────────────────────

export default function RotationTab() {
  const [config, setConfig] = useState<RotationConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [editSlot, setEditSlot] = useState<number | null>(null);
  const [showSettings, setShowSettings] = useState(false);
  const [extraWeeks, setExtraWeeks] = useState(0);
  const [syncing, setSyncing] = useState(false);
  const [syncingSchedule, setSyncingSchedule] = useState(false);
  const [addingWeek, setAddingWeek] = useState(false);
  const [syncResult, setSyncResult] = useState<SyncResult | null>(null);
  const [guardNames, setGuardNames] = useState<string[]>([]);
  const [guards, setGuards] = useState<Guard[]>([]);
  const [showUnassigned, setShowUnassigned] = useState(false);
  const [editRangePeriod, setEditRangePeriod] = useState<Period | null>(null);
  const [duplicateSourcePeriod, setDuplicateSourcePeriod] = useState<Period | null>(null);
  const [showActionsMenu, setShowActionsMenu] = useState(false);
  const [showAddWeekModal, setShowAddWeekModal] = useState(false);
  const [addWeekPeriods, setAddWeekPeriods] = useState<{ start: string; end: string }[]>([]);
  const [importPreview, setImportPreview] = useState<ImportPreview | null>(null);
  const [importing, setImporting] = useState(false);
  const importRef = useRef<HTMLInputElement>(null);
  const activePeriodRef = useRef<HTMLTableCellElement>(null);
  const readOnly = useReadOnly();

  const load = async () => {
    setLoading(true);
    setError("");
    try {
      const [cfg, guardList] = await Promise.all([getRotation(), getGuards()]);
      setConfig(cfg);
      setGuards(guardList);
      setGuardNames(guardList.map((g) => g.name));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  };

  const handleSync = async () => {
    setSyncing(true);
    try {
      const result = await syncRotationGuards();
      setSyncResult(result);
      load();
    } catch (e) {
      alert((e as Error).message);
    } finally {
      setSyncing(false);
    }
  };

  const handleSyncSchedule = async () => {
    setSyncingSchedule(true);
    try {
      const result = await syncScheduleGuards();
      setSyncResult(result);
      load();
    } catch (e) {
      alert((e as Error).message);
    } finally {
      setSyncingSchedule(false);
    }
  };

  const handleAddWeek = async (newPeriods: { start: string; end: string }[]) => {
    if (!config) return;
    setShowAddWeekModal(false);
    setAddingWeek(true);
    try {
      const maxRoleSlots = config.roles.reduce((max, role) => Math.max(max, role.slots.length), 0);
      const currentSlotCount = Math.max(9, config.periods?.length ?? 0, maxRoleSlots);
      const nextSlotCount = currentSlotCount + newPeriods.length;

      for (const role of config.roles) {
        const newSlots = Array.from({ length: nextSlotCount }, (_, i) => role.slots[i] ?? []);
        await updateRotationSlots(role.id, newSlots);
      }

      for (let i = 0; i < newPeriods.length; i++) {
        const { start, end } = newPeriods[i];
        if (start && end) {
          await updateRotationPeriod(currentSlotCount + i, start, end);
        }
      }

      await load();
    } catch (e) {
      alert((e as Error).message);
    } finally {
      setAddingWeek(false);
    }
  };

  const handleImportFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !config) return;
    e.target.value = "";
    const numP = Math.max(9 + extraWeeks * 3, config.periods?.length ?? 0);
    const currentPeriods = computePeriods(config, numP);
    try {
      const preview = await parseImportFile(file, config);
      setImportPreview(preview);
    } catch (err) {
      alert((err as Error).message);
    }
  };

  const handleImportConfirm = async () => {
    if (!importPreview || !config) return;
    setImporting(true);
    try {
      await applyImport(importPreview, config);
      setImportPreview(null);
      await load();
    } catch (err) {
      alert((err as Error).message);
    } finally {
      setImporting(false);
    }
  };

  useEffect(() => { load(); }, []);
  useEffect(() => {
    if (!loading && activePeriodRef.current) {
      activePeriodRef.current.scrollIntoView({ inline: "center", behavior: "smooth", block: "nearest" });
    }
  }, [loading]);

  if (loading) return <SkeletonRotation />;
  if (error || !config) return <div className="fade-in card border-danger/30 text-danger">{error || "שגיאה"}</div>;

  const numPeriods = Math.max(9 + extraWeeks * 3, config.periods?.length ?? 0);
  const periods = computePeriods(config, numPeriods);
  const activePeriod = periods.find((p) => p.isActive);
  const activeIdx = periods.findIndex((p) => p.isActive);
  const nextPeriodIdx = activeIdx >= 0 && activeIdx + 1 < periods.length ? activeIdx + 1 : -1;

  // Build name → role map for mismatch detection
  const guardRoleMap = new Map<string, string | null>(
    guards.map((g) => [g.name, g.role])
  );

  // Compute unassigned guards
  const assignedNames = new Set<string>();
  for (const role of config.roles) {
    for (const slot of role.slots) {
      for (const name of slot) assignedNames.add(name);
    }
  }
  const unassigned = guardNames.filter((n) => !assignedNames.has(n));

  return (
    <div className="fade-in space-y-4">
      {/* Hidden file input for import */}
      <input
        ref={importRef}
        type="file"
        accept=".xlsx"
        className="hidden"
        onChange={handleImportFile}
      />

      {/* Toolbar */}
      <div className="flex items-center justify-between gap-2 flex-wrap">
        {activePeriod ? (
          <div className="text-xs font-semibold text-primary-light bg-primary/10 border border-primary/20
                          px-3 py-1.5 rounded-xl inline-flex items-center gap-2">
            <span className="w-2 h-2 bg-primary rounded-full animate-pulse" />
            תקופה פעילה: {activePeriod.label} · {activePeriod.periodLabel}
          </div>
        ) : <div />}
        <div className="flex items-center gap-2">
          {/* Actions menu — export always visible; edit actions hidden for viewers */}
          <div className="relative">
            <button
              onClick={() => setShowActionsMenu((v) => !v)}
              disabled={syncing || syncingSchedule}
              className="flex items-center gap-1.5 bg-bg-card border border-bg-border px-3 py-1.5
                         rounded-xl text-sm font-semibold text-text-dim hover:text-text
                         hover:border-primary/40 transition-all disabled:opacity-50"
            >
              פעולות
              <ChevronDown size={12} className={`transition-transform ${showActionsMenu ? "rotate-180" : ""}`} />
            </button>
            {showActionsMenu && (
              <>
                <div className="fixed inset-0 z-10" onClick={() => setShowActionsMenu(false)} />
                <div className="absolute left-0 top-full mt-1 bg-bg-card border border-bg-border
                                rounded-xl shadow-lg z-20 min-w-[140px] overflow-hidden">
                  {!readOnly && (
                    <>
                      <button
                        onClick={() => {
                          setShowActionsMenu(false);
                          // compute default start from last period end
                          const lastPeriod = periods.length > 0 ? periods[periods.length - 1] : null;
                          const base = lastPeriod ? new Date(lastPeriod.end) : new Date();
                          const d = (n: number) => {
                            const dt = new Date(base); dt.setDate(dt.getDate() + n);
                            return dateInputValue(dt);
                          };
                          setAddWeekPeriods([
                            { start: d(0), end: d(2) },
                            { start: d(2), end: d(4) },
                            { start: d(4), end: d(7) },
                          ]);
                          setShowAddWeekModal(true);
                        }}
                        disabled={addingWeek}
                        className="w-full text-right px-4 py-2.5 text-sm text-text-dim hover:text-text
                                   hover:bg-bg-base/60 transition-colors disabled:opacity-50 flex items-center gap-2 justify-end"
                      >
                        {addingWeek ? "מוסיף..." : "הוסף שבוע"}
                        <PlusCircle size={13} />
                      </button>
                      <button
                        onClick={() => { setShowActionsMenu(false); setExtraWeeks((n) => n - 1); }}
                        disabled={extraWeeks === 0}
                        className="w-full text-right px-4 py-2.5 text-sm text-text-dim hover:text-text
                                   hover:bg-bg-base/60 transition-colors disabled:opacity-40 flex items-center gap-2 justify-end"
                      >
                        הסר שבוע
                        <MinusCircle size={13} />
                      </button>
                      <div className="border-t border-bg-border/50" />
                      <button
                        onClick={() => { setShowActionsMenu(false); handleSync(); }}
                        disabled={syncing}
                        className="w-full text-right px-4 py-2.5 text-sm text-text-dim hover:text-text
                                   hover:bg-bg-base/60 transition-colors disabled:opacity-50 flex items-center gap-2 justify-end"
                      >
                        סנכרן סבב
                        <RefreshCw size={13} className={syncing ? "animate-spin" : ""} />
                      </button>
                      <button
                        onClick={() => { setShowActionsMenu(false); handleSyncSchedule(); }}
                        disabled={syncingSchedule}
                        className="w-full text-right px-4 py-2.5 text-sm text-text-dim hover:text-text
                                   hover:bg-bg-base/60 transition-colors disabled:opacity-50 flex items-center gap-2 justify-end"
                      >
                        סנכרן לוח
                        <CalendarDays size={13} />
                      </button>
                      <div className="border-t border-bg-border/50" />
                    </>
                  )}
                  <button
                    onClick={() => { setShowActionsMenu(false); exportToExcel(config, periods); }}
                    className="w-full text-right px-4 py-2.5 text-sm text-text-dim hover:text-text
                               hover:bg-bg-base/60 transition-colors flex items-center gap-2 justify-end"
                  >
                    ייצוא
                    <FileDown size={13} />
                  </button>
                  {!readOnly && (
                    <button
                      onClick={() => { setShowActionsMenu(false); importRef.current?.click(); }}
                      className="w-full text-right px-4 py-2.5 text-sm text-text-dim hover:text-text
                                 hover:bg-bg-base/60 transition-colors flex items-center gap-2 justify-end"
                    >
                      ייבוא
                      <FileUp size={13} />
                    </button>
                  )}
                </div>
              </>
            )}
          </div>
          {/* Settings button — hidden for viewers */}
          {!readOnly && (
            <button
              onClick={() => setShowSettings(true)}
              className="flex items-center gap-1.5 bg-bg-card border border-bg-border px-3 py-1.5
                         rounded-xl text-sm font-semibold text-text-dim hover:text-text
                         hover:border-primary/40 transition-all"
            >
              <Settings size={14} />
              הגדרות
            </button>
          )}
        </div>
      </div>

      {/* Legend + unassigned button */}
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <div className="flex gap-3 flex-wrap">
          {PERIOD_CONFIG.map((pc, i) => (
            <span key={i} className={`text-xs font-semibold px-3 py-1 rounded-full border ${PERIOD_COLORS[i]}`}>
              {pc.label}
            </span>
          ))}
        </div>
        <button
          onClick={() => setShowUnassigned((v) => !v)}
          className={`text-xs font-semibold px-3 py-1.5 rounded-xl border transition-all
            ${unassigned.length > 0
              ? "text-warning bg-warning/10 border-warning/25"
              : "text-success bg-success/10 border-success/25"}`}
        >
          {unassigned.length > 0
            ? `${unassigned.length} לא שובצו`
            : "כולם שובצו ✓"}
        </button>
      </div>

      {/* Unassigned report */}
      {showUnassigned && (
        <div className="card slide-in">
          <h3 className="font-semibold text-text text-sm mb-2">אנשים שלא שובצו לאף משבצת</h3>
          {unassigned.length === 0 ? (
            <p className="text-success text-sm">כל כוח האדם משובץ בסבב!</p>
          ) : (
            <div className="flex flex-wrap gap-2">
              {unassigned.map((name) => (
                <span key={name} className="text-xs bg-warning/10 text-warning border border-warning/25
                                            px-2.5 py-1 rounded-full font-medium">
                  {name}
                </span>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Table */}
      <div className="overflow-x-auto -mx-4 px-4">
        <table className="w-full text-sm border-collapse" style={{ minWidth: "700px" }}>
          <thead>
            <tr>
              <th className="text-right py-2 px-3 text-text-dim font-semibold text-xs w-20
                             sticky right-0 bg-bg-deep z-10">
                תפקיד
              </th>
              {periods.map((p, pi) => {
                const isNext = pi === nextPeriodIdx;
                return (
                <th
                  key={p.slotIndex}
                  ref={p.isActive ? activePeriodRef : undefined}
                  className={`text-center py-2 px-1 text-xs font-semibold whitespace-nowrap
                    ${p.isActive
                      ? "text-primary bg-primary/10 rounded-t-lg border-t border-x border-primary/25"
                      : isNext
                      ? "text-success bg-success/5 rounded-t-lg border-t border-x border-success/20"
                      : "text-text-dim"
                    }`}
                >
                  <div className="flex flex-col items-center gap-0.5">
                    {isNext && (
                      <span className="text-[9px] font-bold text-success bg-success/15 px-1.5 py-0.5 rounded-full mb-0.5">
                        הבא
                      </span>
                    )}
                    {readOnly ? (
                      <span>{p.label}</span>
                    ) : (
                      <button
                        onClick={() => setEditRangePeriod(p)}
                        className="hover:text-primary transition-colors underline decoration-dotted underline-offset-2"
                        title="עדכון טווח תאריכים לחופשה"
                      >
                        {p.label}
                      </button>
                    )}
                    <span className={`text-[10px] font-normal
                      ${p.isActive ? "text-primary-light" : isNext ? "text-success/70" : "text-text-dim/60"}`}>
                      {p.periodLabel}
                    </span>
                    {!readOnly && (
                      <div className="flex items-center gap-1 mt-0.5">
                        <button
                          onClick={() => setEditRangePeriod(p)}
                          className="p-0.5 text-text-dim/40 hover:text-primary transition-colors"
                          title="עדכן טווח תאריכים"
                        >
                          <CalendarDays size={10} />
                        </button>
                        <button
                          onClick={() => setEditSlot(p.slotIndex)}
                          className="p-0.5 text-text-dim/40 hover:text-primary transition-colors"
                          title="ערוך תקופה"
                        >
                          <Pencil size={10} />
                        </button>
                        <button
                          onClick={() => setDuplicateSourcePeriod(p)}
                          className="p-0.5 text-text-dim/40 hover:text-primary transition-colors"
                          title="שכפל תקופה"
                        >
                          <Copy size={10} />
                        </button>
                      </div>
                    )}
                  </div>
                </th>
                );
              })}
            </tr>
          </thead>
          <tbody>
            {config.roles.map((role) => (
              <tr key={role.id} className="border-t border-bg-border/50">
                <td className="py-2 px-3 font-bold text-text text-xs sticky right-0 bg-bg-deep z-10">
                  {role.name}
                </td>
                {periods.map((p) => {
                  const names = role.slots[p.slotIndex] ?? [];
                  return (
                    <td
                      key={p.slotIndex}
                      onClick={() => !readOnly && setEditSlot(p.slotIndex)}
                      className={`py-2 px-1 text-center align-top transition-colors
                        ${!readOnly ? "cursor-pointer hover:bg-bg-card/60" : ""}
                        ${p.isActive ? "bg-primary/5 border-x border-primary/25" : ""}`}
                    >
                      {names.length === 0 ? (
                        <span className="text-text-dim/30 text-xs">—</span>
                      ) : (
                        <div className="space-y-0.5">
                          {names.map((name) => {
                            const guardRole = guardRoleMap.get(name);
                            const mismatch = guardRole !== undefined && guardRole !== null && guardRole !== role.name;
                            return (
                              <div
                                key={name}
                                className={`text-xs px-1.5 py-0.5 rounded-lg border font-medium
                                  ${mismatch
                                    ? "bg-warning/10 border-warning/30 text-warning"
                                    : PERIOD_COLORS[p.periodIndex]
                                  }`}
                                title={mismatch ? `תפקיד אמיתי: ${guardRole || "ללא תפקיד"}` : undefined}
                              >
                                <div className="flex items-center gap-0.5">
                                  {mismatch && <span className="text-[9px]">⚠</span>}
                                  <span>{name}</span>
                                </div>
                                {guardRole && (
                                  <span className={`text-[9px] opacity-60 block leading-tight
                                    ${mismatch ? "text-warning" : ""}`}>
                                    {guardRole}
                                  </span>
                                )}
                              </div>
                            );
                          })}
                        </div>
                      )}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Edit period modal */}
      {editSlot !== null && (
        <EditPeriodModal
          config={config}
          period={periods[editSlot]}
          guardNames={guardNames}
          guards={guards}
          onClose={() => setEditSlot(null)}
          onSaved={() => { setEditSlot(null); load(); }}
        />
      )}

      {editRangePeriod && (
        <EditPeriodRangeModal
          config={config}
          period={editRangePeriod}
          onClose={() => setEditRangePeriod(null)}
          onSaved={() => { setEditRangePeriod(null); load(); }}
        />
      )}

      {duplicateSourcePeriod && (
        <DuplicatePeriodModal
          config={config}
          sourcePeriod={duplicateSourcePeriod}
          periods={periods}
          onClose={() => setDuplicateSourcePeriod(null)}
          onSaved={() => { setDuplicateSourcePeriod(null); load(); }}
        />
      )}

      {/* Settings modal (role management + start date) */}
      {showSettings && (
        <EditRotationModal
          config={config}
          numPeriods={numPeriods}
          guardNames={guardNames}
          guards={guards}
          onClose={() => setShowSettings(false)}
          onSaved={() => { setShowSettings(false); load(); }}
        />
      )}

      {/* Sync result modal */}
      {syncResult && (
        <SyncModal result={syncResult} onClose={() => setSyncResult(null)} />
      )}

      {/* Add week modal */}
      {showAddWeekModal && (
        <div className="fixed inset-0 z-50 bg-black/60 flex items-end" onClick={() => setShowAddWeekModal(false)}>
          <div
            className="w-full bg-bg-card border-t border-bg-border rounded-t-2xl pb-8 slide-in
                       max-w-2xl mx-auto max-h-[85vh] flex flex-col"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between p-5 border-b border-bg-border shrink-0">
              <h2 className="font-bold text-text text-lg">הוספת תקופות חדשות</h2>
              <button onClick={() => setShowAddWeekModal(false)} className="text-text-dim hover:text-text text-xl px-2">✕</button>
            </div>

            <div className="overflow-y-auto flex-1 p-5 space-y-3">
              {addWeekPeriods.map((p, i) => (
                <div key={i} className="card space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-text-dim">תקופה {i + 1}</span>
                    {addWeekPeriods.length > 1 && (
                      <button
                        onClick={() => setAddWeekPeriods((prev) => prev.filter((_, idx) => idx !== i))}
                        className="text-danger/60 hover:text-danger text-xs"
                      >
                        הסר
                      </button>
                    )}
                  </div>
                  <div className="flex gap-2 items-center">
                    <div className="flex-1">
                      <label className="text-xs text-text-dim block mb-1">מתאריך</label>
                      <input
                        type="date"
                        value={p.start}
                        onChange={(e) => setAddWeekPeriods((prev) =>
                          prev.map((r, idx) => idx === i ? { ...r, start: e.target.value } : r)
                        )}
                        className="input text-sm w-full"
                      />
                    </div>
                    <div className="text-text-dim pt-4">—</div>
                    <div className="flex-1">
                      <label className="text-xs text-text-dim block mb-1">עד תאריך</label>
                      <input
                        type="date"
                        value={p.end}
                        onChange={(e) => setAddWeekPeriods((prev) =>
                          prev.map((r, idx) => idx === i ? { ...r, end: e.target.value } : r)
                        )}
                        className="input text-sm w-full"
                      />
                    </div>
                  </div>
                  {p.start && p.end && p.end > p.start && (
                    <div className="text-xs text-success">
                      {Math.round((new Date(p.end).getTime() - new Date(p.start).getTime()) / 86400000)} ימים
                    </div>
                  )}
                  {p.start && p.end && p.end <= p.start && (
                    <div className="text-xs text-danger">תאריך סיום חייב להיות אחרי ההתחלה</div>
                  )}
                </div>
              ))}

              <button
                onClick={() => {
                  const last = addWeekPeriods[addWeekPeriods.length - 1];
                  const base = last?.end ? new Date(last.end) : new Date();
                  const d = (n: number) => { const dt = new Date(base); dt.setDate(dt.getDate() + n); return dateInputValue(dt); };
                  setAddWeekPeriods((prev) => [...prev, { start: d(0), end: d(2) }]);
                }}
                className="w-full border border-dashed border-bg-border text-text-dim hover:text-text
                           hover:border-primary/40 text-sm py-2 rounded-xl transition-colors"
              >
                + הוסף תקופה נוספת
              </button>
            </div>

            <div className="p-5 border-t border-bg-border shrink-0">
              <button
                onClick={() => handleAddWeek(addWeekPeriods)}
                disabled={addingWeek || addWeekPeriods.some((p) => !p.start || !p.end || p.end <= p.start)}
                className="btn-primary w-full"
              >
                {addingWeek ? "מוסיף..." : `הוסף ${addWeekPeriods.length} תקופות`}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Import preview / confirm modal */}
      {importPreview && (
        <div className="fixed inset-0 z-50 bg-black/60 flex items-end" onClick={() => setImportPreview(null)}>
          <div
            className="w-full bg-bg-card border-t border-bg-border rounded-t-2xl pb-8 slide-in
                       max-w-2xl mx-auto max-h-[80vh] flex flex-col"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between p-5 border-b border-bg-border shrink-0">
              <h2 className="font-bold text-text text-lg">אישור ייבוא סבב חופשה</h2>
              <button onClick={() => setImportPreview(null)} className="text-text-dim hover:text-text text-xl px-2">✕</button>
            </div>

            <div className="overflow-y-auto flex-1 p-5 space-y-4">
              {/* Summary */}
              <div className="flex gap-3 flex-wrap">
                <div className="card flex-1 text-center">
                  <div className="text-2xl font-bold text-primary">{importPreview.matchedPeriods}</div>
                  <div className="text-xs text-text-dim mt-0.5">תקופות זוהו</div>
                </div>
                <div className="card flex-1 text-center">
                  <div className="text-2xl font-bold text-primary">{importPreview.roles.length}</div>
                  <div className="text-xs text-text-dim mt-0.5">תפקידים</div>
                </div>
                <div className="card flex-1 text-center">
                  <div className="text-2xl font-bold text-primary">
                    {importPreview.roles.reduce((sum, r) => {
                      let names = 0;
                      r.slotsMap.forEach((arr) => { names += arr.length; });
                      return sum + names;
                    }, 0)}
                  </div>
                  <div className="text-xs text-text-dim mt-0.5">שיבוצים</div>
                </div>
              </div>

              {/* Per-role preview */}
              <div className="space-y-2">
                {importPreview.roles.map((r) => {
                  const totalNames = Array.from(r.slotsMap.values()).reduce((s, a) => s + a.length, 0);
                  return (
                    <div key={r.id} className="flex items-center justify-between bg-bg-base/40 border border-bg-border rounded-xl px-3 py-2">
                      <span className="text-sm font-semibold text-text">{r.name}</span>
                      <span className="text-xs text-text-dim">
                        {totalNames} שיבוצים ב-{r.slotsMap.size} תקופות
                      </span>
                    </div>
                  );
                })}
              </div>

              {importPreview.matchedPeriods < importPreview.totalPeriods && (
                <div className="text-xs text-warning bg-warning/10 border border-warning/25 rounded-xl p-3">
                  ⚠ {importPreview.totalPeriods - importPreview.matchedPeriods} תקופות לא זוהו בקובץ — הנתונים הקיימים בתקופות אלו לא ישתנו.
                </div>
              )}

              <div className="text-xs text-text-dim bg-primary/10 border border-primary/20 rounded-xl px-3 py-2">
                הייבוא יחליף את שמות השומרים בתקופות שזוהו. פעולה זו אינה ניתנת לביטול.
              </div>
            </div>

            <div className="p-5 border-t border-bg-border shrink-0 flex gap-3">
              <button
                onClick={() => setImportPreview(null)}
                className="flex-1 btn-secondary"
              >
                ביטול
              </button>
              <button
                onClick={handleImportConfirm}
                disabled={importing}
                className="flex-1 btn-primary"
              >
                {importing ? "מייבא..." : "אישור ייבוא"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

