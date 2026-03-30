import { useEffect, useRef, useState } from "react";
import { Trash2, Save, AlertTriangle, UserPlus, ChevronDown, Undo2, Search, X } from "lucide-react";
import { getGuards, addGuards, updateGuard, deleteGuard } from "../api";
import type { Guard } from "../types";
import { SkeletonGuardCards } from "./Skeleton";
import { useReadOnly } from "../hooks/useReadOnly";
import { copyText } from "../utils/clipboard";

interface EditState {
  name: string;
  phone: string;
  role: string;
  isActive: boolean;
}

export default function GuardsTab() {
  const [guards, setGuards] = useState<Guard[]>([]);
  const [loading, setLoading] = useState(true);
  const [addInput, setAddInput] = useState("");
  const [edits, setEdits] = useState<Record<number, EditState>>({});
  const [expanded, setExpanded] = useState<number | null>(null);
  const [toast, setToast] = useState("");
  const [pendingDelete, setPendingDelete] = useState<{ id: number; name: string } | null>(null);
  const deleteTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const readOnly = useReadOnly();

  const load = async () => {
    setLoading(true);
    try {
      const g = await getGuards(true);
      setGuards(g);
      const e: Record<number, EditState> = {};
      g.forEach((guard) => {
        e[guard.id] = {
          name: guard.name,
          phone: guard.phone ?? "",
          role: guard.role ?? "",
          isActive: guard.is_active,
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
      await updateGuard(id, e.name.trim(), e.phone || null, e.role || null, e.isActive);
      showToast(`💾 ${e.name} עודכן`);
      load();
    } catch (err) {
      showToast(`שגיאה: ${(err as Error).message}`);
    }
  };

  const handleDelete = (guard: Guard) => {
    if (deleteTimerRef.current) clearTimeout(deleteTimerRef.current);
    setPendingDelete({ id: guard.id, name: guard.name });
    deleteTimerRef.current = setTimeout(async () => {
      await deleteGuard(guard.id);
      setPendingDelete(null);
      load();
    }, 5000);
  };

  const cancelDelete = () => {
    if (deleteTimerRef.current) clearTimeout(deleteTimerRef.current);
    setPendingDelete(null);
  };

  const setField = (id: number, field: keyof EditState, value: string) =>
    setEdits((prev) => ({ ...prev, [id]: { ...prev[id], [field]: value } }));

  const overloaded = guards.filter((g) => g.overloaded && g.is_active);
  const activeCount = guards.filter((g) => g.is_active).length;
  const q = searchQuery.trim().toLowerCase();
  const visibleGuards = q
    ? guards.filter((g) => g.name.toLowerCase().includes(q) || (g.role ?? "").toLowerCase().includes(q))
    : guards;

  return (
    <div className="fade-in space-y-4">
      {toast && (
        <div className="fixed top-20 right-4 left-4 max-w-sm mx-auto z-50">
          <div className="card border-primary/40 bg-primary/10 text-text text-sm text-center font-medium slide-in">
            {toast}
          </div>
        </div>
      )}

      {/* Undo delete toast */}
      {pendingDelete && (
        <div className="fixed bottom-24 right-4 left-4 max-w-sm mx-auto z-50 slide-in">
          <div className="bg-bg-card border-2 border-danger rounded-2xl p-4 flex items-center gap-3 shadow-2xl">
            <span className="text-danger text-sm flex-1 truncate">
              🗑 מוחק: {pendingDelete.name}
            </span>
            <button
              onClick={cancelDelete}
              className="flex items-center gap-1 text-xs font-bold text-danger border border-danger/40
                         hover:bg-danger/10 px-2.5 py-1.5 rounded-lg transition-all shrink-0"
            >
              <Undo2 size={13} />
              בטל
            </button>
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

      {/* Add — hidden for viewers */}
      {!readOnly && (
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
      )}

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
                  copyText(csv).then(() => showToast("📋 הועתק ללוח"));
                }}
                title="ייצא רשימה"
              >
                📋 ייצא
              </button>
            )}
            <span className="text-xs text-text-dim bg-bg-base px-2 py-1 rounded-full">
              {activeCount} פעילים · {guards.length - activeCount} לא פעילים
            </span>
          </div>
        </div>

        {/* Search */}
        <div className="relative">
          <Search size={14} className="absolute right-3 top-1/2 -translate-y-1/2 text-text-dim pointer-events-none" />
          <input
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="חיפוש לפי שם או תפקיד..."
            className="input pr-9 text-sm py-2"
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery("")}
              className="absolute left-3 top-1/2 -translate-y-1/2 text-text-dim hover:text-text"
            >
              <X size={13} />
            </button>
          )}
        </div>

        {loading && <SkeletonGuardCards />}
        {!loading && guards.length === 0 && (
          <div className="text-center text-text-dim py-6">אין אנשים – הוסף למעלה</div>
        )}

        <div className="space-y-2 max-h-[500px] overflow-y-auto">
          {visibleGuards.map((g) => {
            const e = edits[g.id];
            const isOpen = expanded === g.id;
            return (
              <div
                key={g.id}
                className={`rounded-xl border transition-all
                  ${g.overloaded ? "border-warning/30 bg-warning/5" : "border-bg-border bg-bg-base"}
                  ${!g.is_active ? "opacity-50" : ""}`}
              >
                {/* Main row */}
                <div className="flex items-center gap-2 p-2.5">
                  <input
                    value={e?.name ?? g.name}
                    onChange={(ev) => !readOnly && setField(g.id, "name", ev.target.value)}
                    onKeyDown={(ev) => ev.key === "Enter" && !readOnly && handleUpdate(g.id)}
                    readOnly={readOnly}
                    className={`input flex-1 text-sm py-1.5 h-8 ${readOnly ? "cursor-default" : ""}`}
                  />
                  <div className="flex gap-1 shrink-0 items-center">
                    <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-semibold shrink-0
                      ${g.is_active ? "bg-success/15 text-success" : "bg-bg-hover text-text-dim"}`}>
                      {g.is_active ? "פעיל" : "לא פעיל"}
                    </span>
                    <span className="pill-past">✅ {g.past}</span>
                    <span className="pill-future">🕐 {g.future}</span>
                  </div>
                  {!readOnly && (
                    <button
                      onClick={() => setExpanded(isOpen ? null : g.id)}
                      className="p-1.5 text-text-dim hover:text-text rounded-lg hover:bg-bg-border transition-colors"
                      title="פרטים נוספים"
                    >
                      <ChevronDown size={14} className={`transition-transform ${isOpen ? "rotate-180" : ""}`} />
                    </button>
                  )}
                  {!readOnly && (
                    <button
                      onClick={() => handleUpdate(g.id)}
                      className="p-1.5 text-text-dim hover:text-success rounded-lg hover:bg-success/10 transition-colors"
                    >
                      <Save size={15} />
                    </button>
                  )}
                  {!readOnly && (
                    <button
                      onClick={() => handleDelete(g)}
                      disabled={pendingDelete?.id === g.id}
                      className={`p-1.5 rounded-lg transition-colors ${
                        pendingDelete?.id === g.id
                          ? "text-danger opacity-40 cursor-not-allowed"
                          : "text-text-dim hover:text-danger hover:bg-danger/10"
                      }`}
                    >
                      <Trash2 size={15} />
                    </button>
                  )}
                </div>

                {/* Expanded: active toggle + phone + role */}
                {isOpen && (
                  <div className="px-3 pb-3 space-y-2 border-t border-bg-border pt-2 slide-in">
                    <label className="flex items-center gap-2 text-sm text-text cursor-pointer w-fit">
                      <input
                        type="checkbox"
                        checked={Boolean(e?.isActive)}
                        onChange={(ev) => setField(g.id, "isActive", ev.target.checked)}
                        className="w-4 h-4 accent-primary"
                      />
                      פעיל
                    </label>
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
