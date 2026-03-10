import { useEffect, useState } from "react";
import ShiftsTab from "./components/ShiftsTab";
import AddShiftTab from "./components/AddShiftTab";
import GuardsTab from "./components/GuardsTab";
import StatsTab from "./components/StatsTab";
import PinScreen from "./components/PinScreen";
import AbsencesTab from "./features/absences/AbsencesTab";
import { getSettings, updateSettings } from "./features/absences/api";

const TABS = [
  { id: "shifts",   icon: "📋", label: "משמרות"    },
  { id: "absences", icon: "🚪", label: "יציאות"    },
  { id: "add",      icon: "➕", label: "הוסף"      },
  { id: "guards",   icon: "👥", label: "שומרים"    },
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
          <p className="text-xs text-text-dim mb-2">ישלח התראה אדומה אם שומר בחוץ יותר מהזמן הנקוב. 0 = כבוי.</p>
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

  useEffect(() => {
    // If already verified in this session, skip PIN
    if (sessionStorage.getItem("pin_ok") === "1") {
      setPinReady(true);
      return;
    }
    fetch("/api/pin/required")
      .then((r) => r.json())
      .then((d) => {
        if (!d.required) {
          setPinReady(true);
        } else {
          setPinReady(false);
        }
      })
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
          <button
            onClick={() => setShowSettings(true)}
            className="p-2 text-text-dim hover:text-text rounded-xl hover:bg-bg-base transition-colors"
            title="הגדרות"
          >
            ⚙️
          </button>
        </div>
      </header>

      {/* Content */}
      <main className="max-w-2xl mx-auto px-4 pt-5">
        {tab === "shifts"   && <ShiftsTab />}
        {tab === "absences" && <AbsencesTab />}
        {tab === "add"      && <AddShiftTab onSaved={() => setTab("shifts")} />}
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
