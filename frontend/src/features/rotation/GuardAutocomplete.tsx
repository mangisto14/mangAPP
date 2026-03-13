import { useEffect, useRef, useState } from "react";
import type { Guard } from "../../types";

interface Props {
  value: string;
  onChange: (value: string) => void;
  guardNames: string[];
  guards?: Guard[];      // full guard objects for role filtering
  roleFilter?: string;  // role name to prioritize/warn against
  placeholder?: string;
  className?: string;
}

/**
 * Text input that shows autocomplete suggestions from the guard list.
 * Supports comma-separated names — suggestions appear for the last token.
 * When roleFilter is provided, matching guards are shown first and
 * mismatched names show a soft warning.
 */
export default function GuardAutocomplete({ value, onChange, guardNames, guards, roleFilter, placeholder, className }: Props) {
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

  // Build a role lookup map
  const guardRoleMap = new Map<string, string | null>(
    (guards ?? []).map((g) => [g.name, g.role])
  );

  // Extract tokens from the comma-separated string
  const tokens = value.split(",").map((s) => s.trim());
  const lastToken = tokens[tokens.length - 1] ?? "";
  const existingNames = new Set(tokens.slice(0, -1).map((t) => t.trim()).filter(Boolean));

  // Filter candidates matching last token, exclude already-used
  const candidates = lastToken.length > 0
    ? guardNames.filter((n) => n.includes(lastToken) && !existingNames.has(n))
    : [];

  // Sort: matching role first
  let suggestions: string[];
  if (roleFilter && guards) {
    const matching = candidates.filter((n) => guardRoleMap.get(n) === roleFilter);
    const others = candidates.filter((n) => guardRoleMap.get(n) !== roleFilter);
    suggestions = [...matching, ...others];
  } else {
    suggestions = candidates;
  }

  // Detect mismatched names in the current value
  const mismatchedNames: string[] = [];
  if (roleFilter && guards) {
    for (const token of tokens) {
      const name = token.trim();
      if (!name) continue;
      const guardRole = guardRoleMap.get(name);
      if (guardRole !== undefined && guardRole !== roleFilter) {
        mismatchedNames.push(name);
      }
    }
  }

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

  // Find the index where "others" start in suggestions (for separator)
  const matchingCount = roleFilter && guards
    ? candidates.filter((n) => guardRoleMap.get(n) === roleFilter).length
    : suggestions.length;

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
      {/* Mismatch warning */}
      {mismatchedNames.length > 0 && (
        <div className="mt-1 flex flex-wrap gap-1">
          {mismatchedNames.map((name) => (
            <span
              key={name}
              className="text-[10px] bg-warning/10 text-warning border border-warning/30 px-1.5 py-0.5 rounded-full"
              title={`${name} משובץ כ-${guardRoleMap.get(name) || "ללא תפקיד"}, לא ${roleFilter}`}
            >
              ⚠ {name} ({guardRoleMap.get(name) || "ללא תפקיד"})
            </span>
          ))}
        </div>
      )}
      {open && suggestions.length > 0 && (
        <ul className="absolute z-50 top-full mt-1 inset-x-0 bg-bg-card border border-bg-border rounded-xl
                       shadow-lg max-h-40 overflow-y-auto">
          {suggestions.slice(0, 10).map((name, i) => {
            const isMatch = roleFilter ? guardRoleMap.get(name) === roleFilter : true;
            const isSeparator = roleFilter && i === matchingCount && matchingCount > 0 && i < suggestions.length;
            return (
              <div key={name}>
                {isSeparator && (
                  <div className="px-3 py-1 text-[10px] text-text-dim/50 border-t border-bg-border bg-bg-base">
                    שאר כוח האדם
                  </div>
                )}
                <li
                  onMouseDown={() => selectSuggestion(name)}
                  className={`px-3 py-2 text-sm cursor-pointer transition-colors flex items-center justify-between
                    ${i === focusIdx ? "bg-primary/15 text-primary" : "text-text hover:bg-bg-base"}
                    ${!isMatch ? "opacity-60" : ""}`}
                >
                  <span>{name}</span>
                  {roleFilter && guards && (
                    <span className={`text-[10px] px-1.5 py-0.5 rounded-full border ml-2 shrink-0
                      ${isMatch
                        ? "bg-success/10 text-success border-success/25"
                        : "bg-warning/10 text-warning border-warning/25"
                      }`}>
                      {guardRoleMap.get(name) || "ללא"}
                    </span>
                  )}
                </li>
              </div>
            );
          })}
        </ul>
      )}
    </div>
  );
}
