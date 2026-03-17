import type { AbsenceStatus, AbsenceHistory, Settings } from "./types";

const BASE = (import.meta.env.VITE_API_URL ?? "") + "/api";

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

export const getAbsencesActiveOn = (date: string) =>
  req<{ name: string; reason: string | null }[]>(`/absences/active-on?date=${date}`);

export const markLeave = (guard_id: number, reason?: string) =>
  req<{ ok: boolean }>("/absences/leave", {
    method: "POST",
    body: JSON.stringify({ guard_id, reason: reason ?? null }),
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

export const getHistory = (params?: {
  guard_id?: number;
  date_from?: string;
  date_to?: string;
}) => {
  const qs = new URLSearchParams();
  if (params?.guard_id) qs.set("guard_id", String(params.guard_id));
  if (params?.date_from) qs.set("date_from", params.date_from);
  if (params?.date_to) qs.set("date_to", params.date_to);
  const q = qs.toString();
  return req<AbsenceHistory[]>(`/absences/history${q ? "?" + q : ""}`);
};

export const getSettings = () => req<Settings>("/settings");

export const updateSettings = (settings: Partial<Settings>) =>
  req<{ ok: boolean }>("/settings", {
    method: "POST",
    body: JSON.stringify(settings),
  });

export function historyCSVUrl(params?: {
  guard_id?: number;
  date_from?: string;
  date_to?: string;
}) {
  const qs = new URLSearchParams();
  if (params?.guard_id) qs.set("guard_id", String(params.guard_id));
  if (params?.date_from) qs.set("date_from", params.date_from);
  if (params?.date_to) qs.set("date_to", params.date_to);
  const q = qs.toString();
  return `/api/absences/history.csv${q ? "?" + q : ""}`;
}
