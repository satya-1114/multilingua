import { en } from "./en";

export const te: typeof en = {
  ...en,
  common: {
    ...en.common,
    save: "సేవ్",
    cancel: "రద్దు చేయి",
    delete: "తొలగించు",
    edit: "సవరించు",
    create: "సృష్టించు",
    search: "శోధించు",
    loading: "లోడ్ అవుతోంది…",
  },
  nav: {
    ...en.nav,
    dashboard: "డాష్‌బోర్డ్",
    campaigns: "క్యాంపెయిన్‌లు",
    audience: "ప్రేక్షకులు",
    settings: "సెట్టింగ్‌లు",
    translation: "అనువాదం",
    aiStudio: "AI స్టూడియో",
  },
};
