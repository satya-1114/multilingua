import { useMemo, useState } from "react";
import { Download, Filter as FilterIcon, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { LANGUAGES } from "@/constants/india";
import { PermissionGuard } from "@/components/common/permission-guard";
import { PERMISSIONS } from "@/constants/rbac";
import type { AnalyticsFilters, ExportFormat, ReportDataset } from "@/types/analytics";

interface AnalyticsFilterBarProps {
  value: AnalyticsFilters;
  onChange: (next: AnalyticsFilters) => void;
  /** When provided, renders export buttons wired to this dataset. */
  exportDataset?: ReportDataset;
  onExport?: (format: ExportFormat) => Promise<void> | void;
}

const EXPORT_FORMATS: { label: string; value: ExportFormat }[] = [
  { label: "CSV", value: "csv" },
  { label: "Excel (.xlsx)", value: "xlsx" },
  { label: "PDF", value: "pdf" },
];

/**
 * Reusable analytics filter bar. Renders date range + language multiselect and
 * (optionally) export controls. Kept intentionally simple — heavier filter
 * surfaces (campaigns / disasters / volunteers / orgs) are dataset-specific
 * and layered on top of this by their host pages.
 */
export function AnalyticsFilterBar({ value, onChange, exportDataset, onExport }: AnalyticsFilterBarProps) {
  const [busy, setBusy] = useState<ExportFormat | null>(null);

  const langChips = useMemo(
    () =>
      (value.languages ?? []).map((code) => ({
        code,
        label: LANGUAGES.find((l) => l.code === code)?.label ?? code,
      })),
    [value.languages],
  );

  const toggleLanguage = (code: string) => {
    const set = new Set(value.languages ?? []);
    if (set.has(code)) set.delete(code);
    else set.add(code);
    onChange({ ...value, languages: Array.from(set) });
  };

  const reset = () => onChange({});

  const runExport = async (format: ExportFormat) => {
    if (!onExport) return;
    setBusy(format);
    try {
      await onExport(format);
    } finally {
      setBusy(null);
    }
  };

  return (
    <Card className="shadow-card">
      <CardContent className="flex flex-col gap-3 p-4 md:flex-row md:flex-wrap md:items-end">
        <div className="grid gap-1">
          <Label htmlFor="af-from" className="text-xs text-muted-foreground">From</Label>
          <Input
            id="af-from"
            type="date"
            className="h-9 w-40"
            value={value.from ?? ""}
            onChange={(e) => onChange({ ...value, from: e.target.value || undefined })}
          />
        </div>
        <div className="grid gap-1">
          <Label htmlFor="af-to" className="text-xs text-muted-foreground">To</Label>
          <Input
            id="af-to"
            type="date"
            className="h-9 w-40"
            value={value.to ?? ""}
            onChange={(e) => onChange({ ...value, to: e.target.value || undefined })}
          />
        </div>

        <div className="grid gap-1">
          <Label className="text-xs text-muted-foreground">Languages</Label>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" size="sm" className="h-9">
                <FilterIcon className="mr-1.5 h-3.5 w-3.5" />
                {langChips.length ? `${langChips.length} selected` : "All languages"}
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="start" className="max-h-72 overflow-y-auto">
              {LANGUAGES.map((l) => {
                const active = (value.languages ?? []).includes(l.code);
                return (
                  <DropdownMenuItem
                    key={l.code}
                    onSelect={(e) => {
                      e.preventDefault();
                      toggleLanguage(l.code);
                    }}
                    className={active ? "font-medium" : ""}
                  >
                    <span className="mr-2 inline-block w-3">{active ? "✓" : ""}</span>
                    {l.label}
                  </DropdownMenuItem>
                );
              })}
            </DropdownMenuContent>
          </DropdownMenu>
        </div>

        {langChips.length > 0 && (
          <div className="flex flex-wrap items-center gap-1">
            {langChips.map((c) => (
              <Badge key={c.code} variant="secondary" className="gap-1">
                {c.label}
                <button
                  type="button"
                  onClick={() => toggleLanguage(c.code)}
                  className="ml-0.5 rounded-full p-0.5 hover:bg-muted"
                  aria-label={`Remove ${c.label}`}
                >
                  <X className="h-3 w-3" />
                </button>
              </Badge>
            ))}
          </div>
        )}

        <div className="ml-auto flex flex-wrap items-center gap-2">
          <Button variant="ghost" size="sm" onClick={reset} className="h-9">
            Reset
          </Button>
          {exportDataset && onExport && (
            <PermissionGuard anyOf={[PERMISSIONS.ANALYTICS_EXPORT]}>
              {EXPORT_FORMATS.map((f) => (
                <Button
                  key={f.value}
                  size="sm"
                  variant="outline"
                  className="h-9"
                  disabled={busy !== null}
                  onClick={() => runExport(f.value)}
                >
                  <Download className="mr-1 h-3.5 w-3.5" />
                  {busy === f.value ? "Exporting…" : f.label}
                </Button>
              ))}
            </PermissionGuard>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
