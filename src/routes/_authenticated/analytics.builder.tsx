import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { reportService } from "@/services/report.service";
import type { ReportKind, ReportResult } from "@/types/analytics";

export const Route = createFileRoute("/_authenticated/analytics/builder")({
  component: ReportBuilderPage,
});

const kinds: { value: ReportKind; label: string }[] = [
  { value: "campaign", label: "Campaign performance" },
  { value: "audience", label: "Audience by geography" },
  { value: "organization", label: "Organization comparison" },
  { value: "delivery", label: "Delivery by channel" },
  { value: "template", label: "Template usage" },
  { value: "translation", label: "Translation usage" },
  { value: "ai", label: "AI usage" },
  { value: "audit", label: "Audit trail" },
  { value: "security", label: "Security events" },
  { value: "activity", label: "User activity" },
];

function ReportBuilderPage() {
  const qc = useQueryClient();
  const [name, setName] = useState("Untitled report");
  const [kind, setKind] = useState<ReportKind>("campaign");
  const [description, setDescription] = useState("");
  const [range, setRange] = useState("last_30d");
  const [preview, setPreview] = useState<ReportResult | null>(null);

  const run = useMutation({ mutationFn: (k: ReportKind) => reportService.run(k), onSuccess: (r) => setPreview(r) });
  const save = useMutation({
    mutationFn: () => reportService.create({ name, kind, description, filters: { range }, createdBy: "You" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["reports"] }),
  });

  return (
    <div className="grid gap-5 lg:grid-cols-[360px,1fr]">
      <Card>
        <CardHeader><CardTitle className="text-base">Report definition</CardTitle></CardHeader>
        <CardContent className="space-y-3">
          <div>
            <Label className="text-xs uppercase text-muted-foreground">Name</Label>
            <Input value={name} onChange={(e) => setName(e.target.value)} />
          </div>
          <div>
            <Label className="text-xs uppercase text-muted-foreground">Kind</Label>
            <Select value={kind} onValueChange={(v) => setKind(v as ReportKind)}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                {kinds.map((k) => <SelectItem key={k.value} value={k.value}>{k.label}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
          <div>
            <Label className="text-xs uppercase text-muted-foreground">Date range</Label>
            <Select value={range} onValueChange={setRange}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="last_7d">Last 7 days</SelectItem>
                <SelectItem value="last_30d">Last 30 days</SelectItem>
                <SelectItem value="last_90d">Last 90 days</SelectItem>
                <SelectItem value="ytd">Year to date</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div>
            <Label className="text-xs uppercase text-muted-foreground">Description</Label>
            <Textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={3} />
          </div>
          <div className="flex gap-2">
            <Button onClick={() => run.mutate(kind)} disabled={run.isPending}>Preview</Button>
            <Button variant="outline" onClick={() => save.mutate()} disabled={save.isPending}>Save report</Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle className="text-base">Preview</CardTitle></CardHeader>
        <CardContent>
          {!preview ? (
            <p className="text-sm text-muted-foreground">Run a preview to see rows.</p>
          ) : (
            <div className="overflow-auto rounded-lg border">
              <table className="w-full text-sm">
                <thead className="bg-muted/40 text-xs uppercase text-muted-foreground">
                  <tr>
                    {preview.columns.map((c) => <th key={c.key} className="px-3 py-2 text-left font-medium">{c.label}</th>)}
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {preview.rows.map((r) => (
                    <tr key={r.id}>
                      {preview.columns.map((c) => <td key={c.key} className="px-3 py-2">{String(r[c.key])}</td>)}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
