import { useEffect, useState } from "react";
import { Trash2, Save, AlertTriangle, UserPlus } from "lucide-react";
import { getGuards, addGuards, updateGuard, deleteGuard } from "../api";
import type { Guard } from "../types";

export default function GuardsTab() {
  const [guards, setGuards] = useState<Guard[]>([]);
  const [loading, setLoading] = useState(true);
  const [addInput, setAddInput] = useState("");
  const [editNames, setEditNames] = useState<Record<number, string>>({});
  const [toast, setToast] = useState("");

  const load = async () => {
    setLoading(true);
    try {
      const g = await getGuards();
      setGuards(g);
      const names: Record<number, string> = {};
      g.forEach((guard) => (names[guard.id] = guard.name));
      setEditNames(names);
    } catch (e) {
      showToast(`שגיאה: ${(e as Error).message}`);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const showToast = (msg: string) => {
    setToast(msg);
    setTimeout(() => setToast(""), 3000);
  };

  const handleAdd = async () => {
    const names = addInput.split(",").map((n) => n.trim()).filter(Boolean);
    if (names.length === 0) return;
    try {
      const { added, skipped } = await addGuards(names);
      let msg = "";
      if (added.length) msg += `✅ נוסף: ${added.join(", ")}`;
      if (skipped.length) msg += ` · קיים: ${skipped.join(", ")}`;
      showToast(msg || "הושלם");
      setAddInput("");
      load();
    } catch (e) {
      showToast(`שגיאה: ${(e as Error).message}`);
    }
  };

  const handleUpdate = async (id: number) => {
    const name = editNames[id]?.trim();
    if (!name) return;
    try {
      await updateGuard(id, name);
      showToast(`💾 ${name} עודכן`);
      load();
    } catch (e) {
      showToast(`שגיאה: ${(e as Error).message}`);
    }
  };

  const handleDelete = async (guard: Guard) => {
    if (!confirm(`למחוק את ${guard.name}?`)) return;
    await deleteGuard(guard.id);
    load();
  };

  const overloaded = guards.filter((g) => g.overloaded);

  return (
    <div className="fade-in space-y-4">
      {/* Toast */}
      {toast && (
        <div className="fixed top-20 right-4 left-4 max-w-sm mx-auto z-50">
          <div className="card border-primary/40 bg-primary/10 text-text text-sm text-center font-medium slide-in">
            {toast}
          </div>
        </div>
      )}

      {/* ── Overload Alert ─────────────────────────────────────── */}
      {overloaded.length > 0 && (
        <div className="card border-warning/40 bg-warning/5 slide-in">
          <div className="flex items-start gap-2">
            <AlertTriangle size={18} className="text-warning flex-shrink-0 mt-0.5" />
            <div>
              <p className="font-bold text-warning mb-1">⚠️ שומרים עם עומס יתר</p>
              <div className="flex flex-wrap gap-2">
                {overloaded.map((g) => (
                  <span key={g.id} className="overload-badge">
                    {g.name} · {g.future} עתידיות
                  </span>
                ))}
              </div>
              <p className="text-xs text-text-dim mt-2">
                שומרים אלה משובץ ב-{overloaded[0]?.future}+ משמרות עתידיות.
                מומלץ לשבץ שומרים אחרים.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* ── Add Guards ─────────────────────────────────────────── */}
      <div className="card space-y-3">
        <h2 className="font-bold text-text flex items-center gap-2">
          <UserPlus size={16} className="text-primary-light" />
          הוספת שומרים
        </h2>
        <div className="flex gap-2">
          <input
            value={addInput}
            onChange={(e) => setAddInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleAdd()}
            placeholder="ישראל ישראלי, משה כהן, ..."
            className="input flex-1"
          />
          <button onClick={handleAdd} className="btn-primary px-5">
            הוסף
          </button>
        </div>
        <p className="text-xs text-text-dim">ניתן להוסיף מספר שומרים, מופרדים בפסיק</p>
      </div>

      {/* ── Guards List ────────────────────────────────────────── */}
      <div className="card space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="font-bold text-text">רשימת שומרים</h2>
          <span className="text-xs text-text-dim bg-bg-base px-2 py-1 rounded-full">
            {guards.length} שומרים
          </span>
        </div>

        {loading && (
          <div className="text-center text-text-dim py-6">טוען...</div>
        )}

        {!loading && guards.length === 0 && (
          <div className="text-center text-text-dim py-6">
            אין שומרים – הוסף למעלה
          </div>
        )}

        <div className="space-y-2 max-h-[420px] overflow-y-auto">
          {guards.map((g) => (
            <div
              key={g.id}
              className={`flex items-center gap-2 p-3 rounded-xl border transition-all
                ${g.overloaded ? "border-warning/30 bg-warning/5" : "border-bg-border bg-bg-base"}`}
            >
              {/* Name input */}
              <input
                value={editNames[g.id] ?? g.name}
                onChange={(e) =>
                  setEditNames((prev) => ({ ...prev, [g.id]: e.target.value }))
                }
                onKeyDown={(e) => e.key === "Enter" && handleUpdate(g.id)}
                className="input flex-1 text-sm py-1.5 h-8"
              />

              {/* Stats */}
              <div className="flex gap-1 flex-shrink-0">
                <span className="pill-past">✅ {g.past}</span>
                <span className="pill-future">🕐 {g.future}</span>
                {g.overloaded && (
                  <span className="overload-badge">
                    <AlertTriangle size={10} />
                    עמוס
                  </span>
                )}
              </div>

              {/* Save */}
              <button
                onClick={() => handleUpdate(g.id)}
                title="שמור שם"
                className="flex-shrink-0 text-text-dim hover:text-success transition-colors p-1.5
                           rounded-lg hover:bg-success/10"
              >
                <Save size={15} />
              </button>

              {/* Delete */}
              <button
                onClick={() => handleDelete(g)}
                title="מחק"
                className="flex-shrink-0 text-text-dim hover:text-danger transition-colors p-1.5
                           rounded-lg hover:bg-danger/10"
              >
                <Trash2 size={15} />
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
