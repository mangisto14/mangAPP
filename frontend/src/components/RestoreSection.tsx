import { useRef, useState } from "react";
import {
  restorePreview,
  restoreBackup,
  type RestoreTablePreview,
  type RestoreTableConfig,
} from "../api";

type Step = "idle" | "preview" | "pin" | "done";

export default function RestoreSection() {
  const fileRef = useRef<HTMLInputElement>(null);
  const [step, setStep] = useState<Step>("idle");
  const [file, setFile] = useState<File | null>(null);
  const [tables, setTables] = useState<RestoreTablePreview[]>([]);
  const [selected, setSelected] = useState<Record<string, boolean>>({});
  const [modes, setModes] = useState<Record<string, "replace" | "merge">>({});
  const [pin, setPin] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [results, setResults] = useState<Record<string, { ok: boolean; inserted?: number; error?: string }>>({});

  const TABLE_LABELS: Record<string, string> = {
    guards: "שומרים",
    shifts: "משמרות",
    absences: "יציאות",
    rotation_config: "הגדרות סבב",
    rotation_roles: "תפקידי סבב",
    rotation_slots: "משבצות סבב",
    rotation_periods: "תקופות סבב",
    settings: "הגדרות מערכת",
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (!f) return;
    setFile(f);
    setError("");
    setLoading(true);
    try {
      const data = await restorePreview(f);
      setTables(data.tables);
      const initSelected: Record<string, boolean> = {};
      const initModes: Record<string, "replace" | "merge"> = {};
      data.tables.forEach((t) => {
        initSelected[t.name] = true;
        initModes[t.name] = "replace";
      });
      setSelected(initSelected);
      setModes(initModes);
      setStep("preview");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "שגיאה בקריאת הגיבוי");
    } finally {
      setLoading(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  };

  const handleRestore = async () => {
    const selectedTables: RestoreTableConfig[] = tables
      .filter((t) => selected[t.name])
      .map((t) => ({ name: t.name, mode: modes[t.name] ?? "replace" }));

    if (!selectedTables.length) {
      setError("יש לבחור לפחות טבלה אחת");
      return;
    }
    setStep("pin");
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
    setStep("idle");
    setFile(null);
    setTables([]);
    setSelected({});
    setModes({});
    setPin("");
    setError("");
    setResults({});
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-semibold text-text">שחזור מגיבוי</p>
          <p className="text-xs text-text-dim mt-0.5">העלה קובץ ZIP מגיבוי קודם</p>
        </div>
        {step !== "idle" && (
          <button onClick={reset} className="btn-ghost text-xs px-3 py-1.5">ביטול</button>
        )}
      </div>

      {/* Step: idle */}
      {step === "idle" && (
        <>
          <input
            ref={fileRef}
            type="file"
            accept=".zip"
            className="hidden"
            onChange={handleFileChange}
          />
          <button
            onClick={() => fileRef.current?.click()}
            disabled={loading}
            className="btn-ghost w-full text-sm disabled:opacity-50"
          >
            {loading ? "טוען..." : "📂 בחר קובץ ZIP"}
          </button>
        </>
      )}

      {/* Step: preview */}
      {step === "preview" && (
        <div className="space-y-2">
          <p className="text-xs text-text-dim">בחר טבלאות ומצב שחזור:</p>
          {tables.map((t) => (
            <div key={t.name} className="bg-bg-base rounded-xl px-3 py-2 flex items-center gap-2">
              <input
                type="checkbox"
                id={`tbl-${t.name}`}
                checked={!!selected[t.name]}
                onChange={(e) => setSelected((p) => ({ ...p, [t.name]: e.target.checked }))}
                className="w-4 h-4 accent-primary shrink-0"
              />
              <label htmlFor={`tbl-${t.name}`} className="flex-1 min-w-0">
                <span className="text-sm font-medium text-text">
                  {TABLE_LABELS[t.name] ?? t.name}
                </span>
                <span className="text-xs text-text-dim mr-1">({t.rows} שורות)</span>
              </label>
              <select
                value={modes[t.name] ?? "replace"}
                onChange={(e) => setModes((p) => ({ ...p, [t.name]: e.target.value as "replace" | "merge" }))}
                disabled={!selected[t.name]}
                className="input text-xs py-1 w-24 shrink-0 disabled:opacity-40"
              >
                <option value="replace">החלף</option>
                <option value="merge">מיזוג</option>
              </select>
            </div>
          ))}
          <button
            onClick={handleRestore}
            className="btn-primary w-full mt-1"
          >
            שחזר נבחרות
          </button>
        </div>
      )}

      {/* Step: PIN */}
      {step === "pin" && (
        <div className="space-y-3">
          <p className="text-sm text-text text-center">הזן קוד PIN לאישור שחזור</p>
          <input
            type="password"
            inputMode="numeric"
            maxLength={6}
            value={pin}
            autoFocus
            onChange={(e) => setPin(e.target.value.replace(/\D/g, ""))}
            placeholder="• • • •"
            className="input w-full text-center text-lg tracking-widest"
          />
          <button
            onClick={handlePinConfirm}
            disabled={loading || !pin}
            className="btn-primary w-full disabled:opacity-50"
          >
            {loading ? "מבצע שחזור..." : "אשר שחזור"}
          </button>
        </div>
      )}

      {/* Step: done */}
      {step === "done" && (
        <div className="space-y-2">
          {Object.entries(results).map(([name, r]) => (
            <div
              key={name}
              className={`rounded-xl px-3 py-2 text-sm flex items-center gap-2 ${
                r.ok ? "bg-success/10 text-success" : "bg-danger/10 text-danger"
              }`}
            >
              <span>{r.ok ? "✅" : "❌"}</span>
              <span className="font-medium">{TABLE_LABELS[name] ?? name}</span>
              {r.ok && r.inserted !== undefined && (
                <span className="text-xs opacity-70 mr-auto">{r.inserted} שורות</span>
              )}
              {!r.ok && r.error && (
                <span className="text-xs opacity-70 mr-auto">{r.error}</span>
              )}
            </div>
          ))}
          <button onClick={reset} className="btn-ghost w-full text-sm mt-1">סגור</button>
        </div>
      )}

      {error && (
        <p className="text-xs text-danger bg-danger/10 rounded-xl px-3 py-2">{error}</p>
      )}
    </div>
  );
}
