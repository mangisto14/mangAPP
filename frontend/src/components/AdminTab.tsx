import { useEffect, useRef, useState } from "react";
import {
  getReminders, createReminder, updateReminder, toggleReminder, deleteReminder,
  restorePreview, restoreBackup,
  type Reminder, type ReminderCreate,
  type RestoreTablePreview, type RestoreTableConfig,
} from "../api";

const BASE = (import.meta.env.VITE_API_URL ?? "") + "/api";

// ── Backup Section ────────────────────────────────────────────────────────────
function BackupSection() {
  const [status, setStatus] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const triggerBackup = async () => {
    setLoading(true);
    setStatus(null);
    try {
      const res = await fetch(`${BASE}/admin/test-backup`, { method: "POST" });
      const data = await res.json();
      setStatus(data.ok ? `✅ גיבוי תוזמן ל-${data.scheduled_at}` : `❌ ${data.error}`);
    } catch {
      setStatus("❌ שגיאת חיבור");
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="card space-y-3">
      <h3 className="font-bold text-text">📦 גיבוי</h3>
      <p className="text-xs text-text-dim">גיבוי יומי אוטומטי נשלח ל-Telegram בכל יום 03:00 (Asia/Jerusalem).</p>
      <button onClick={triggerBackup} disabled={loading} className="btn-primary w-full disabled:opacity-50">
        {loading ? "מתזמן..." : "שלח גיבוי עכשיו (בעוד 2 דקות)"}
      </button>
      {status && <p className="text-xs text-center text-text-dim">{status}</p>}
    </section>
  );
}

// ── Restore Section ───────────────────────────────────────────────────────────
const TABLE_LABELS: Record<string, string> = {
  guards: "שומרים", shifts: "משמרות", absences: "יציאות",
  rotation_config: "הגדרות סבב", rotation_roles: "תפקידי סבב",
  rotation_slots: "משבצות סבב", rotation_period_ranges: "תקופות סבב",
  settings: "הגדרות מערכת", recurring_reminders: "תזכורות",
};

type RestoreStep = "idle" | "preview" | "pin" | "done";

function RestoreSection() {
  const fileRef = useRef<HTMLInputElement>(null);
  const [step, setStep] = useState<RestoreStep>("idle");
  const [file, setFile] = useState<File | null>(null);
  const [tables, setTables] = useState<RestoreTablePreview[]>([]);
  const [selected, setSelected] = useState<Record<string, boolean>>({});
  const [modes, setModes] = useState<Record<string, "replace" | "merge">>({});
  const [pin, setPin] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [results, setResults] = useState<Record<string, { ok: boolean; inserted?: number; error?: string }>>({});

  const handleFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (!f) return;
    setFile(f);
    setError("");
    setLoading(true);
    try {
      const data = await restorePreview(f);
      setTables(data.tables);
      const sel: Record<string, boolean> = {};
      const mds: Record<string, "replace" | "merge"> = {};
      data.tables.forEach((t) => { sel[t.name] = true; mds[t.name] = "replace"; });
      setSelected(sel);
      setModes(mds);
      setStep("preview");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "שגיאה בקריאת הגיבוי");
    } finally {
      setLoading(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  };

  const handlePinConfirm = async () => {
    if (!file) return;
    setLoading(true);
    setError("");
    try {
      const selectedTables: RestoreTableConfig[] = tables
        .filter((t) => selected[t.name])
        .map((t) => ({ name: t.name, mode: modes[t.name] ?? "replace" }));
      const res = await restoreBackup(file, selectedTables, pin);
      setResults(res.results);
      setStep("done");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "שגיאת שחזור");
      setStep("preview");
    } finally {
      setLoading(false);
      setPin("");
    }
  };

  const reset = () => {
    setStep("idle"); setFile(null); setTables([]); setSelected({});
    setModes({}); setPin(""); setError(""); setResults({});
  };

  return (
    <section className="card space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="font-bold text-text">🔄 שחזור מגיבוי</h3>
        {step !== "idle" && <button onClick={reset} className="btn-ghost text-xs px-3 py-1">ביטול</button>}
      </div>

      {step === "idle" && (
        <>
          <input ref={fileRef} type="file" accept=".zip" className="hidden" onChange={handleFile} />
          <button onClick={() => fileRef.current?.click()} disabled={loading} className="btn-ghost w-full text-sm disabled:opacity-50">
            {loading ? "טוען..." : "📂 בחר קובץ ZIP"}
          </button>
        </>
      )}

      {step === "preview" && (
        <div className="space-y-2">
          <p className="text-xs text-text-dim">בחר טבלאות ומצב שחזור:</p>
          {tables.map((t) => (
            <div key={t.name} className="bg-bg-base rounded-xl px-3 py-2 flex items-center gap-2">
              <input type="checkbox" id={`r-${t.name}`} checked={!!selected[t.name]}
                onChange={(e) => setSelected((p) => ({ ...p, [t.name]: e.target.checked }))}
                className="w-4 h-4 accent-primary shrink-0" />
              <label htmlFor={`r-${t.name}`} className="flex-1 min-w-0 text-sm font-medium text-text">
                {TABLE_LABELS[t.name] ?? t.name}
                <span className="text-xs text-text-dim mr-1">({t.rows} שורות)</span>
              </label>
              <select value={modes[t.name] ?? "replace"}
                onChange={(e) => setModes((p) => ({ ...p, [t.name]: e.target.value as "replace" | "merge" }))}
                disabled={!selected[t.name]}
                className="input text-xs py-1 w-24 shrink-0 disabled:opacity-40">
                <option value="replace">החלף</option>
                <option value="merge">מיזוג</option>
              </select>
            </div>
          ))}
          <button onClick={() => setStep("pin")} className="btn-primary w-full mt-1">שחזר נבחרות</button>
        </div>
      )}

      {step === "pin" && (
        <div className="space-y-3">
          <p className="text-sm text-text text-center">הזן קוד PIN לאישור שחזור</p>
          <input type="password" inputMode="numeric" maxLength={6} value={pin} autoFocus
            onChange={(e) => setPin(e.target.value.replace(/\D/g, ""))}
            placeholder="• • • •" className="input w-full text-center text-lg tracking-widest" />
          <button onClick={handlePinConfirm} disabled={loading || !pin} className="btn-primary w-full disabled:opacity-50">
            {loading ? "מבצע שחזור..." : "אשר שחזור"}
          </button>
        </div>
      )}

      {step === "done" && (
        <div className="space-y-2">
          {Object.entries(results).map(([name, r]) => (
            <div key={name} className={`rounded-xl px-3 py-2 text-sm flex items-center gap-2 ${r.ok ? "bg-success/10 text-success" : "bg-danger/10 text-danger"}`}>
              <span>{r.ok ? "✅" : "❌"}</span>
              <span className="font-medium">{TABLE_LABELS[name] ?? name}</span>
              {r.ok && <span className="text-xs opacity-70 mr-auto">{r.inserted} שורות</span>}
              {!r.ok && <span className="text-xs opacity-70 mr-auto">{r.error}</span>}
            </div>
          ))}
          <button onClick={reset} className="btn-ghost w-full text-sm mt-1">סגור</button>
        </div>
      )}

      {error && <p className="text-xs text-danger bg-danger/10 rounded-xl px-3 py-2">{error}</p>}
    </section>
  );
}

