import { useEffect, useState } from "react";

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

export default function Clock({ leftAt, alert }: { leftAt: string; alert?: boolean }) {
  const [, setTick] = useState(0);
  useEffect(() => {
    const id = setInterval(() => setTick((t) => t + 1), 1000);
    return () => clearInterval(id);
  }, []);

  const { days, h, m, s } = elapsed(leftAt);
  return (
    <span className={`font-mono text-sm font-bold tabular-nums ${alert ? "text-danger" : "text-warning"}`}>
      {days > 0 && (
        <span className="text-xs font-semibold ml-1 opacity-80">
          {days}י׳{" "}
        </span>
      )}
      {h}:{m}:{s}
    </span>
  );
}
