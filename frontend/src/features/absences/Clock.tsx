import { useEffect, useState } from "react";

export type AlertLevel = "warning" | "danger" | "critical" | null;

function elapsed(leftAt: string) {
  const diff = Math.max(
    0,
    Math.floor((Date.now() - new Date(leftAt.endsWith("Z") ? leftAt : leftAt + "Z").getTime()) / 1000)
  );
  const days = Math.floor(diff / 86400);
  const h = String(Math.floor((diff % 86400) / 3600)).padStart(2, "0");
  const m = String(Math.floor((diff % 3600) / 60)).padStart(2, "0");
  const s = String(diff % 60).padStart(2, "0");
  return { days, h, m, s };
}

const LEVEL_COLOR: Record<NonNullable<AlertLevel>, string> = {
  warning:  "text-warning",
  danger:   "text-orange-400",
  critical: "text-danger",
};

export default function Clock({ leftAt, level }: { leftAt: string; level?: AlertLevel }) {
  const [, setTick] = useState(0);
  useEffect(() => {
    const id = setInterval(() => setTick((t) => t + 1), 1000);
    return () => clearInterval(id);
  }, []);

  const { days, h, m, s } = elapsed(leftAt);
  const colorClass = level ? LEVEL_COLOR[level] : "text-warning";

  if (days > 0) {
    return (
      <span className={`font-mono text-sm font-bold tabular-nums ${colorClass}`}>
        {days} יום {h}:{m}
      </span>
    );
  }

  return (
    <span className={`font-mono text-sm font-bold tabular-nums ${colorClass}`}>
      {h}:{m}:{s}
    </span>
  );
}
