import { useState } from "react";

const BASE = (import.meta.env.VITE_API_URL ?? "") + "/api";

async function verifyPin(pin: string): Promise<{ ok: boolean; mode: "admin" | "viewer" }> {
  const res = await fetch(`${BASE}/pin/verify?pin=${pin}`);
  if (!res.ok) return { ok: false, mode: "admin" };
  const data = await res.json();
  return { ok: data.ok, mode: data.mode ?? "admin" };
}

export default function PinScreen({ onSuccess }: { onSuccess: (mode: "admin" | "viewer") => void }) {
  const [digits, setDigits] = useState<string[]>([]);
  const [error, setError] = useState(false);
  const [shake, setShake] = useState(false);
  const [loading, setLoading] = useState(false);

  const append = async (d: string) => {
    if (loading || digits.length >= 4) return;
    const next = [...digits, d];
    setDigits(next);
    setError(false);

    if (next.length === 4) {
      setLoading(true);
      const result = await verifyPin(next.join(""));
      setLoading(false);
      if (result.ok) {
        sessionStorage.setItem("pin_ok", "1");
        sessionStorage.setItem("pin_mode", result.mode);
        onSuccess(result.mode);
      } else {
        setShake(true);
        setError(true);
        setTimeout(() => {
          setShake(false);
          setDigits([]);
        }, 600);
      }
    }
  };

  const del = () => {
    if (loading) return;
    setDigits((d) => d.slice(0, -1));
    setError(false);
  };

  const keys = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "", "0", "⌫"];

  return (
    <div className="fixed inset-0 bg-bg-deep flex flex-col items-center justify-center gap-8 px-6">
      <div className="text-center">
        <h1 className="text-2xl font-bold text-text">מצבת כוח</h1>
        <p className="text-text-dim text-sm mt-1">הזן קוד כניסה</p>
      </div>

      {/* Dots */}
      <div
        className={`flex gap-4 ${shake ? "animate-shake" : ""}`}
        aria-label={`קוד PIN: ${digits.length} מתוך 4 ספרות הוזנו`}
        aria-live="polite"
      >
        {[0, 1, 2, 3].map((i) => (
          <div
            key={i}
            className={`w-4 h-4 rounded-full border-2 transition-all duration-150
              ${digits.length > i
                ? error
                  ? "bg-danger border-danger"
                  : "bg-primary border-primary"
                : "border-bg-border bg-transparent"
              }`}
          />
        ))}
      </div>

      {error && (
        <p role="alert" className="text-danger text-sm font-medium -mt-4">קוד שגוי, נסה שוב</p>
      )}

      {/* Numpad */}
      <div className="grid grid-cols-3 gap-3 w-full max-w-xs" role="group" aria-label="לוח מקשים">
        {keys.map((k, i) => (
          <button
            key={i}
            disabled={loading || k === ""}
            onClick={() => (k === "⌫" ? del() : k !== "" ? append(k) : undefined)}
            aria-label={k === "⌫" ? "מחק ספרה" : k !== "" ? `ספרה ${k}` : undefined}
            className={`h-16 rounded-2xl text-xl font-semibold transition-all duration-100 active:scale-95
              ${k === ""
                ? "invisible"
                : k === "⌫"
                ? "bg-bg-card text-text-muted hover:bg-bg-border"
                : "bg-bg-card text-text hover:bg-bg-border active:bg-primary/20"
              }`}
          >
            {k}
          </button>
        ))}
      </div>
    </div>
  );
}
