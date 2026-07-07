import React, { createContext, useContext, useEffect, useState } from "react";

export type Theme = "Light" | "Dark" | "System default";

const ThemeContext = createContext<{
  theme: Theme;
  setTheme: (t: Theme) => void;
}>({ theme: "System default", setTheme: () => {} });

export const useTheme = () => useContext(ThemeContext);

const THEME_STORAGE_KEY = "app.theme";

const loadTheme = (): Theme => {
  const stored = localStorage.getItem(THEME_STORAGE_KEY);
  return stored === "Light" || stored === "Dark" || stored === "System default" ? stored : "System default";
};

export const ThemeProvider = ({ children }: { children: React.ReactNode }) => {
  const [theme, setTheme] = useState<Theme>(loadTheme);

  useEffect(() => {
    localStorage.setItem(THEME_STORAGE_KEY, theme);
    const root = document.documentElement;
    const mq = window.matchMedia("(prefers-color-scheme: dark)");

    const apply = () => {
      const isDark = theme === "Dark" || (theme === "System default" && mq.matches);
      root.classList.toggle("dark", isDark);
    };

    apply();

    if (theme === "System default") {
      mq.addEventListener("change", apply);
      return () => mq.removeEventListener("change", apply);
    }
  }, [theme]);

  return (
    <ThemeContext.Provider value={{ theme, setTheme }}>
      {children}
    </ThemeContext.Provider>
  );
};
