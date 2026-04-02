import { useEffect, useRef, useState } from "react";
import ShiftsTab from "./components/ShiftsTab";
import GuardsTab from "./components/GuardsTab";
import StatsTab from "./components/StatsTab";
import PinScreen from "./components/PinScreen";
import AbsencesTab from "./features/absences/AbsencesTab";
import RotationTab from "./features/rotation/RotationTab";
import { getSettings, updateSettings } from "./features/absences/api";
import type { AlertThreshold } from "./features/absences/types";
import { useDesign, type DesignPreset } from "./hooks/useDesign";
import { useFontSize } from "./hooks/useFontSize";
import { ReadOnlyContext } from "./hooks/useReadOnly";
import { ShiftsIcon, AbsencesIcon, RotationIcon, GuardsIcon, StatsIcon, AdminIcon } from "./components/TabIcons";
import AdminTab from "./components/AdminTab";

const TABS = [
  { id: "shifts",   Icon: ShiftsIcon,   label: "משמרות",    adminOnly: false },
  { id: "absences", Icon: AbsencesIcon, label: "יציאות",    adminOnly: false },
  { id: "rotation", Icon: RotationIcon, label: "סבב",       adminOnly: false },
  { id: "guards",   Icon: GuardsIcon,   label: "כוח אדם",   adminOnly: false },
  { id: "stats",    Icon: StatsIcon,    label: "סטטיסטיקה", adminOnly: false },
  { id: "admin",    Icon: AdminIcon,    label: "ניהול",      adminOnly: true  },
] as const;

type TabId = (typeof TABS)[number]["id"];

const LEVEL_LABELS: Record<AlertThreshold["level"], string> = {
  warning:  "🟡 אזהרה",
  danger:   "🟠 סכנה",
  critical: "🔴 קריטי",
};

const LEVEL_OPTIONS: AlertThreshold["level"][] = ["warning", "danger", "critical"];

// ── Design presets metadata ───────────────────────────────────────────────────
const DESIGN_PRESETS: { id: DesignPreset; label: string; swatches: string[]; desc: string }[] = [
  {
    id: "dark",
    label: "כהה",
    desc: "כחול לילה",
    swatches: ["#0d1520", "#2563eb", "#162033"],
  },
  {
    id: "light",
    label: "בהיר",
    desc: "לבן נקי",
    swatches: ["#f8fafc", "#2563eb", "#e2e8f0"],
  },
  {
    id: "modern",
    label: "מודרני",
    desc: "טרקוטה & זית",
    swatches: ["#F5F2EA", "#B85C38", "#556B2F"],
  },
  {
    id: "contrast",
    label: "ניגודיות",
    desc: "נגישות גבוהה",
    swatches: ["#000000", "#ffff00", "#00ff00"],
  },
];

