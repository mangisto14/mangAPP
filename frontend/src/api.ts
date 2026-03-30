import type { Guard, Shift, Stats, Suggestion, StagedShift } from "./types";

const BASE = (import.meta.env.VITE_API_URL ?? "") + "/api";

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
export const getGuards = (includeInactive = false) => {
  const params = new URLSearchParams();
  if (includeInactive) params.set("include_inactive", "true");
  const query = params.toString();
  return req<Guard[]>(query ? `/guards?${query}` : "/guards");
};
export const addGuards = (names: string[]) =>
  req<{ added: string[]; skipped: string[] }>("/guards", {
    method: "POST",
    body: JSON.stringify({ names }),
  });
export const updateGuard = (
  id: number,
  name: string,
  phone?: string | null,
  role?: string | null,
  isActive?: boolean,
) =>
  req<{ ok: boolean }>(`/guards/${id}`, {
    method: "PUT",
    body: JSON.stringify({
      name,
      phone: phone ?? null,
      role: role ?? null,
      ...(typeof isActive === "boolean" ? { is_active: isActive } : {}),
    }),
  });
export const deleteGuard = (id: number) =>
  req<{ ok: boolean }>(`/guards/${id}`, { method: "DELETE" });

// Shifts
export const getShifts = (
  filter: "all" | "future" | "past" = "all",
  dateFrom?: string,
  dateTo?: string,
) => {
  const params = new URLSearchParams({ filter });
  if (dateFrom) params.set("date_from", dateFrom);
  if (dateTo) params.set("date_to", dateTo);
  return req<Shift[]>(`/shifts?${params}`);
};
export const addShifts = (shifts: StagedShift[]) =>
  req<{ ok: boolean; count: number }>("/shifts", {
    method: "POST",
    body: JSON.stringify({ shifts }),
  });
export const deleteShift = (id: number) =>
  req<{ ok: boolean }>(`/shifts/${id}`, { method: "DELETE" });
export const updateShift = (id: number, start_time: string, end_time: string, names: string[]) =>
  req<{ ok: boolean }>(`/shifts/${id}`, {
    method: "PUT",
    body: JSON.stringify({ start_time, end_time, names }),
  });

// Stats & Suggest
export const getStats = () => req<Stats>("/stats");
export const getSuggest = (limit = 3) =>
  req<Suggestion[]>(`/suggest?limit=${limit}`);

// WhatsApp
export const getWhatsapp = () =>
  req<{ url: string; text: string }>("/whatsapp");

