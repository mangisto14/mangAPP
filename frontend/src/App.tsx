import { useState } from "react";
import ShiftsTab from "./components/ShiftsTab";
import AddShiftTab from "./components/AddShiftTab";
import GuardsTab from "./components/GuardsTab";
import StatsTab from "./components/StatsTab";
import AbsencesTab from "./features/absences/AbsencesTab";

const TABS = [
  { id: "shifts",    icon: "📋", label: "משמרות"    },
  { id: "absences",  icon: "🚪", label: "יציאות"    },
  { id: "add",       icon: "➕", label: "הוסף"      },
  { id: "guards",    icon: "👥", label: "שומרים"    },
  { id: "stats",     icon: "📊", label: "סטטיסטיקה" },
] as const;

type TabId = (typeof TABS)[number]["id"];

export default function App() {
  const [tab, setTab] = useState<TabId>("shifts");

  return (
    <div className="min-h-screen pb-20">
      {/* Header */}
      <header className="sticky top-0 z-50 bg-bg-deep/90 backdrop-blur border-b border-bg-border">
        <div className="max-w-2xl mx-auto px-4 py-3">
          <h1 className="text-lg font-bold text-text">מצבת כוח</h1>
          <p className="text-xs text-text-dim">ניהול מצבת כוח</p>
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
      <nav className="fixed bottom-0 inset-x-0 z-50 bg-bg-deep/95 backdrop-blur border-t border-bg-border safe-bottom">
        <div className="max-w-2xl mx-auto flex">
          {TABS.map((t) => {
            const active = tab === t.id;
            return (
              <button
                key={t.id}
                onClick={() => setTab(t.id)}
                className={`flex-1 flex flex-col items-center gap-0.5 py-2.5 text-xs font-semibold transition-colors duration-150
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
    </div>
  );
}
