import type { Guard, Shift, Stats, Suggestion, StagedShift } from "./types";

const BASE = "/api";

async function req<T>(
  path: string,
  opts?: RequestInit
): Promise<T> {
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

// Guards
export const getGuards = () => req<Guard[]>("/guards");
export const addGuards = (names: string[]) =>
  req<{ added: string[]; skipped: string[] }>("/guards", {
    method: "POST",
    body: JSON.stringify({ names }),
  });
export const updateGuard = (id: number, name: string) =>
  req<{ ok: boolean }>(`/guards/${id}`, {
    method: "PUT",
    body: JSON.stringify({ name }),
  });
export const deleteGuard = (id: number) =>
  req<{ ok: boolean }>(`/guards/${id}`, { method: "DELETE" });

// Shifts
export const getShifts = (filter: "all" | "future" | "past" = "all") =>
  req<Shift[]>(`/shifts?filter=${filter}`);
export const addShifts = (shifts: StagedShift[]) =>
  req<{ ok: boolean; count: number }>("/shifts", {
    method: "POST",
    body: JSON.stringify({ shifts }),
  });
export const deleteShift = (id: number) =>
  req<{ ok: boolean }>(`/shifts/${id}`, { method: "DELETE" });

// Stats & Suggest
export const getStats = () => req<Stats>("/stats");
export const getSuggest = (limit = 3) =>
  req<Suggestion[]>(`/suggest?limit=${limit}`);

// WhatsApp
export const getWhatsapp = () =>
  req<{ url: string; text: string }>("/whatsapp");

