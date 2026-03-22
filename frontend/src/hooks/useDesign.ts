import { useEffect, useState } from "react";

export type DesignPreset = "dark" | "light" | "modern";

const DARK_PRESETS: DesignPreset[] = ["dark", "modern"];

export function useDesign() {
  const [design, setDesign] = useState<DesignPreset>(() => {
    return (localStorage.getItem("design") as DesignPreset) || "dark";
  });

  useEffect(() => {
    const html = document.documentElement;
    html.setAttribute("data-design", design);
    // data-dark drives Tailwind's darkMode selector for existing dark: classes
    if (DARK_PRESETS.includes(design)) {
      html.setAttribute("data-dark", "");
    } else {
      html.removeAttribute("data-dark");
    }
    localStorage.setItem("design", design);
  }, [design]);

  return { design, setDesign };
}
