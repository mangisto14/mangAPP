import type { AbsenceStatus } from "./types";

const BASE = "/api";

async function req<T>(path: string, opts?: RequestInit): Promise<T> {
  const res = await fetch(BASE + path, {
    headers: { "Content-Type": "application/json" },
    ...opts,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? `HTTP ${res.status}`);
  }
  return res.json();
}

export const getAbsences = () => req<AbsenceStatus[]>("/absences");

export const markLeave = (guard_id: number) =>
  req<{ ok: boolean }>("/absences/leave", {
    method: "POST",
    body: JSON.stringify({ guard_id }),
  });

export const markReturn = (guard_id: number) =>
  req<{ ok: boolean }>("/absences/return", {
    method: "POST",
    body: JSON.stringify({ guard_id }),
  });

export const resetAbsence = (guard_id: number) =>
  req<{ ok: boolean }>("/absences/reset", {
    method: "POST",
    body: JSON.stringify({ guard_id }),
  });
