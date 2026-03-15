import type { RotationConfig } from "./types";

const BASE = (import.meta.env.VITE_API_URL ?? "") + "/api";

export async function getRotation(): Promise<RotationConfig> {
  const r = await fetch(`${BASE}/rotation`);
  if (!r.ok) throw new Error("שגיאה בטעינת הסבב");
  return r.json();
}

export async function updateRotationConfig(start_date: string, period_days: number) {
  const r = await fetch(`${BASE}/rotation/config`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ start_date, period_days }),
  });
  if (!r.ok) throw new Error("שגיאה בעדכון הגדרות הסבב");
}

export async function addRotationRole(name: string) {
  const r = await fetch(`${BASE}/rotation/roles`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  });
  if (!r.ok) throw new Error("שגיאה בהוספת תפקיד");
}

export async function updateRotationRole(id: number, name: string) {
  const r = await fetch(`${BASE}/rotation/roles/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  });
  if (!r.ok) throw new Error("שגיאה בעדכון תפקיד");
}

export async function deleteRotationRole(id: number) {
  const r = await fetch(`${BASE}/rotation/roles/${id}`, { method: "DELETE" });
  if (!r.ok) throw new Error("שגיאה במחיקת תפקיד");
}

export async function updateRotationSlots(roleId: number, slots: string[][]) {
  const r = await fetch(`${BASE}/rotation/roles/${roleId}/slots`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ slots }),
  });
  if (!r.ok) throw new Error("שגיאה בעדכון קבוצות");
}

export interface SyncResult {
  updated: { name: string; old_role: string | null; new_role: string }[];
  conflicts: { name: string; roles: string[] }[];
  unknown_in_rotation: string[];
}

export async function syncRotationGuards(): Promise<SyncResult> {
  const r = await fetch(`${BASE}/sync/rotation-guards`, { method: "POST" });
  if (!r.ok) throw new Error("שגיאה בסנכרון");
  return r.json();
}
