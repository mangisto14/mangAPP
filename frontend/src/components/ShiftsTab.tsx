import { useEffect, useRef, useState } from "react";
import { Trash2, Pencil, MessageCircle, Copy, Check, X, Plus, ChevronDown, ChevronUp, Undo2 } from "lucide-react";
import { getShifts, deleteShift, getWhatsapp } from "../api";
import type { Shift } from "../types";
import AddShiftTab from "./AddShiftTab";
import EditShiftModal from "./EditShiftModal";
import { SkeletonShiftCards } from "./Skeleton";
import { useReadOnly } from "../hooks/useReadOnly";

const SWIPE_THRESHOLD = 72;

function SwipeableRow({
  shift,
  onEdit,
  onDelete,
  pendingDelete,
}: {
  shift: Shift;
  onEdit: () => void;
  onDelete: () => void;
  pendingDelete: boolean;
}) {
  const startXRef = useRef(0);
  const [offset, setOffset] = useState(0);
  const [swiped, setSwiped] = useState(false);

  const onTouchStart = (e: React.TouchEvent) => {
    startXRef.current = e.touches[0].clientX;
  };

  const onTouchMove = (e: React.TouchEvent) => {
    const dx = e.touches[0].clientX - startXRef.current;
    if (dx < 0) setOffset(Math.max(dx, -SWIPE_THRESHOLD));
    else if (swiped) setOffset(Math.min(0, -SWIPE_THRESHOLD + dx));
  };

  const onTouchEnd = () => {
    if (offset <= -SWIPE_THRESHOLD + 4) {
      setOffset(-SWIPE_THRESHOLD);
      setSwiped(true);
    } else {
      setOffset(0);
      setSwiped(false);
    }
  };

  const close = () => { setOffset(0); setSwiped(false); };

  return (
    <div className="relative overflow-hidden rounded-xl">
      {/* Delete zone behind the card */}
      <div
        className="absolute inset-y-0 left-0 flex items-center justify-center bg-danger"
        style={{ width: SWIPE_THRESHOLD, borderRadius: "inherit" }}
      >
        <button
          onClick={() => { close(); onDelete(); }}
          disabled={pendingDelete}
          className="flex items-center justify-center w-full h-full text-white"
          aria-label="מחיקה"
        >
          <Trash2 size={18} />
        </button>
      </div>

      {/* Card — slides right→left on swipe */}
      <div
        className={`card flex items-center justify-between gap-3 ${shift.is_past ? "opacity-60" : ""}`}
        style={{
          transform: `translateX(${offset}px)`,
          transition: offset === 0 || offset === -SWIPE_THRESHOLD ? "transform 0.2s ease" : "none",
          touchAction: "pan-y",
        }}
        onTouchStart={onTouchStart}
        onTouchMove={onTouchMove}
        onTouchEnd={onTouchEnd}
        onClick={swiped ? close : undefined}
      >
        <div className="flex items-center gap-3 min-w-0">
          <span className={`w-2 h-2 rounded-full flex-shrink-0 ${shift.is_past ? "bg-muted" : "bg-primary-light"}`} />
          <span className="text-sm font-bold text-text-muted tabular-nums">
            {formatTime(shift.start_time)}–{formatTime(shift.end_time)}
          </span>
          <span className="text-sm text-text truncate">{shift.names.join(", ")}</span>
        </div>
        <button
          onClick={(e) => { e.stopPropagation(); onEdit(); }}
          className="flex-shrink-0 text-text-dim hover:text-primary transition-colors p-1 rounded-lg hover:bg-primary/10"
          aria-label="עריכה"
        >
          <Pencil size={14} />
        </button>
      </div>
    </div>
  );
}

interface PendingDelete {
  id: number;
  label: string;
}

type Filter = "all" | "future" | "past" | "today" | "range";

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

/** Returns YYYY-MM-DD for a given Date */
function toYMD(d: Date) {
  return d.toISOString().slice(0, 10);
}

/** Returns today's date as a range (from=to=today) */
function todayRange(): { from: string; to: string } {
  const today = toYMD(new Date());
  return { from: today, to: today };
}

