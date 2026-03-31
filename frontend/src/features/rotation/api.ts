import type { RotationConfig } from "./types";

const BASE = (import.meta.env.VITE_API_URL ?? "") + "/api";

export async function getRotation(): Promise<RotationConfig> {
  const r = await fetch(`${BASE}/rotation`);
  if (!r.ok) throw new Error("Failed to load rotation");
  return r.json();
}

export async function updateRotationConfig(start_date: string, period_days: number) {
  const r = await fetch(`${BASE}/rotation/config`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ start_date, period_days }),
  });
  if (!r.ok) throw new Error("Failed to update rotation config");
}

export async function clearAllRotationSlots() {
  const r = await fetch(`${BASE}/rotation/slots/all`, { method: "DELETE" });
  if (!r.ok) throw new Error("Failed to clear rotation slots");
}

export async function deleteRotationPeriod(slotNum: number) {
  const r = await fetch(`${BASE}/rotation/periods/${slotNum}`, { method: "DELETE" });
  if (!r.ok) throw new Error("Failed to delete period");
}

export async function updateRotationPeriod(slotNum: number, start_date: string, end_date: string, force = false) {
  const url = `${BASE}/rotation/periods/${slotNum}${force ? "?force=true" : ""}`;
  const r = await fetch(url, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ start_date, end_date }),
  });
  if (!r.ok) throw new Error("Failed to update period range");
}

export async function addRotationRole(name: string) {
  const r = await fetch(`${BASE}/rotation/roles`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  });
  if (!r.ok) throw new Error("Failed to add role");
}

export async function updateRotationRole(id: number, name: string) {
  const r = await fetch(`${BASE}/rotation/roles/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  });
  if (!r.ok) throw new Error("Failed to update role");
}

export async function deleteRotationRole(id: number) {
  const r = await fetch(`${BASE}/rotation/roles/${id}`, { method: "DELETE" });
  if (!r.ok) throw new Error("Failed to delete role");
}

export async function updateRotationSlots(roleId: number, slots: string[][]) {
  const r = await fetch(`${BASE}/rotation/roles/${roleId}/slots`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ slots }),
  });
  if (!r.ok) throw new Error("Failed to update groups");
}

export interface SyncResult {
  updated: { name: string; old_role: string | null; new_role: string }[];
  conflicts: { name: string; roles: string[] }[];
  unknown_in_rotation: string[];
}

export async function syncRotationGuards(): Promise<SyncResult> {
  const r = await fetch(`${BASE}/sync/rotation-guards`, { method: "POST" });
  if (!r.ok) throw new Error("Failed to sync rotation");
  return r.json();
}

export async function syncScheduleGuards(): Promise<SyncResult> {
  const r = await fetch(`${BASE}/sync/schedule-guards`, { method: "POST" });
  if (!r.ok) throw new Error("Failed to sync schedule");
  return r.json();
}

