import { useEffect, useRef, useState } from "react";
import ShiftsTab from "./components/ShiftsTab";
import GuardsTab from "./components/GuardsTab";
import StatsTab from "./components/StatsTab";
import PinScreen from "./components/PinScreen";
import AbsencesTab from "./features/absences/AbsencesTab";
import RotationTab from "./features/rotation/RotationTab";
import { getSettings, updateSettings } from "./features/absences/api";
import { useTheme } from "./hooks/useTheme";

const TABS = [
  { id: "shifts",   icon: "📋", label: "משמרות"    },
  { id: "absences", icon: "🚪", label: "יציאות"    },
  { id: "rotation", icon: "🔄", label: "סבב"       },
  { id: "guards",   icon: "👥", label: "כוח אדם"   },
  { id: "stats",    icon: "📊", label: "סטטיסטיקה" },
] as const;

type TabId = (typeof TABS)[number]["id"];

// ── Settings Modal ────────────────────────────────────────────────────────────
function SettingsModal({ onClose }: { onClose: () => void }) {
  const [alertMin, setAlertMin] = useState<string>("");
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    getSettings().then((s) => setAlertMin(s.alert_minutes ? String(s.alert_minutes) : ""));
  }, []);

  const save = async () => {
    await updateSettings({ alert_minutes: alertMin ? Number(alertMin) : null });
    setSaved(true);
    setTimeout(() => { setSaved(false); onClose(); }, 800);
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/60 flex items-end" onClick={onClose}>
      <div
        className="w-full bg-bg-card border-t border-bg-border rounded-t-2xl p-5 pb-8 space-y-5 slide-in max-w-2xl mx-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between">
          <h2 className="font-bold text-text text-lg">⚙️ הגדרות</h2>
          <button onClick={onClose} className="text-text-dim hover:text-text text-xl px-2">✕</button>
        </div>

        <div>
          <label className="text-sm font-semibold text-text block mb-1">
            התרעה אחרי כמה דקות בחוץ?
          </label>
          <p className="text-xs text-text-dim mb-2">
            שורה תהפוך אדומה אם שומר בחוץ יותר מהזמן הנקוב. 0 = כבוי.
          </p>
          <div className="flex gap-2">
            <input
              type="number"
              min="0"
              value={alertMin}
              onChange={(e) => setAlertMin(e.target.value)}
              placeholder="0 = ללא התראה"
              className="input flex-1"
            />
            <span className="text-text-dim self-center text-sm">דקות</span>
          </div>
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
  const [showSettings, setShowSettings] = useState(false);
  const { theme, toggle: toggleTheme } = useTheme();

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
      setPinReady(true);
      return;
    }
    fetch("/api/pin/required")
      .then((r) => r.json())
      .then((d) => setPinReady(!d.required))
      .catch(() => setPinReady(true));
  }, []);

  if (pinReady === null) return null;
  if (pinReady === false) return <PinScreen onSuccess={() => setPinReady(true)} />;

  return (
    <div className="min-h-screen pb-20">
      {/* Header */}
      <header className="sticky top-0 z-50 bg-bg-deep/90 backdrop-blur border-b border-bg-border">
        <div className="max-w-2xl mx-auto px-4 py-3 flex items-center justify-between">
          <div>
            <h1 className="text-lg font-bold text-text">מצבת כוח</h1>
            <p className="text-xs text-text-dim">ניהול מצבת כוח</p>
          </div>
          <div className="flex items-center gap-1">
            {/* Theme toggle */}
            <button
              onClick={toggleTheme}
              className="p-2 text-text-dim hover:text-text rounded-xl hover:bg-bg-base transition-colors text-lg"
              title={theme === "dark" ? "מצב יום" : "מצב לילה"}
            >
              {theme === "dark" ? "☀️" : "🌙"}
            </button>
            {/* Settings */}
            <button
              onClick={() => setShowSettings(true)}
              className="p-2 text-text-dim hover:text-text rounded-xl hover:bg-bg-base transition-colors"
              title="הגדרות"
            >
              ⚙️
            </button>
          </div>
        </div>
      </header>

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
              className="text-text-dim hover:text-text p-1 shrink-0"
            >
              ✕
            </button>
          </div>
        </div>
      )}

      {/* Content */}
      <main className="max-w-2xl mx-auto px-4 pt-5">
        {tab === "shifts"   && <ShiftsTab />}
        {tab === "absences" && <AbsencesTab />}
        {tab === "rotation" && <RotationTab />}
        {tab === "guards"   && <GuardsTab />}
        {tab === "stats"    && <StatsTab />}
      </main>

      {/* Bottom Navigation */}
      <nav className="fixed bottom-0 inset-x-0 z-50 bg-bg-deep/95 backdrop-blur border-t border-bg-border">
        <div className="max-w-2xl mx-auto flex">
          {TABS.map((t) => {
            const active = tab === t.id;
            return (
              <button
                key={t.id}
                onClick={() => setTab(t.id)}
                className={`relative flex-1 flex flex-col items-center gap-0.5 py-2.5 text-xs font-semibold transition-colors duration-150
                  ${active ? "text-primary" : "text-text-dim hover:text-text-muted"}`}
              >
                <span className="text-xl leading-none">{t.icon}</span>
                <span>{t.label}</span>
                {active && (
                  <span className="absolute bottom-0 w-8 h-0.5 bg-primary rounded-full" />
                )}
              </button>
            );
          })}
        </div>
      </nav>

      {showSettings && <SettingsModal onClose={() => setShowSettings(false)} />}
    </div>
  );
}
