import { useState } from "react";
import ShiftsTab from "./components/ShiftsTab";
import AddShiftTab from "./components/AddShiftTab";
import GuardsTab from "./components/GuardsTab";
import StatsTab from "./components/StatsTab";
import AbsencesTab from "./components/AbsencesTab";

const TABS = [
  { id: "shifts", label: "📋 משמרות" },
  { id: "absences", label: "🚪 יציאות" },
  { id: "add", label: "➕ הוסף" },
  { id: "guards", label: "👥 שומרים" },
  { id: "stats", label: "📊 סטטיסטיקה" },
] as const;

type TabId = (typeof TABS)[number]["id"];

export default function App() {
  const [tab, setTab] = useState<TabId>("shifts");

  return (
    <div className="min-h-screen pb-10">
      {/* Header */}
      <header className="sticky top-0 z-50 bg-bg-deep/90 backdrop-blur border-b border-bg-border">
        <div className="max-w-2xl mx-auto px-4 py-3 flex items-center justify-between">
          <div>
            <h1 className="text-lg font-bold text-text">
              🛡️ Smart Guard Manager
            </h1>
            <p className="text-xs text-text-dim">ניהול משמרות חכם</p>
          </div>
        </div>

        {/* Tabs */}
        <div className="max-w-2xl mx-auto px-4 pb-3">
          <div className="flex gap-1.5 bg-bg-card rounded-2xl p-1.5">
            {TABS.map((t) => (
              <button
                key={t.id}
                onClick={() => setTab(t.id)}
                className={`tab-btn ${tab === t.id ? "tab-btn-active" : "tab-btn-inactive"}`}
              >
                {t.label}
              </button>
            ))}
          </div>
        </div>
      </header>

      {/* Content */}
      <main className="max-w-2xl mx-auto px-4 pt-5">
        {tab === "shifts" && <ShiftsTab />}
        {tab === "absences" && <AbsencesTab />}
        {tab === "add" && <AddShiftTab onSaved={() => setTab("shifts")} />}
        {tab === "guards" && <GuardsTab />}
        {tab === "stats" && <StatsTab />}
      </main>
    </div>
  );
}
