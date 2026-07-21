import type { TemplateCategory } from "@/types/template";

export const TEMPLATE_CATEGORIES: {
  key: TemplateCategory;
  label: string;
  description: string;
}[] = [
  { key: "email", label: "Email", description: "Long-form transactional or marketing email." },
  { key: "sms", label: "SMS", description: "160-character text message." },
  { key: "whatsapp", label: "WhatsApp", description: "WhatsApp business message." },
  { key: "push", label: "Push", description: "Mobile / web push notification." },
  { key: "banner", label: "Website Banner", description: "On-site banner or notice." },
  { key: "social", label: "Social Media", description: "Post copy for social channels." },
  { key: "emergency_alert", label: "Emergency Alert", description: "Time-critical broadcast." },
  { key: "government_notice", label: "Government Notice", description: "Formal notice or advisory." },
  { key: "healthcare", label: "Healthcare", description: "Public health messaging." },
  { key: "education", label: "Education", description: "School or university updates." },
  { key: "internal", label: "Internal", description: "Internal staff communication." },
  { key: "custom", label: "Custom", description: "General-purpose template." },
];

export const TEMPLATE_CATEGORY_META: Record<TemplateCategory, (typeof TEMPLATE_CATEGORIES)[number]> =
  Object.fromEntries(TEMPLATE_CATEGORIES.map((c) => [c.key, c])) as Record<
    TemplateCategory,
    (typeof TEMPLATE_CATEGORIES)[number]
  >;

export const TEMPLATE_CHANNEL_LIMITS: Partial<Record<TemplateCategory, number>> = {
  sms: 160,
  push: 240,
  whatsapp: 1024,
  banner: 320,
  social: 280,
};

export const BUILTIN_VARIABLES = [
  { key: "first_name", label: "First name", example: "Aarav" },
  { key: "last_name", label: "Last name", example: "Sharma" },
  { key: "organization", label: "Organization", example: "Ministry of Health" },
  { key: "campaign_name", label: "Campaign name", example: "Monsoon Health Advisory" },
  { key: "language", label: "Language", example: "en" },
  { key: "city", label: "City", example: "Pune" },
  { key: "district", label: "District", example: "Pune" },
  { key: "state", label: "State", example: "Maharashtra" },
  { key: "date", label: "Date", example: "12 Jul 2026" },
  { key: "time", label: "Time", example: "10:30 AM" },
];

export function extractVariables(body: string): string[] {
  const out = new Set<string>();
  const re = /\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}/g;
  let m: RegExpExecArray | null;
  while ((m = re.exec(body)) !== null) out.add(m[1]!);
  return [...out];
}

export function interpolate(body: string, values: Record<string, string>): string {
  return body.replace(/\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}/g, (_, k) => values[k] ?? `{{${k}}}`);
}
