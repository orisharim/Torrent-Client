import React, { createContext, useContext, useEffect, useMemo, useState } from "react";
import { translations } from "../i18n/translations";
import type { Language } from "../i18n/translations";

export type { Language };

const LANGUAGE_STORAGE_KEY = "app.language";

const languageCodes: Record<Language, string> = {
  English: "en",
  Hebrew: "he",
  Spanish: "es",
  French: "fr",
  German: "de",
};

const loadLanguage = (): Language => {
  const stored = localStorage.getItem(LANGUAGE_STORAGE_KEY);
  return stored && stored in translations ? (stored as Language) : "English";
};

type LanguageContextType = {
  language: Language;
  setLanguage: (l: Language) => void;
  t: (key: string) => string;
};

const LanguageContext = createContext<LanguageContextType>({
  language: "English",
  setLanguage: () => {},
  t: (key) => key,
});

export const useLanguage = () => useContext(LanguageContext);

export const LanguageProvider = ({ children }: { children: React.ReactNode }) => {
  const [language, setLanguage] = useState<Language>(loadLanguage);
  const dict = useMemo(() => translations[language], [language]);
  const t = (key: string): string => dict[key] ?? key;

  useEffect(() => {
    localStorage.setItem(LANGUAGE_STORAGE_KEY, language);
    document.documentElement.dir = language === "Hebrew" ? "rtl" : "ltr";
    document.documentElement.lang = languageCodes[language];
  }, [language]);

  return (
    <LanguageContext.Provider value={{ language, setLanguage, t }}>
      {children}
    </LanguageContext.Provider>
  );
};
