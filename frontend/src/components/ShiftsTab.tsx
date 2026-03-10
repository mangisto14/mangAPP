import { useEffect, useState } from "react";
import { Trash2, MessageCircle, Copy, Check } from "lucide-react";
import { getShifts, deleteShift, getWhatsapp } from "../api";
import type { Shift } from "../types";

type Filter = "all" | "future" | "past";

const HE_DAY: Record<string, string> = {
  Sunday: "ראשון",
  Monday: "שני",
  Tuesday: "שלישי",
  Wednesday: "רביעי",
  Thursday: "חמישי",
  Friday: "שישי",
  Saturday: "שבת",
};

function formatDate(iso: string) {
  const d = new Date(iso);
  const day = d.toLocaleDateString("en-US", { weekday: "long" });
  const dd = String(d.getDate()).padStart(2, "0");
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const yyyy = d.getFullYear();
  return { date: `${dd}/${mm}/${yyyy}`, dayHe: HE_DAY[day] ?? day };
}

function formatTime(iso: string) {
  const d = new Date(iso);
  return `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
}

export default function ShiftsTab() {
  const [shifts, setShifts] = useState<Shift[]>([]);
  const [filter, setFilter] = useState<Filter>("all");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = async () => {
    setLoading(true);
    setError("");
    try {
      setShifts(await getShifts(filter));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [filter]);

  const handleDelete = async (id: number) => {
    if (!confirm("למחוק משמרת זו?")) return;
    await deleteShift(id);
    load();
  };

  const [copied, setCopied] = useState(false);

  const handleWhatsApp = async () => {
    const { url } = await getWhatsapp();
    if (url) window.open(url, "_blank");
    else alert("אין משמרות עתידיות לשלוח");
  };

  const handleCopy = async () => {
    const { text } = await getWhatsapp();
    if (!text) { alert("אין משמרות עתידיות להעתיק"); return; }
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // Group by date
  const grouped: Record<string, Shift[]> = {};
  for (const s of shifts) {
    const { date } = formatDate(s.start_time);
    if (!grouped[date]) grouped[date] = [];
    grouped[date].push(s);
  }

  const FILTERS: { id: Filter; label: string }[] = [
    { id: "all", label: "הכל" },
    { id: "future", label: "עתידי" },
    { id: "past", label: "עבר" },
  ];

  return (
    <div className="fade-in space-y-4">
      {/* Toolbar */}
      <div className="flex items-center justify-between gap-3">
        <div className="flex gap-2">
          {FILTERS.map((f) => (
            <button
              key={f.id}
              onClick={() => setFilter(f.id)}
              className={`px-4 py-1.5 rounded-full text-sm font-semibold transition-all ${
                filter === f.id
                  ? "bg-primary text-white shadow shadow-primary/30"
                  : "bg-bg-card text-text-muted hover:text-text"
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>
        <div className="flex gap-2">
          <button
            onClick={handleCopy}
            className="flex items-center gap-1.5 bg-bg-card hover:bg-bg-border text-text-muted
                       border border-bg-border px-3 py-1.5 rounded-xl text-sm font-semibold transition-all"
            title="העתק טקסט"
          >
            {copied ? <Check size={15} className="text-success" /> : <Copy size={15} />}
            {copied ? "הועתק!" : "העתק"}
          </button>
          <button
            onClick={handleWhatsApp}
            className="flex items-center gap-1.5 bg-success/10 hover:bg-success/20 text-success
                       border border-success/30 px-3 py-1.5 rounded-xl text-sm font-semibold transition-all"
          >
            <MessageCircle size={15} />
            שלח
          </button>
        </div>
      </div>

      {/* Content */}
      {loading && (
        <div className="text-center text-text-dim py-10">טוען...</div>
      )}
      {error && (
        <div className="card border-danger/30 text-danger text-sm">{error}</div>
      )}
      {!loading && !error && shifts.length === 0 && (
        <div className="card text-center text-text-dim py-10">
          אין משמרות להצגה
        </div>
      )}

      {!loading &&
        Object.entries(grouped).map(([date, dayShifts]) => {
          const { dayHe } = formatDate(dayShifts[0].start_time);
          return (
            <div key={date} className="space-y-2 slide-in">
              {/* Date header */}
              <div className="flex items-center gap-2 px-1">
                <div
                  className="text-xs font-bold text-primary-light bg-primary/10 px-3 py-1
                                rounded-full border border-primary/20"
                >
                  יום {dayHe} · {date}
                </div>
                <div className="flex-1 h-px bg-bg-border" />
              </div>

              {/* Shift rows */}
              {dayShifts.map((s) => (
                <div
                  key={s.id}
                  className={`card flex items-center justify-between gap-3 transition-all hover:border-bg-border/60
                    ${s.is_past ? "opacity-60" : ""}`}
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <span
                      className={`w-2 h-2 rounded-full flex-shrink-0 ${
                        s.is_past ? "bg-muted" : "bg-primary-light"
                      }`}
                    />
                    <span className="text-sm font-bold text-text-muted tabular-nums">
                      {formatTime(s.start_time)}–{formatTime(s.end_time)}
                    </span>
                    <span className="text-sm text-text truncate">
                      {s.names.join(", ")}
                    </span>
                  </div>
                  <button
                    onClick={() => handleDelete(s.id)}
                    className="flex-shrink-0 text-text-dim hover:text-danger transition-colors p-1 rounded-lg
                               hover:bg-danger/10"
                  >
                    <Trash2 size={15} />
                  </button>
                </div>
              ))}
            </div>
          );
        })}
    </div>
  );
}
