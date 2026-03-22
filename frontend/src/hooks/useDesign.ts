import { useEffect, useState } from "react";

export type DesignVariant = "classic" | "material";

export function useDesign() {
  const [design, setDesign] = useState<DesignVariant>(() => {
    return (localStorage.getItem("design") as DesignVariant) || "classic";
  });

  useEffect(() => {
    document.documentElement.setAttribute("data-design", design);
    localStorage.setItem("design", design);
  }, [design]);

  const setVariant = (v: DesignVariant) => setDesign(v);

  return { design, setVariant };
}
