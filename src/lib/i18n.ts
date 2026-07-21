import i18n from "i18next";
import { initReactI18next } from "react-i18next";

import { en } from "@/locales/en";
import { hi } from "@/locales/hi";
import { ta } from "@/locales/ta";
import { te } from "@/locales/te";

export const SUPPORTED_UI_LANGUAGES = [
  { code: "en", label: "English" },
  { code: "hi", label: "हिन्दी" },
  { code: "ta", label: "தமிழ்" },
  { code: "te", label: "తెలుగు" },
];

const STORAGE_KEY = "app.ui.language";
const SUPPORTED_CODES = SUPPORTED_UI_LANGUAGES.map((l) => l.code);

/**
 * Initialize i18next synchronously with the "en" fallback ONLY. The
 * browser LanguageDetector plugin is NOT registered here because it reads
 * `navigator`/`localStorage` at init time; the SSR runtime provides a
 * stubbed `navigator` and no storage, and that discrepancy vs. the
 * client's real preference produces hydration mismatches in every
 * translated string.
 *
 * Language detection is performed exclusively on the client via
 * `syncClientLocale()`, called from a `useEffect` in `__root.tsx`.
 */
if (!i18n.isInitialized) {
  void i18n.use(initReactI18next).init({
    resources: {
      en: { translation: en },
      hi: { translation: hi },
      ta: { translation: ta },
      te: { translation: te },
    },
    lng: "en",
    fallbackLng: "en",
    supportedLngs: SUPPORTED_CODES,
    interpolation: { escapeValue: false },
    returnNull: false,
  });
}

function detectClientLocale(): string {
  if (typeof window === "undefined") return "en";
  try {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    if (stored && SUPPORTED_CODES.includes(stored)) return stored;
  } catch {
    /* storage disabled */
  }
  const nav = window.navigator?.language?.slice(0, 2);
  if (nav && SUPPORTED_CODES.includes(nav)) return nav;
  return "en";
}

/**
 * Applies the user's preferred UI language on the client after hydration
 * has committed. Safe no-op on the server.
 */
export function syncClientLocale(): void {
  if (typeof window === "undefined") return;
  const target = detectClientLocale();
  if (i18n.language !== target) void i18n.changeLanguage(target);
  if (typeof document !== "undefined") {
    document.documentElement.lang = target;
  }
}

export function setUiLanguage(code: string): void {
  void i18n.changeLanguage(code);
  if (typeof window !== "undefined") {
    try {
      window.localStorage.setItem(STORAGE_KEY, code);
    } catch {
      /* storage disabled */
    }
    if (typeof document !== "undefined") {
      document.documentElement.lang = code;
    }
  }
}

export default i18n;
