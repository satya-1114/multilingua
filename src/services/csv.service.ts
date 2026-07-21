import type { AudienceContact, AudienceInput } from "@/types/audience";
import { audienceService } from "@/services/audience.service";
import { auditService } from "@/services/audit.service";

/**
 * CSV import/export service. Uses the browser's File API and constructs
 * downloads client-side. Parsing is intentionally strict and validates every
 * row before it is handed to the audience service.
 */

const REQUIRED_HEADERS = [
  "firstName",
  "lastName",
  "email",
  "phone",
  "state",
  "district",
  "city",
  "preferredLanguage",
  "preferredChannel",
] as const;

export const AUDIENCE_CSV_FIELDS = [
  "firstName",
  "lastName",
  "email",
  "phone",
  "alternatePhone",
  "dateOfBirth",
  "gender",
  "occupation",
  "department",
  "state",
  "district",
  "city",
  "address",
  "pincode",
  "preferredLanguage",
  "preferredChannel",
  "status",
  "notes",
] as const;

export interface CsvPreview {
  headers: string[];
  rows: Record<string, string>[];
  totalRows: number;
}

export interface CsvImportError {
  row: number;
  field?: string;
  message: string;
}

export interface CsvImportResult {
  created: number;
  skipped: number;
  duplicates: number;
  errors: CsvImportError[];
}

function parseCsv(text: string): { headers: string[]; rows: string[][] } {
  const lines = text.replace(/\r/g, "").split("\n").filter((l) => l.trim().length > 0);
  if (lines.length === 0) return { headers: [], rows: [] };
  const parseLine = (line: string) => {
    const out: string[] = [];
    let cur = "";
    let inQuote = false;
    for (let i = 0; i < line.length; i++) {
      const ch = line[i];
      if (inQuote) {
        if (ch === '"' && line[i + 1] === '"') { cur += '"'; i++; }
        else if (ch === '"') inQuote = false;
        else cur += ch;
      } else {
        if (ch === '"') inQuote = true;
        else if (ch === ",") { out.push(cur); cur = ""; }
        else cur += ch;
      }
    }
    out.push(cur);
    return out.map((s) => s.trim());
  };
  const headers = parseLine(lines[0]!);
  const rows = lines.slice(1).map(parseLine);
  return { headers, rows };
}

function toCsv(rows: Record<string, unknown>[], headers: string[]): string {
  const escape = (v: unknown) => {
    const s = v == null ? "" : String(v);
    return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  const head = headers.join(",");
  const body = rows.map((r) => headers.map((h) => escape(r[h])).join(",")).join("\n");
  return `${head}\n${body}`;
}

function download(filename: string, content: string) {
  const blob = new Blob([content], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

export const csvService = {
  async previewFile(file: File, limit = 10): Promise<CsvPreview> {
    const text = await file.text();
    const { headers, rows } = parseCsv(text);
    const preview = rows.slice(0, limit).map((r) => {
      const obj: Record<string, string> = {};
      headers.forEach((h, i) => (obj[h] = r[i] ?? ""));
      return obj;
    });
    return { headers, rows: preview, totalRows: rows.length };
  },

  async importFile(
    file: File,
    mapping: Partial<Record<(typeof AUDIENCE_CSV_FIELDS)[number], string>>,
    options: { skipDuplicates?: boolean } = { skipDuplicates: true },
    onProgress?: (percent: number) => void,
  ): Promise<CsvImportResult> {
    const text = await file.text();
    const { headers, rows } = parseCsv(text);
    const errors: CsvImportError[] = [];
    let created = 0;
    let skipped = 0;
    let duplicates = 0;
    const existingEmails = new Set(
      (await audienceService.listAll()).map((c) => c.email.toLowerCase()),
    );

    for (let i = 0; i < rows.length; i++) {
      const row = rows[i]!;
      const record: Record<string, string> = {};
      headers.forEach((h, idx) => (record[h] = row[idx] ?? ""));
      const value = (key: (typeof AUDIENCE_CSV_FIELDS)[number]) => {
        const src = mapping[key] ?? key;
        return record[src]?.trim() ?? "";
      };
      const missing = REQUIRED_HEADERS.filter((f) => !value(f));
      if (missing.length) {
        errors.push({ row: i + 2, field: missing[0], message: `Missing required field: ${missing.join(", ")}` });
        skipped++;
        continue;
      }
      const email = value("email").toLowerCase();
      if (existingEmails.has(email)) {
        duplicates++;
        if (options.skipDuplicates) { skipped++; continue; }
      }
      const input: AudienceInput = {
        firstName: value("firstName"),
        lastName: value("lastName"),
        email: value("email"),
        phone: value("phone"),
        alternatePhone: value("alternatePhone") || undefined,
        dateOfBirth: value("dateOfBirth") || undefined,
        gender: (value("gender") || undefined) as AudienceInput["gender"],
        occupation: value("occupation") || undefined,
        department: value("department") || undefined,
        state: value("state"),
        district: value("district"),
        city: value("city"),
        address: value("address") || undefined,
        pincode: value("pincode") || undefined,
        preferredLanguage: value("preferredLanguage"),
        preferredChannel: (value("preferredChannel") || "sms") as AudienceInput["preferredChannel"],
        status: (value("status") || "active") as AudienceInput["status"],
        notes: value("notes") || undefined,
        consentGiven: true,
      };
      try {
        await audienceService.create(input);
        existingEmails.add(email);
        created++;
      } catch (err) {
        errors.push({ row: i + 2, message: err instanceof Error ? err.message : "Failed to create record" });
        skipped++;
      }
      if (onProgress) onProgress(Math.round(((i + 1) / rows.length) * 100));
    }

    auditService.record("imported", "audience", undefined, `${created} contacts`, { created, skipped, duplicates });
    return { created, skipped, duplicates, errors };
  },

  async exportAudience(contacts: AudienceContact[], filename = "audience-export.csv"): Promise<void> {
    const headers = [...AUDIENCE_CSV_FIELDS, "tags", "createdAt"];
    const rows = contacts.map((c) => ({
      firstName: c.firstName,
      lastName: c.lastName,
      email: c.email,
      phone: c.phone,
      alternatePhone: c.alternatePhone ?? "",
      dateOfBirth: c.dateOfBirth ?? "",
      gender: c.gender ?? "",
      occupation: c.occupation ?? "",
      department: c.department ?? "",
      state: c.state,
      district: c.district,
      city: c.city,
      address: c.address ?? "",
      pincode: c.pincode ?? "",
      preferredLanguage: c.preferredLanguage,
      preferredChannel: c.preferredChannel,
      status: c.status,
      notes: c.notes ?? "",
      tags: c.tags.map((t) => t.name).join("|"),
      createdAt: c.createdAt,
    }));
    download(filename, toCsv(rows, headers));
    auditService.record("exported", "audience", undefined, `${contacts.length} contacts`);
  },

  downloadTemplate(): void {
    const sample = [
      {
        firstName: "Ananya",
        lastName: "Iyer",
        email: "ananya.iyer@example.org",
        phone: "+91 9876543210",
        state: "Karnataka",
        district: "Bengaluru Urban",
        city: "Bengaluru",
        preferredLanguage: "kn",
        preferredChannel: "sms",
        status: "active",
      },
    ];
    download("audience-template.csv", toCsv(sample, [...AUDIENCE_CSV_FIELDS]));
  },
};
