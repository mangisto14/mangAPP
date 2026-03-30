/**
 * Cross-browser clipboard copy.
 * Uses modern Clipboard API where available, falls back to
 * execCommand('copy') for Safari < 13.1 and other legacy browsers.
 */
export async function copyText(text: string): Promise<boolean> {
  // Modern API (Chrome, Firefox, Safari 13.1+)
  if (navigator.clipboard?.writeText) {
    try {
      await navigator.clipboard.writeText(text);
      return true;
    } catch {
      // Permissions denied or not in secure context — fall through
    }
  }

  // Legacy fallback (Safari < 13.1, iOS WebView, HTTP)
  try {
    const el = document.createElement("textarea");
    el.value = text;
    // Keep it off-screen but in the DOM so iOS can select it
    el.setAttribute("readonly", "");
    el.style.cssText = "position:fixed;top:0;left:0;opacity:0;pointer-events:none;";
    document.body.appendChild(el);
    el.focus();
    el.select();
    // iOS needs setSelectionRange
    el.setSelectionRange(0, text.length);
    const ok = document.execCommand("copy");
    document.body.removeChild(el);
    return ok;
  } catch {
    return false;
  }
}
