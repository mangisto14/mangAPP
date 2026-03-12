import { useState } from "react";
import { Trash2, Plus } from "lucide-react";
import type { RotationConfig, RotationRole } from "./types";
import {
  updateRotationConfig,
  updateRotationRole,
  deleteRotationRole,
  updateRotationSlots,
} from "./api";
import GuardAutocomplete from "./GuardAutocomplete";

interface Props {
  config: RotationConfig;
  guardNames: string[];
  onClose: () => void;
  onSaved: () => void;
}

export default function EditRotationModal({ config, guardNames, onClose, onSaved }: Props) {
  const [startDate, setStartDate] = useState(config.start_date);
  const [periodDays, setPeriodDays] = useState(String(config.period_days));
  const [roles, setRoles] = useState<RotationRole[]>(
    config.roles.map((r) => ({
      ...r,
      slots: Array.from({ length: 9 }, (_, i) => r.slots[i] ?? []),
    }))
  );
  const [newRoleName, setNewRoleName] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const updateSlotText = (roleIdx: number, slotIdx: number, text: string) => {
    setRoles((prev) => {
      const next = [...prev];
      const role = { ...next[roleIdx], slots: [...next[roleIdx].slots] };
      role.slots[slotIdx] = text.split(",").map((s) => s.trim()).filter(Boolean);
      next[roleIdx] = role;
      return next;
    });
  };

  const updateRoleName = (roleIdx: number, name: string) => {
    setRoles((prev) => {
      const next = [...prev];
      next[roleIdx] = { ...next[roleIdx], name };
      return next;
    });
  };

  const removeRole = (roleIdx: number) => {
    setRoles((prev) => prev.filter((_, i) => i !== roleIdx));
  };

  const handleAddRole = () => {
    const name = newRoleName.trim();
    if (!name) return;
    setRoles((prev) => [
      ...prev,
      { id: -Date.now(), name, position: prev.length, slots: Array.from({ length: 9 }, () => []) },
    ]);
    setNewRoleName("");
  };

  const handleSave = async () => {
    setSaving(true);
    setError("");
    try {
      await updateRotationConfig(startDate, Number(periodDays) || 2);

      const originalIds = new Set(config.roles.map((r) => r.id));
      const currentIds = new Set(roles.filter((r) => r.id > 0).map((r) => r.id));

      // Delete removed roles
      for (const orig of config.roles) {
        if (!currentIds.has(orig.id)) {
          await deleteRotationRole(orig.id);
        }
      }

      // Update existing / add new
      for (const role of roles) {
        if (role.id > 0 && originalIds.has(role.id)) {
          await updateRotationRole(role.id, role.name);
          await updateRotationSlots(role.id, role.slots);
        } else {
          // new role — add then update slots
          const r = await fetch(
            (import.meta.env.VITE_API_URL ?? "") + "/api/rotation/roles",
            {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ name: role.name }),
            }
          );
          if (r.ok) {
            const data = await r.json();
            await updateRotationSlots(data.id, role.slots);
          }
        }
      }
      onSaved();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/60 flex items-end" onClick={onClose}>
      <div
        className="w-full bg-bg-card border-t border-bg-border rounded-t-2xl pb-8 slide-in max-w-2xl mx-auto
                   max-h-[90vh] flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-bg-border shrink-0">
          <h2 className="font-bold text-text text-lg">✏️ עריכת סבב</h2>
          <button onClick={onClose} className="text-text-dim hover:text-text text-xl px-2">✕</button>
        </div>

        <div className="overflow-y-auto flex-1 p-5 space-y-5">
          {/* Config */}
          <div className="card space-y-3">
            <h3 className="font-semibold text-text text-sm">הגדרות כלליות</h3>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs text-text-dim mb-1 block">תאריך תחילת סבב</label>
                <input
                  type="date"
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                  className="input text-sm w-full"
                />
              </div>
              <div>
                <label className="text-xs text-text-dim mb-1 block">ימים לתקופה</label>
                <input
                  type="number"
                  min="1"
                  value={periodDays}
                  onChange={(e) => setPeriodDays(e.target.value)}
                  className="input text-sm w-full"
                />
              </div>
            </div>
          </div>

          {/* Roles */}
          {roles.map((role, ri) => (
            <div key={role.id} className="card space-y-3">
              <div className="flex items-center gap-2">
                <input
                  value={role.name}
                  onChange={(e) => updateRoleName(ri, e.target.value)}
                  className="input text-sm flex-1 font-semibold"
                />
                <button
                  onClick={() => removeRole(ri)}
                  className="text-text-dim hover:text-danger transition-colors p-1"
                >
                  <Trash2 size={16} />
                </button>
              </div>
              {Array.from({ length: 9 }, (_, si) => {
                const periodLabels = ["א-ג", "ג-ה", "ו-א"];
                return (
                  <div key={si}>
                    <label className="text-xs text-text-dim mb-1 block">
                      תקופה {si + 1} · {periodLabels[si % 3]} (מופרד בפסיק)
                    </label>
                    <GuardAutocomplete
                      value={(role.slots[si] ?? []).join(", ")}
                      onChange={(v) => updateSlotText(ri, si, v)}
                      guardNames={guardNames}
                    />
                  </div>
                );
              })}
            </div>
          ))}

          {/* Add role */}
          <div className="flex gap-2">
            <input
              value={newRoleName}
              onChange={(e) => setNewRoleName(e.target.value)}
              placeholder="שם תפקיד חדש..."
              className="input text-sm flex-1"
              onKeyDown={(e) => e.key === "Enter" && handleAddRole()}
            />
            <button onClick={handleAddRole} className="btn-primary flex items-center gap-1 px-3">
              <Plus size={16} />
              הוסף תפקיד
            </button>
          </div>

          {error && (
            <div className="text-danger text-sm bg-danger/10 border border-danger/30 rounded-xl p-3">
              {error}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-5 border-t border-bg-border shrink-0">
          <button
            onClick={handleSave}
            disabled={saving}
            className="btn-primary w-full"
          >
            {saving ? "שומר..." : "💾 שמור שינויים"}
          </button>
        </div>
      </div>
    </div>
  );
}
