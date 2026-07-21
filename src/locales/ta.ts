import { en } from "./en";

// Tamil UI strings mirror the English shape; keys without a translation
// fall back to English at runtime through i18next.
export const ta: typeof en = {
  ...en,
  common: {
    ...en.common,
    save: "சேமி",
    cancel: "ரத்து",
    delete: "நீக்கு",
    edit: "தொகு",
    create: "உருவாக்கு",
    search: "தேடு",
    loading: "ஏற்றுகிறது…",
  },
  nav: {
    ...en.nav,
    dashboard: "டாஷ்போர்டு",
    campaigns: "பிரச்சாரங்கள்",
    audience: "பார்வையாளர்கள்",
    settings: "அமைப்புகள்",
    translation: "மொழிபெயர்ப்பு",
    aiStudio: "AI ஸ்டுடியோ",
  },
};