// ── Design Picker Panel ───────────────────────────────────────────────────────
function DesignPicker({
  current,
  onChange,
  onClose,
}: {
  current: DesignPreset;
  onChange: (d: DesignPreset) => void;
  onClose: () => void;
}) {
  return (
    <div
      className="fixed inset-0 z-[60]"
      onClick={onClose}
      aria-hidden="true"
    >
      <div
        role="dialog"
        aria-label="בחר עיצוב"
        className="absolute top-[64px] left-4 bg-bg-card border border-bg-border rounded-2xl p-4 shadow-2xl w-64 scale-in"
        onClick={(e) => e.stopPropagation()}
      >
        <p className="text-xs font-bold text-text-dim uppercase tracking-widest mb-3 text-right">
          גרסאות עיצוב
        </p>
        <div className="flex flex-col gap-2">
          {DESIGN_PRESETS.map((preset) => {
            const active = current === preset.id;
            return (
              <button
                key={preset.id}
                onClick={() => { onChange(preset.id); onClose(); }}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-xl text-right transition-all duration-150 w-full
                  ${active
                    ? "bg-primary/10 border border-primary/30 text-text"
                    : "hover:bg-bg-hover text-text-muted hover:text-text border border-transparent"
                  }`}
              >
                {/* Swatches */}
                <div className="flex gap-1 shrink-0">
                  {preset.swatches.map((c, i) => (
                    <div
                      key={i}
                      className="w-4 h-4 rounded-full border border-white/10"
                      style={{ backgroundColor: c }}
                    />
                  ))}
                </div>
                {/* Labels */}
                <div className="flex-1 text-right">
                  <div className="text-sm font-semibold leading-none">{preset.label}</div>
                  <div className="text-[10px] text-text-dim mt-0.5">{preset.desc}</div>
                </div>
                {/* Active indicator */}
                {active && (
                  <div className="w-2 h-2 rounded-full bg-primary shrink-0" />
                )}
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}

// ── Settings Modal ────────────────────────────────────────────────────────────
function SettingsModal({ onClose }: { onClose: () => void }) {
  const [thresholds, setThresholds] = useState<AlertThreshold[]>([]);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    getSettings().then((s) => setThresholds(s.alert_thresholds ?? []));
  }, []);

  const add = () =>
    setThresholds((prev) => {
      const usedLevels = new Set(prev.map((t) => t.level));
      const nextLevel = (["warning", "danger", "critical"] as AlertThreshold["level"][])
        .find((l) => !usedLevels.has(l));
      if (!nextLevel) return prev; // all 3 types already added
      return [...prev, { minutes: 30, level: nextLevel }];
    });

  const remove = (i: number) =>
    setThresholds((prev) => prev.filter((_, idx) => idx !== i));

  const update = (i: number, patch: Partial<AlertThreshold>) =>
    setThresholds((prev) => prev.map((t, idx) => idx === i ? { ...t, ...patch } : t));

  const save = async () => {
    const sorted = [...thresholds].sort((a, b) => a.minutes - b.minutes);
    await updateSettings({ alert_thresholds: sorted });
    setSaved(true);
    setTimeout(() => { setSaved(false); onClose(); }, 800);
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/60 flex items-end" onClick={onClose} aria-hidden="true">
      <div
        role="dialog"
        aria-modal="true"
        aria-label="הגדרות"
        className="w-full bg-bg-card border-t border-bg-border rounded-t-2xl p-5 pb-8 space-y-5 slide-in max-w-2xl mx-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between">
          <h2 className="font-bold text-text text-lg">⚙️ הגדרות</h2>
          <button onClick={onClose} aria-label="סגור הגדרות" className="text-text-dim hover:text-text text-xl px-2 min-h-[44px] min-w-[44px] flex items-center justify-center">✕</button>
        </div>

        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-semibold text-text">ספי התראה לפי זמן בחוץ</p>
              <p className="text-xs text-text-dim mt-0.5">כל ספ משנה צבע את שורת השומר</p>
            </div>
            <button
              onClick={add}
              disabled={thresholds.length >= 3}
              className="btn-ghost text-xs px-3 py-1.5 disabled:opacity-40 disabled:cursor-not-allowed"
            >+ הוסף</button>
          </div>

          {thresholds.length === 0 ? (
            <p className="text-text-dim text-xs text-center py-3">אין ספי התראה — לחץ "הוסף"</p>
          ) : (
            <div className="space-y-2">
              {thresholds.map((t, i) => (
                <div key={i} className="flex items-center gap-2 bg-bg-base rounded-xl px-3 py-2">
                  <input
                    type="number"
                    min="1"
                    value={t.minutes}
                    onChange={(e) => update(i, { minutes: Number(e.target.value) })}
                    className="input w-20 text-sm text-center"
                  />
                  <span className="text-text-dim text-xs shrink-0">דק'</span>
                  <select
                    value={t.level}
                    onChange={(e) => update(i, { level: e.target.value as AlertThreshold["level"] })}
                    className="input flex-1 text-sm"
                  >
                    {LEVEL_OPTIONS.filter(
                      (l) => l === t.level || !thresholds.some((x, xi) => xi !== i && x.level === l)
                    ).map((l) => (
                      <option key={l} value={l}>{LEVEL_LABELS[l]}</option>
                    ))}
                  </select>
                  <button
                    onClick={() => remove(i)}
                    aria-label={`מחק סף התראה של ${t.minutes} דקות`}
                    className="text-danger hover:opacity-70 text-sm px-1 shrink-0 min-h-[44px] min-w-[44px] flex items-center justify-center"
                  >
                    🗑
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        <button onClick={save} className="btn-primary w-full">
          {saved ? "✅ נשמר!" : "שמור"}
        </button>
      </div>
    </div>
  );
}

// ── App ───────────────────────────────────────────────────────────────────────
export default function App() {
  const [tab, setTab] = useState<TabId>("shifts");
  const [pinReady, setPinReady] = useState<boolean | null>(null);
  const [readOnly, setReadOnly] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [showDesignPicker, setShowDesignPicker] = useState(false);
  const { design, setDesign } = useDesign();
  const { increase, decrease, canIncrease, canDecrease } = useFontSize();

  // PWA install prompt
  const deferredPrompt = useRef<any>(null);
  const [showInstall, setShowInstall] = useState(false);

  useEffect(() => {
    const handler = (e: Event) => {
      e.preventDefault();
      deferredPrompt.current = e;
      setShowInstall(true);
    };
    window.addEventListener("beforeinstallprompt", handler);
    return () => window.removeEventListener("beforeinstallprompt", handler);
  }, []);

  const handleInstall = async () => {
    const prompt = deferredPrompt.current;
    if (!prompt) return;
    prompt.prompt();
    const { outcome } = await prompt.userChoice;
    if (outcome === "accepted") {
      deferredPrompt.current = null;
      setShowInstall(false);
    }
  };

  // PIN gate
  useEffect(() => {
    if (sessionStorage.getItem("pin_ok") === "1") {
      setReadOnly(sessionStorage.getItem("pin_mode") === "viewer");
      setPinReady(true);
      return;
    }
    fetch((import.meta.env.VITE_API_URL ?? "") + "/api/pin/required")
      .then((r) => r.json())
      .then((d) => setPinReady(!d.required))
      .catch(() => setPinReady(true));
  }, []);

  if (pinReady === null) return null;
  if (pinReady === false) return (
    <PinScreen onSuccess={(mode) => { setReadOnly(mode === "viewer"); setPinReady(true); }} />
  );

  const isModern = design === "modern";

  return (
    <ReadOnlyContext.Provider value={readOnly}>
    <div className="min-h-screen pb-20">

      {/* ── Header ── */}
      <header className={`sticky top-0 z-50 border-b transition-colors duration-300
        ${isModern
          ? "bg-bg-deep/90 backdrop-blur-xl border-bg-border/60 shadow-sm"
          : "bg-bg-deep/90 backdrop-blur border-bg-border"
        }`}
      >
        <div className="max-w-2xl mx-auto px-4 py-3 flex items-center justify-between">
          <div>
            <h1 className={`text-lg font-bold text-text ${isModern ? "font-inter" : ""}`}>
              מצבת כוח
            </h1>
            <p className="text-xs text-text-dim">ניהול מצבת כוח</p>
          </div>

          <div className="flex items-center gap-1">
            {/* Design picker trigger */}
            <div className="relative">
              <button
                onClick={() => setShowDesignPicker((v) => !v)}
                className={`p-2 rounded-xl transition-all duration-150 min-h-[44px] min-w-[44px] flex items-center justify-center gap-1.5
                  ${showDesignPicker
                    ? "bg-primary/15 text-primary"
                    : "text-text-dim hover:text-text hover:bg-bg-base"
                  }`}
                title="שנה עיצוב"
                aria-label="שנה עיצוב"
                aria-expanded={showDesignPicker}
              >
                {/* Three colored dots as design icon */}
                <span className="flex gap-0.5">
                  <span className="w-2 h-2 rounded-full bg-primary inline-block" />
                  <span className="w-2 h-2 rounded-full bg-secondary inline-block" />
                  <span className="w-2 h-2 rounded-full bg-accent inline-block" />
                </span>
              </button>
            </div>

            {/* Settings — hidden for viewers */}
            {!readOnly && (
              <button
                onClick={() => setShowSettings(true)}
                className="p-2 text-text-dim hover:text-text rounded-xl hover:bg-bg-base transition-colors min-h-[44px] min-w-[44px] flex items-center justify-center"
                title="הגדרות"
                aria-label="הגדרות"
              >
                ⚙️
              </button>
            )}
          </div>
        </div>
      </header>

      {/* Design Picker Panel */}
      {showDesignPicker && (
        <DesignPicker
          current={design}
          onChange={setDesign}
          onClose={() => setShowDesignPicker(false)}
        />
      )}

      {/* PWA install banner */}
      {showInstall && (
        <div className="max-w-2xl mx-auto px-4 pt-3">
          <div className="card border-primary/30 bg-primary/5 flex items-center gap-3 slide-in">
            <span className="text-2xl shrink-0">🛡️</span>
            <p className="flex-1 text-sm text-text font-medium">
              הוסף מצבת כוח למסך הבית כאפליקציה
            </p>
            <button
              onClick={handleInstall}
              className="btn-primary text-xs px-3 py-1.5 shrink-0"
            >
              הוסף
            </button>
            <button
              onClick={() => setShowInstall(false)}
              aria-label="סגור הצעת התקנה"
              className="text-text-dim hover:text-text p-1 shrink-0 min-h-[44px] min-w-[44px] flex items-center justify-center"
            >
              ✕
            </button>
          </div>
        </div>
      )}

      {/* Content */}
      <main className="max-w-2xl mx-auto px-4 pt-5">
        {tab === "shifts"   && <ShiftsTab />}
        {tab === "absences" && !readOnly && <AbsencesTab />}
        {tab === "rotation" && <RotationTab />}
        {tab === "guards"   && <GuardsTab />}
        {tab === "stats"    && <StatsTab />}
        {tab === "admin"    && !readOnly && <AdminTab />}
      </main>

      {/* ── Bottom Navigation ── */}
      <nav
        aria-label="ניווט ראשי"
        className={`fixed bottom-0 inset-x-0 z-50 transition-colors duration-300
          ${isModern
            ? "bg-bg-deep/90 backdrop-blur-xl border-t border-bg-border/60 shadow-[0_-2px_12px_rgb(0,0,0,0.06)]"
            : "bg-bg-deep/95 backdrop-blur border-t border-bg-border"
          }`}
      >
        <div className="max-w-2xl mx-auto flex" role="tablist">
          {TABS.filter((t) => !(readOnly && (t.id === "absences" || t.adminOnly))).map((t) => {
            const active = tab === t.id;
            return (
              <button
                key={t.id}
                role="tab"
                aria-selected={active}
                aria-current={active ? "page" : undefined}
                onClick={() => setTab(t.id)}
                className={`relative flex-1 flex flex-col items-center gap-0.5 py-2.5 text-xs font-semibold transition-all duration-200
                  ${active
                    ? "text-primary"
                    : "text-text-dim hover:text-text-muted"
                  }`}
              >
                <t.Icon className={`w-6 h-6 transition-transform duration-200 ${active ? "scale-110" : ""}`} />
                <span>{t.label}</span>
                {active && (
                  <span
                    className="absolute bottom-0 w-8 h-0.5 rounded-full bg-primary"
                    aria-hidden="true"
                  />
                )}
              </button>
            );
          })}
        </div>
      </nav>

      {/* Font size FAB */}
      <div className="fixed bottom-20 left-3 z-40 flex flex-col gap-1">
        <button
          onClick={increase}
          disabled={!canIncrease}
          aria-label="הגדל גופן"
          className="w-9 h-9 rounded-full bg-bg-card border border-bg-border shadow-lg flex items-center justify-center text-text-muted hover:text-text hover:border-primary/50 transition-all disabled:opacity-30 disabled:cursor-not-allowed"
        >
          <span className="text-sm font-bold leading-none">A+</span>
        </button>
        <button
          onClick={decrease}
          disabled={!canDecrease}
          aria-label="הקטן גופן"
          className="w-9 h-9 rounded-full bg-bg-card border border-bg-border shadow-lg flex items-center justify-center text-text-muted hover:text-text hover:border-primary/50 transition-all disabled:opacity-30 disabled:cursor-not-allowed"
        >
          <span className="text-xs font-bold leading-none">A−</span>
        </button>
      </div>

      {showSettings && <SettingsModal onClose={() => setShowSettings(false)} />}
    </div>
    </ReadOnlyContext.Provider>
  );
}