export default function ShiftsTab() {
  const [shifts, setShifts] = useState<Shift[]>([]);
  const [filter, setFilter] = useState<Filter>("all");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showAddPanel, setShowAddPanel] = useState(false);
  const [collapsedDates, setCollapsedDates] = useState<Set<string>>(new Set());
  const [pendingDelete, setPendingDelete] = useState<PendingDelete | null>(null);
  const deleteTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [editingShift, setEditingShift] = useState<Shift | null>(null);
  const [showSwipeHint, setShowSwipeHint] = useState(
    () => !localStorage.getItem("shifts_swipe_hint_dismissed")
  );
  const readOnly = useReadOnly();

  const dismissSwipeHint = () => {
    localStorage.setItem("shifts_swipe_hint_dismissed", "1");
    setShowSwipeHint(false);
  };

  /** Derive the backend filter + date range from UI state */
  function getApiParams(): {
    backendFilter: "all" | "future" | "past";
    from?: string;
    to?: string;
  } {
    if (filter === "today") {
      const { from, to } = todayRange();
      return { backendFilter: "all", from, to };
    }
    if (filter === "range") {
      return {
        backendFilter: "all",
        from: dateFrom || undefined,
        to: dateTo || undefined,
      };
    }
    return { backendFilter: filter as "all" | "future" | "past" };
  }

  const load = async () => {
    setLoading(true);
    setError("");
    try {
      const { backendFilter, from, to } = getApiParams();
      setShifts(await getShifts(backendFilter, from, to));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [filter, dateFrom, dateTo]);

  useEffect(() => {
    const entries = Object.keys(grouped);
    setCollapsedDates(new Set(entries.slice(1)));
  }, [filter, dateFrom, dateTo, shifts.length]);

  const handleDelete = (shift: Shift) => {
    // Cancel any existing pending delete
    if (deleteTimerRef.current) clearTimeout(deleteTimerRef.current);

    const label = `${formatTime(shift.start_time)}–${formatTime(shift.end_time)} · ${shift.names.join(", ")}`;
    setPendingDelete({ id: shift.id, label });

    deleteTimerRef.current = setTimeout(async () => {
      await deleteShift(shift.id);
      setPendingDelete(null);
      load();
    }, 5000);
  };

  const cancelDelete = () => {
    if (deleteTimerRef.current) clearTimeout(deleteTimerRef.current);
    setPendingDelete(null);
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

  const handleToday = () => {
    setDateFrom("");
    setDateTo("");
    setFilter("today");
  };

  const handleFilterBtn = (f: Filter) => {
    if (f !== "range") {
      setDateFrom("");
      setDateTo("");
    }
    setFilter(f);
  };

  const clearRange = () => {
    setDateFrom("");
    setDateTo("");
    setFilter("all");
  };

  const toggleDate = (date: string) => {
    setCollapsedDates((prev) => {
      const next = new Set(prev);
      if (next.has(date)) next.delete(date);
      else next.add(date);
      return next;
    });
  };

  // Group by date
  const grouped: Record<string, Shift[]> = {};
  for (const s of shifts) {
    const { date } = formatDate(s.start_time);
    if (!grouped[date]) grouped[date] = [];
    grouped[date].push(s);
  }

  const FILTERS: { id: Filter; label: string }[] = [
    { id: "today", label: "היום" },
    { id: "future", label: "עתידי" },
    { id: "past", label: "עבר" },
    { id: "all", label: "הכל" },
    { id: "range", label: "טווח" },
  ];

  return (
    <div className="fade-in space-y-4">
      {/* Edit modal */}
      {editingShift && (
        <EditShiftModal
          shift={editingShift}
          onClose={() => setEditingShift(null)}
          onSaved={() => { setEditingShift(null); load(); }}
        />
      )}
      {/* Swipe hint banner — shown once until dismissed */}
      {!readOnly && showSwipeHint && (
        <div className="flex items-center gap-3 bg-primary/8 border border-primary/20 rounded-xl px-4 py-3 slide-in">
          <span className="text-lg select-none">👈</span>
          <span className="text-sm text-text-muted flex-1">
            גרור משמרת שמאלה כדי למחוק אותה
          </span>
          <button
            onClick={dismissSwipeHint}
            className="text-text-dim hover:text-text transition-colors p-1 flex-shrink-0"
            aria-label="סגור"
          >
            <X size={15} />
          </button>
        </div>
      )}
      {/* Undo toast */}
      {pendingDelete && (
        <div className="fixed bottom-24 right-4 left-4 max-w-sm mx-auto z-50 slide-in">
          <div className="bg-bg-card border-2 border-danger rounded-2xl p-4 flex items-center gap-3 shadow-2xl">
            <span className="text-danger text-sm flex-1 truncate">
              🗑 מוחק: {pendingDelete.label}
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
      {/* Toolbar */}
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div className="flex gap-2 flex-wrap">
          {FILTERS.map((f) => (
            <button
              key={f.id}
              onClick={() => f.id === "today" ? handleToday() : handleFilterBtn(f.id)}
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
          {!readOnly && (
            <button
              onClick={handleWhatsApp}
              className="flex items-center gap-1.5 bg-success/10 hover:bg-success/20 text-success
                         border border-success/30 px-3 py-1.5 rounded-xl text-sm font-semibold transition-all"
            >
              <MessageCircle size={15} />
              שלח
            </button>
          )}
        </div>
      </div>

      {/* Add shift panel toggle — hidden for viewers */}
      {!readOnly && (
        <>
          <button
            onClick={() => setShowAddPanel((v) => !v)}
            className={`w-full flex items-center justify-between px-4 py-3 rounded-xl border
                        font-semibold text-sm transition-all
                        ${showAddPanel
                          ? "bg-primary/10 border-primary/40 text-primary-light"
                          : "bg-bg-card border-bg-border text-text-muted hover:text-text hover:border-primary/30"
                        }`}
          >
            <span className="flex items-center gap-2">
              <Plus size={16} />
              הוסף משמרת
            </span>
            <ChevronDown
              size={16}
              className={`transition-transform duration-200 ${showAddPanel ? "rotate-180" : ""}`}
            />
          </button>

          {showAddPanel && (
            <div className="slide-in">
              <AddShiftTab onSaved={() => { setShowAddPanel(false); load(); }} />
            </div>
          )}
        </>
      )}

      {/* Date range inputs */}
      {filter === "range" && (
        <div className="flex items-center gap-3 flex-wrap card py-3">
          <span className="text-sm text-text-muted font-semibold">מ-</span>
          <input
            type="date"
            value={dateFrom}
            onChange={(e) => setDateFrom(e.target.value)}
            className="bg-bg-border text-text text-sm rounded-lg px-3 py-1.5 border border-bg-border
                       focus:outline-none focus:border-primary/50"
          />
          <span className="text-sm text-text-muted font-semibold">עד-</span>
          <input
            type="date"
            value={dateTo}
            onChange={(e) => setDateTo(e.target.value)}
            className="bg-bg-border text-text text-sm rounded-lg px-3 py-1.5 border border-bg-border
                       focus:outline-none focus:border-primary/50"
          />
          <button
            onClick={clearRange}
            className="text-text-dim hover:text-danger transition-colors p-1"
            title="נקה סינון"
          >
            <X size={15} />
          </button>
        </div>
      )}

      {/* Today indicator */}
      {filter === "today" && (
        <div className="text-xs text-primary-light bg-primary/10 px-3 py-1.5 rounded-xl
                        border border-primary/20 inline-flex items-center gap-2">
          היום: {todayRange().from.split("-").reverse().join("/")}
        </div>
      )}

      {/* Content */}
      {loading && <SkeletonShiftCards />}
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
          const isCollapsed = collapsedDates.has(date);
          return (
            <div key={date} className="space-y-2 slide-in">
              {/* Date header */}
              <div className="flex items-center gap-2 px-1">
                <button
                  onClick={() => toggleDate(date)}
                  className="inline-flex items-center gap-2 text-xs font-bold text-primary-light bg-primary/10 px-3 py-1
                             rounded-full border border-primary/20 hover:bg-primary/15 transition-all"
                >
                  <span>יום {dayHe} · {date}</span>
                  <span className="text-primary/70">({dayShifts.length})</span>
                  {isCollapsed ? <ChevronDown size={12} /> : <ChevronUp size={12} />}
                </button>
                <div className="flex-1 h-px bg-bg-border" />
              </div>

              {/* Swipe hint inline */}
              {!isCollapsed && !readOnly && (
                <div className="flex items-center gap-1 px-1 pb-0.5">
                  <span className="text-[10px] text-text-dim select-none">← החלק למחיקה</span>
                </div>
              )}

              {/* Shift rows */}
              {!isCollapsed && dayShifts.map((s) =>
                readOnly ? (
                  <div
                    key={s.id}
                    className={`card flex items-center gap-3 ${s.is_past ? "opacity-60" : ""}`}
                  >
                    <span className={`w-2 h-2 rounded-full flex-shrink-0 ${s.is_past ? "bg-muted" : "bg-primary-light"}`} />
                    <span className="text-sm font-bold text-text-muted tabular-nums">
                      {formatTime(s.start_time)}–{formatTime(s.end_time)}
                    </span>
                    <span className="text-sm text-text truncate">{s.names.join(", ")}</span>
                  </div>
                ) : (
                  <SwipeableRow
                    key={s.id}
                    shift={s}
                    onEdit={() => setEditingShift(s)}
                    onDelete={() => handleDelete(s)}
                    pendingDelete={pendingDelete?.id === s.id}
                  />
                )
              )}
            </div>
          );
        })}
    </div>
  );
}
