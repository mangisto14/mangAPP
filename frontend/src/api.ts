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

// Backup & Restore
export type RestoreTablePreview = { name: string; rows: number };
export type RestoreTableConfig = { name: string; mode: "replace" | "merge" };
export type RestoreResult = { ok: boolean; results: Record<string, { ok: boolean; inserted?: number; error?: string }> };

export async function restorePreview(file: File): Promise<{ tables: RestoreTablePreview[] }> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${BASE}/admin/restore/preview`, { method: "POST", body: form });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? `HTTP ${res.status}`);
  }
  return res.json();
}

// Reminders
export type Reminder = {
  id: number;
  task_name: string;
  start_date: string;
  interval_days: number;
  send_time: string;
  message_text: string;
  last_sent_date: string | null;
  is_active: number;
};
export type ReminderCreate = Omit<Reminder, "id" | "last_sent_date" | "is_active">;

export const getReminders = () => req<Reminder[]>("/reminders");
export const createReminder = (body: ReminderCreate) =>
  req<{ ok: boolean; id: number }>("/reminders", { method: "POST", body: JSON.stringify(body) });
export const toggleReminder = (id: number) =>
  req<{ ok: boolean; is_active: number }>(`/reminders/${id}/toggle`, { method: "PUT" });
export const updateReminder = (id: number, body: ReminderCreate) =>
  req<{ ok: boolean }>(`/reminders/${id}`, { method: "PUT", body: JSON.stringify(body) });
export const deleteReminder = (id: number) =>
  req<{ ok: boolean }>(`/reminders/${id}`, { method: "DELETE" });

export async function restoreBackup(file: File, tables: RestoreTableConfig[], pin: string): Promise<RestoreResult> {
  const form = new FormData();
  form.append("file", file);
  form.append("config", JSON.stringify({ pin, tables }));
  const res = await fetch(`${BASE}/admin/restore`, { method: "POST", body: form });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? `HTTP ${res.status}`);
  }
  return res.json();
}

