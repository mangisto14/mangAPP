import { useEffect, useRef, useState } from "react";

interface Props {
  value: string;
  onChange: (value: string) => void;
  guardNames: string[];
  placeholder?: string;
  className?: string;
}

/**
 * Text input that shows autocomplete suggestions from the guard list.
 * Supports comma-separated names — suggestions appear for the last token.
 */
export default function GuardAutocomplete({ value, onChange, guardNames, placeholder, className }: Props) {
  const [open, setOpen] = useState(false);
  const [focusIdx, setFocusIdx] = useState(-1);
  const wrapRef = useRef<HTMLDivElement>(null);

  // close on outside click
  useEffect(() => {
    function handler(e: MouseEvent) {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  // Extract tokens from the comma-separated string
  const tokens = value.split(",").map((s) => s.trim());
  const lastToken = tokens[tokens.length - 1] ?? "";
  const existingNames = new Set(tokens.slice(0, -1).map((t) => t.trim()).filter(Boolean));

  // Filter suggestions: match last token, exclude already-used names
  const suggestions = lastToken.length > 0
    ? guardNames.filter(
        (n) => n.includes(lastToken) && !existingNames.has(n)
      )
    : [];

  function selectSuggestion(name: string) {
    const before = tokens.slice(0, -1);
    before.push(name);
    onChange(before.join(", ") + ", ");
    setOpen(false);
    setFocusIdx(-1);
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (!open || suggestions.length === 0) return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setFocusIdx((prev) => Math.min(prev + 1, suggestions.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setFocusIdx((prev) => Math.max(prev - 1, 0));
    } else if (e.key === "Enter" && focusIdx >= 0) {
      e.preventDefault();
      selectSuggestion(suggestions[focusIdx]);
    }
  }

  return (
    <div ref={wrapRef} className="relative flex-1">
      <input
        value={value}
        onChange={(e) => { onChange(e.target.value); setOpen(true); setFocusIdx(-1); }}
        onFocus={() => setOpen(true)}
        onKeyDown={handleKeyDown}
        placeholder={placeholder ?? "שם1, שם2, שם3"}
        className={className ?? "input text-sm w-full"}
      />
      {open && suggestions.length > 0 && (
        <ul className="absolute z-50 top-full mt-1 inset-x-0 bg-bg-card border border-bg-border rounded-xl
                       shadow-lg max-h-40 overflow-y-auto">
          {suggestions.slice(0, 8).map((name, i) => (
            <li
              key={name}
              onMouseDown={() => selectSuggestion(name)}
              className={`px-3 py-2 text-sm cursor-pointer transition-colors
                ${i === focusIdx ? "bg-primary/15 text-primary" : "text-text hover:bg-bg-base"}`}
            >
              {name}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
