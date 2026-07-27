import { useEffect, useState } from "react";

/** Tema claro/escuro com persistência em localStorage. */
export function useTheme() {
  const [theme, setTheme] = useState(() => localStorage.getItem("twin-mpfm-theme") || "light");

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem("twin-mpfm-theme", theme);
  }, [theme]);

  const toggle = () => setTheme((t) => (t === "light" ? "dark" : "light"));
  return { theme, toggle };
}