const EMPTY_FORM: ReminderCreate = { task_name: "", start_date: "", interval_days: 1, send_time: "08:00", message_text: "" };

// ── Reminders Section ─────────────────────────────────────────────────────────
function RemindersSection() {
  const [reminders, setReminders] = useState<Reminder[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [form, setForm] = useState<ReminderCreate>(EMPTY_FORM);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const load = () => getReminders().then(setReminders).catch(() => {});
  useEffect(() => { load(); }, []);

  const openAdd = () => { setEditingId(null); setForm(EMPTY_FORM); setError(""); setShowForm(true); };
  const openEdit = (r: Reminder) => {
    setEditingId(r.id);
    setForm({ task_name: r.task_name, start_date: r.start_date, interval_days: r.interval_days, send_time: r.send_time, message_text: r.message_text });
    setError("");
    setShowForm(true);
  };
  const closeForm = () => { setShowForm(false); setEditingId(null); setForm(EMPTY_FORM); setError(""); };

  const save = async () => {
    if (!form.task_name || !form.start_date || !form.message_text) {
      setError("יש למלא את כל השדות"); return;
    }
    setSaving(true);
    try {
      if (editingId !== null) {
        await updateReminder(editingId, form);
      } else {
        await createReminder(form);
      }
      closeForm();
      load();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "שגיאה");
    } finally {
      setSaving(false);
    }
  };

  const toggle = async (id: number) => { await toggleReminder(id).catch(() => {}); load(); };
  const remove = async (id: number) => {
    if (!confirm("למחוק תזכורת זו?")) return;
    await deleteReminder(id).catch(() => {});
    load();
  };

  return (
    <section className="card space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="font-bold text-text">🔔 תזכורות מחזוריות</h3>
        <button onClick={showForm ? closeForm : openAdd} className="btn-ghost text-xs px-3 py-1">
          {showForm ? "ביטול" : "+ הוסף"}
        </button>
      </div>

      {showForm && (
        <div className="bg-bg-base rounded-xl p-3 space-y-2">
          <input placeholder="שם משימה" value={form.task_name}
            onChange={(e) => setForm((p) => ({ ...p, task_name: e.target.value }))}
            className="input w-full text-sm" />
          <div className="flex gap-2">
            <div className="flex-1">
              <label className="text-xs text-text-dim block mb-1">תאריך התחלה</label>
              <input type="date" value={form.start_date}
                onChange={(e) => setForm((p) => ({ ...p, start_date: e.target.value }))}
                className="input w-full text-sm" />
            </div>
            <div className="w-24">
              <label className="text-xs text-text-dim block mb-1">שעת שליחה</label>
              <input type="time" value={form.send_time}
                onChange={(e) => setForm((p) => ({ ...p, send_time: e.target.value }))}
                className="input w-full text-sm" />
            </div>
          </div>
          <div>
            <label className="text-xs text-text-dim block mb-1">תדירות (כל כמה ימים)</label>
            <input type="number" min={1} value={form.interval_days}
              onChange={(e) => setForm((p) => ({ ...p, interval_days: Number(e.target.value) }))}
              className="input w-full text-sm" />
          </div>
          <div>
            <label className="text-xs text-text-dim block mb-1">תוכן ההודעה</label>
            <textarea rows={3} value={form.message_text}
              onChange={(e) => setForm((p) => ({ ...p, message_text: e.target.value }))}
              placeholder="טקסט שיישלח לטלגרם..."
              className="input w-full text-sm resize-none" />
          </div>
          {error && <p className="text-xs text-danger">{error}</p>}
          <button onClick={save} disabled={saving} className="btn-primary w-full disabled:opacity-50">
            {saving ? "שומר..." : editingId !== null ? "עדכן תזכורת" : "שמור תזכורת"}
          </button>
        </div>
      )}

      {reminders.length === 0 ? (
        <p className="text-xs text-text-dim text-center py-2">אין תזכורות — לחץ "+ הוסף"</p>
      ) : (
        <div className="space-y-2">
          {reminders.map((r) => (
            <div key={r.id} className={`rounded-xl px-3 py-2.5 flex items-start gap-2 ${r.is_active ? "bg-bg-base" : "bg-bg-base opacity-50"}`}>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-semibold text-text truncate">{r.task_name}</p>
                <p className="text-xs text-text-dim mt-0.5">
                  כל {r.interval_days} יום · {r.send_time} · מ-{r.start_date}
                </p>
                {r.last_sent_date && (
                  <p className="text-xs text-text-dim">נשלח לאחרונה: {r.last_sent_date}</p>
                )}
              </div>
              <button onClick={() => toggle(r.id)}
                className={`text-xs px-2 py-1 rounded-lg border shrink-0 ${r.is_active ? "border-success/40 text-success" : "border-bg-border text-text-dim"}`}>
                {r.is_active ? "פעיל" : "כבוי"}
              </button>
              <button onClick={() => openEdit(r)}
                className="text-text-dim hover:text-primary shrink-0 min-h-[32px] min-w-[32px] flex items-center justify-center text-sm">
                ✏️
              </button>
              <button onClick={() => remove(r.id)}
                className="text-danger hover:opacity-70 shrink-0 min-h-[32px] min-w-[32px] flex items-center justify-center">
                🗑
              </button>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

// ── Main AdminTab ─────────────────────────────────────────────────────────────
export default function AdminTab() {
  return (
    <div className="space-y-4 pb-24">
      <h2 className="text-lg font-bold text-text">🛡️ ניהול מערכת</h2>
      <BackupSection />
      <RestoreSection />
      <RemindersSection />
    </div>
  );
}
