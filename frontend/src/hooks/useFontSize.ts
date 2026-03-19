import { useEffect, useState } from "react";

const SIZES = [14, 16, 18, 20] as const;
type FontSize = (typeof SIZES)[number];

const STORAGE_KEY = "font-size";
const DEFAULT: FontSize = 16;

function clamp(v: number): FontSize {
  const nearest = SIZES.reduce((a, b) =>
    Math.abs(b - v) < Math.abs(a - v) ? b : a
  );
  return nearest;
}

export function useFontSize() {
  const [size, setSize] = useState<FontSize>(() => {
    const stored = Number(localStorage.getItem(STORAGE_KEY));
    return stored ? clamp(stored) : DEFAULT;
  });

  useEffect(() => {
    document.documentElement.style.fontSize = `${size}px`;
    localStorage.setItem(STORAGE_KEY, String(size));
  }, [size]);

  const increase = () => {
    setSize((s) => {
      const idx = SIZES.indexOf(s);
      return idx < SIZES.length - 1 ? SIZES[idx + 1] : s;
    });
  };

  const decrease = () => {
    setSize((s) => {
      const idx = SIZES.indexOf(s);
      return idx > 0 ? SIZES[idx - 1] : s;
    });
  };

  const canIncrease = SIZES.indexOf(size) < SIZES.length - 1;
  const canDecrease = SIZES.indexOf(size) > 0;

  return { size, increase, decrease, canIncrease, canDecrease };
}
