import React, { createContext, useContext, useMemo, useState } from "react";
import { translations } from "../i18n/translations";
import type { Language } from "../i18n/translations";

export type { Language };

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
  const [language, setLanguage] = useState<Language>("English");
  const dict = useMemo(() => translations[language], [language]);
  const t = (key: string): string => dict[key] ?? key;
  return (
    <LanguageContext.Provider value={{ language, setLanguage, t }}>
      {children}
    </LanguageContext.Provider>
  );
};
