import { useEffect, useRef, useState } from "react";
import { UploadCloud, FileText, Check, X, Loader2 } from "lucide-react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { csvService, AUDIENCE_CSV_FIELDS, type CsvImportResult, type CsvPreview } from "@/services/csv.service";
import { toast } from "sonner";

interface CsvUploadDialogProps {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  onImported?: (result: CsvImportResult) => void;
}

type Step = "select" | "map" | "importing" | "done";

export function CsvUploadDialog({ open, onOpenChange, onImported }: CsvUploadDialogProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<CsvPreview | null>(null);
  const [mapping, setMapping] = useState<Record<string, string>>({});
  const [step, setStep] = useState<Step>("select");
  const [progress, setProgress] = useState(0);
  const [result, setResult] = useState<CsvImportResult | null>(null);

  useEffect(() => {
    if (!open) {
      setFile(null); setPreview(null); setMapping({}); setStep("select"); setProgress(0); setResult(null);
    }
  }, [open]);

  async function handleFile(f: File) {
    setFile(f);
    try {
      const p = await csvService.previewFile(f);
      setPreview(p);
      const m: Record<string, string> = {};
      AUDIENCE_CSV_FIELDS.forEach((field) => {
        const match = p.headers.find((h) => h.toLowerCase() === field.toLowerCase());
        if (match) m[field] = match;
      });
      setMapping(m);
      setStep("map");
    } catch {
      toast.error("Could not read this CSV file.");
    }
  }

  async function runImport() {
    if (!file) return;
    setStep("importing");
    setProgress(0);
    const res = await csvService.importFile(file, mapping, { skipDuplicates: true }, setProgress);
    setResult(res);
    setStep("done");
    onImported?.(res);
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Import audience from CSV</DialogTitle>
          <DialogDescription>
            Upload a CSV file, map the columns, then review the import summary.
          </DialogDescription>
        </DialogHeader>

        {step === "select" && (
          <div
            onClick={() => inputRef.current?.click()}
            onDragOver={(e) => e.preventDefault()}
            onDrop={(e) => { e.preventDefault(); const f = e.dataTransfer.files?.[0]; if (f) handleFile(f); }}
            className="cursor-pointer rounded-xl border-2 border-dashed border-border p-10 text-center hover:border-primary"
          >
            <UploadCloud className="mx-auto h-10 w-10 text-muted-foreground" />
            <p className="mt-3 text-sm font-medium">Drop CSV here, or click to browse</p>
            <p className="mt-1 text-xs text-muted-foreground">Max 10MB · UTF-8 encoded</p>
            <input
              ref={inputRef}
              type="file"
              accept=".csv,text/csv"
              className="hidden"
              onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0]!)}
            />
            <Button
              type="button"
              variant="link"
              className="mt-3 text-xs"
              onClick={(e) => { e.stopPropagation(); csvService.downloadTemplate(); }}
            >
              Download template
            </Button>
          </div>
        )}

        {step === "map" && preview && (
          <div className="space-y-4">
            <div className="flex items-center gap-2 rounded-lg bg-muted px-3 py-2 text-sm">
              <FileText className="h-4 w-4" />
              <span className="flex-1 truncate">{file?.name}</span>
              <span className="text-muted-foreground">{preview.totalRows} rows</span>
            </div>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 max-h-72 overflow-y-auto pr-2">
              {AUDIENCE_CSV_FIELDS.map((f) => (
                <div key={f} className="space-y-1">
                  <Label className="text-xs">{f}</Label>
                  <Select
                    value={mapping[f] ?? "__none__"}
                    onValueChange={(v) =>
                      setMapping((prev) => {
                        const next = { ...prev };
                        if (v === "__none__") delete next[f];
                        else next[f] = v;
                        return next;
                      })
                    }
                  >
                    <SelectTrigger className="h-9"><SelectValue placeholder="— skip —" /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="__none__">— skip —</SelectItem>
                      {preview.headers.map((h) => (
                        <SelectItem key={h} value={h}>{h}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              ))}
            </div>
          </div>
        )}

        {step === "importing" && (
          <div className="py-8 text-center">
            <Loader2 className="mx-auto h-8 w-8 animate-spin text-primary" />
            <p className="mt-3 text-sm">Importing contacts…</p>
            <Progress value={progress} className="mt-4" />
            <p className="mt-2 text-xs text-muted-foreground">{progress}% complete</p>
          </div>
        )}

        {step === "done" && result && (
          <div className="space-y-3">
            <div className="grid grid-cols-3 gap-3 text-center">
              <div className="rounded-lg bg-emerald-500/10 p-3">
                <Check className="mx-auto h-4 w-4 text-emerald-600" />
                <p className="mt-1 text-lg font-semibold text-emerald-700 dark:text-emerald-400">{result.created}</p>
                <p className="text-xs text-muted-foreground">Created</p>
              </div>
              <div className="rounded-lg bg-amber-500/10 p-3">
                <p className="text-lg font-semibold text-amber-700 dark:text-amber-400">{result.duplicates}</p>
                <p className="text-xs text-muted-foreground">Duplicates</p>
              </div>
              <div className="rounded-lg bg-rose-500/10 p-3">
                <X className="mx-auto h-4 w-4 text-rose-600" />
                <p className="mt-1 text-lg font-semibold text-rose-700 dark:text-rose-400">{result.errors.length}</p>
                <p className="text-xs text-muted-foreground">Errors</p>
              </div>
            </div>
            {result.errors.length > 0 && (
              <div className="max-h-40 overflow-y-auto rounded-lg border p-2 text-xs">
                {result.errors.slice(0, 20).map((e, i) => (
                  <div key={i} className="border-b py-1 last:border-0">
                    Row {e.row}{e.field ? ` · ${e.field}` : ""}: {e.message}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        <DialogFooter>
          {step === "map" && (
            <>
              <Button variant="ghost" onClick={() => setStep("select")}>Back</Button>
              <Button onClick={runImport}>Start import</Button>
            </>
          )}
          {step === "done" && (<Button onClick={() => onOpenChange(false)}>Close</Button>)}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
