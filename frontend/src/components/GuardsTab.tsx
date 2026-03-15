import { useEffect, useState } from "react";
import { Trash2, Save, AlertTriangle, UserPlus, ChevronDown } from "lucide-react";
import { getGuards, addGuards, updateGuard, deleteGuard } from "../api";
import type { Guard } from "../types";

interface EditState {
  name: string;
  phone: string;
  role: string;
}

export default function GuardsTab() {
  const [guards, setGuards] = useState<Guard[]>([]);
  const [loading, setLoading] = useState(true);
  const [addInput, setAddInput] = useState("");
  const [edits, setEdits] = useState<Record<number, EditState>>({});
  const [expanded, setExpanded] = useState<number | null>(null);
  const [toast, setToast] = useState("");

  const load = async () => {
    setLoading(true);
    try {
      const g = await getGuards();
      setGuards(g);
      const e: Record<number, EditState> = {};
      g.forEach((guard) => {
        e[guard.id] = {
          name: guard.name,
          phone: guard.phone ?? "",
          role: guard.role ?? "",
        };
      });
      setEdits(e);
    } catch (err) {
      showToast(`שגיאה: ${(err as Error).message}`);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

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
    } catch (err) {
      showToast(`שגיאה: ${(err as Error).message}`);
    }
  };

  const handleUpdate = async (id: number) => {
    const e = edits[id];
    if (!e?.name.trim()) return;
    try {
      await updateGuard(id, e.name.trim(), e.phone || null, e.role || null);
      showToast(`💾 ${e.name} עודכן`);
      load();
    } catch (err) {
      showToast(`שגיאה: ${(err as Error).message}`);
    }
  };

  const handleDelete = async (guard: Guard) => {
    if (!confirm(`למחוק את ${guard.name}?`)) return;
    await deleteGuard(guard.id);
    load();
  };

  const setField = (id: number, field: keyof EditState, value: string) =>
    setEdits((prev) => ({ ...prev, [id]: { ...prev[id], [field]: value } }));

  const overloaded = guards.filter((g) => g.overloaded);

  return (
    <div className="fade-in space-y-4">
      {toast && (
        <div className="fixed top-20 right-4 left-4 max-w-sm mx-auto z-50">
          <div className="card border-primary/40 bg-primary/10 text-text text-sm text-center font-medium slide-in">
            {toast}
          </div>
        </div>
      )}

      {overloaded.length > 0 && (
        <div className="card border-warning/40 bg-warning/5 slide-in">
          <div className="flex items-start gap-2">
            <AlertTriangle size={18} className="text-warning flex-shrink-0 mt-0.5" />
            <div>
              <p className="font-bold text-warning mb-1">⚠️ אנשים עם עומס יתר</p>
              <div className="flex flex-wrap gap-2">
                {overloaded.map((g) => (
                  <span key={g.id} className="overload-badge">
                    {g.name} · {g.future} עתידיות
                  </span>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Add */}
      <div className="card space-y-3">
        <h2 className="font-bold text-text flex items-center gap-2">
          <UserPlus size={16} className="text-primary-light" />
          הוספת אנשים
        </h2>
        <div className="flex gap-2">
          <input
            value={addInput}
            onChange={(e) => setAddInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleAdd()}
            placeholder="ישראל ישראלי, משה כהן, ..."
            className="input flex-1"
          />
          <button onClick={handleAdd} className="btn-primary px-5">הוסף</button>
        </div>
        <p className="text-xs text-text-dim">ניתן להוסיף מספר אנשים, מופרדים בפסיק</p>
      </div>

      {/* List */}
      <div className="card space-y-2">
        <div className="flex items-center justify-between mb-1">
          <h2 className="font-bold text-text">רשימת אנשים</h2>
          <div className="flex items-center gap-2">
            {guards.length > 0 && (
              <button
                className="text-xs text-text-dim hover:text-primary px-2 py-1 rounded-lg hover:bg-primary/10 transition-colors"
                onClick={() => {
                  const csv = guards.map((g) => g.name).join(", ");
                  navigator.clipboard.writeText(csv).then(() => showToast("📋 הועתק ללוח"));
                }}
                title="ייצא רשימה"
              >
                📋 ייצא
              </button>
            )}
            <span className="text-xs text-text-dim bg-bg-base px-2 py-1 rounded-full">
              {guards.length} אנשים
            </span>
          </div>
        </div>

        {loading && <div className="text-center text-text-dim py-6">טוען...</div>}
        {!loading && guards.length === 0 && (
          <div className="text-center text-text-dim py-6">אין אנשים – הוסף למעלה</div>
        )}

        <div className="space-y-2 max-h-[500px] overflow-y-auto">
          {guards.map((g) => {
            const e = edits[g.id];
            const isOpen = expanded === g.id;
            return (
              <div
                key={g.id}
                className={`rounded-xl border transition-all
                  ${g.overloaded ? "border-warning/30 bg-warning/5" : "border-bg-border bg-bg-base"}`}
              >
                {/* Main row */}
                <div className="flex items-center gap-2 p-2.5">
                  <input
                    value={e?.name ?? g.name}
                    onChange={(ev) => setField(g.id, "name", ev.target.value)}
                    onKeyDown={(ev) => ev.key === "Enter" && handleUpdate(g.id)}
                    className="input flex-1 text-sm py-1.5 h-8"
                  />
                  <div className="flex gap-1 shrink-0">
                    <span className="pill-past">✅ {g.past}</span>
                    <span className="pill-future">🕐 {g.future}</span>
                  </div>
                  <button
                    onClick={() => setExpanded(isOpen ? null : g.id)}
                    className="p-1.5 text-text-dim hover:text-text rounded-lg hover:bg-bg-border transition-colors"
                    title="פרטים נוספים"
                  >
                    <ChevronDown size={14} className={`transition-transform ${isOpen ? "rotate-180" : ""}`} />
                  </button>
                  <button
                    onClick={() => handleUpdate(g.id)}
                    className="p-1.5 text-text-dim hover:text-success rounded-lg hover:bg-success/10 transition-colors"
                  >
                    <Save size={15} />
                  </button>
                  <button
                    onClick={() => handleDelete(g)}
                    className="p-1.5 text-text-dim hover:text-danger rounded-lg hover:bg-danger/10 transition-colors"
                  >
                    <Trash2 size={15} />
                  </button>
                </div>

                {/* Expanded: phone + role */}
                {isOpen && (
                  <div className="px-3 pb-3 space-y-2 border-t border-bg-border pt-2 slide-in">
                    <div className="flex gap-2">
                      <div className="flex-1">
                        <label className="text-xs text-text-dim block mb-1">טלפון</label>
                        <input
                          value={e?.phone ?? ""}
                          onChange={(ev) => setField(g.id, "phone", ev.target.value)}
                          placeholder="050-0000000"
                          className="input text-sm py-1.5"
                          type="tel"
                        />
                      </div>
                      <div className="flex-1">
                        <label className="text-xs text-text-dim block mb-1">תפקיד</label>
                        <input
                          value={e?.role ?? ""}
                          onChange={(ev) => setField(g.id, "role", ev.target.value)}
                          placeholder="פקח / מפקד / נהג..."
                          className="input text-sm py-1.5"
                        />
                      </div>
                    </div>
                    {e?.phone && (
                      <a
                        href={`tel:${e.phone}`}
                        className="btn-ghost text-xs px-3 py-1.5 inline-flex items-center gap-1"
                      >
                        📞 חייג
                      </a>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
