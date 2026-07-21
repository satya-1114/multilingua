import { useEffect, useMemo, useRef, useState } from "react";
import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { ArrowLeft, Monitor, Smartphone } from "lucide-react";
import { SectionHeader } from "@/components/common/section-header";
import { RichTextToolbar } from "@/components/common/rich-text-toolbar";
import { VariableEditor } from "@/components/common/variable-editor";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { templateService } from "@/services/template.service";
import type { TemplateCategory, TemplateInput, TemplateVariable } from "@/types/template";
import { TEMPLATE_CATEGORIES, TEMPLATE_CHANNEL_LIMITS, extractVariables, interpolate, BUILTIN_VARIABLES } from "@/constants/template";
import { LANGUAGES } from "@/constants/india";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/_authenticated/templates/new")({
  head: () => ({
    meta: [
      { title: "New template — Multilingua" },
      { name: "robots", content: "noindex" },
    ],
  }),
  component: NewTemplatePage,
});

const DEFAULT_INPUT: TemplateInput = {
  name: "",
  category: "sms",
  language: "en",
  status: "draft",
  subject: "",
  body: "",
  variables: [],
};

function NewTemplatePage() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [state, setState] = useState<TemplateInput>(DEFAULT_INPUT);
  const [saving, setSaving] = useState(false);
  const [preview, setPreview] = useState<"desktop" | "mobile">("desktop");
  const bodyRef = useRef<HTMLTextAreaElement | null>(null);
  const draftKey = "template-draft";

  useEffect(() => {
    try {
      const raw = typeof window !== "undefined" ? sessionStorage.getItem(draftKey) : null;
      if (raw) setState(JSON.parse(raw));
    } catch { /* ignore */ }
  }, []);

  useEffect(() => {
    const t = setTimeout(() => {
      try { sessionStorage.setItem(draftKey, JSON.stringify(state)); } catch { /* ignore */ }
    }, 500);
    return () => clearTimeout(t);
  }, [state]);

  const detected = useMemo(() => extractVariables(state.body), [state.body]);
  const limit = TEMPLATE_CHANNEL_LIMITS[state.category];
  const overLimit = limit != null && state.body.length > limit;

  const previewValues = useMemo(() => {
    const map: Record<string, string> = {};
    BUILTIN_VARIABLES.forEach((v) => { map[v.key] = v.example ?? v.key; });
    detected.forEach((k) => { if (!map[k]) map[k] = `[${k}]`; });
    return map;
  }, [detected]);

  function insertVariable(key: string) {
    const el = bodyRef.current;
    if (!el) return;
    const before = state.body.slice(0, el.selectionStart);
    const after = state.body.slice(el.selectionEnd);
    const insertion = `{{${key}}}`;
    const next = before + insertion + after;
    setState((s) => ({ ...s, body: next }));
    requestAnimationFrame(() => {
      el.focus();
      el.setSelectionRange(before.length + insertion.length, before.length + insertion.length);
    });
  }

  async function submit() {
    if (!state.name.trim() || !state.body.trim()) {
      toast.error("Name and content are required");
      return;
    }
    setSaving(true);
    try {
      const created = await templateService.create(state);
      sessionStorage.removeItem(draftKey);
      qc.invalidateQueries({ queryKey: ["templates"] });
      toast.success("Template created");
      navigate({ to: "/templates/$id", params: { id: created.id } });
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="space-y-6">
      <SectionHeader
        title="New template"
        description="Draft a reusable multilingual communication template with variables and live preview."
        actions={
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={() => navigate({ to: "/templates" })} className="gap-1.5">
              <ArrowLeft className="h-4 w-4" /> Cancel
            </Button>
            <Button size="sm" onClick={submit} disabled={saving}>
              {saving ? "Saving…" : "Save template"}
            </Button>
          </div>
        }
      />

      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2 shadow-card">
          <CardHeader className="pb-2"><CardTitle className="text-base">Details</CardTitle></CardHeader>
          <CardContent className="grid gap-3 md:grid-cols-2">
            <Field label="Name" required>
              <Input value={state.name} onChange={(e) => setState((s) => ({ ...s, name: e.target.value }))} placeholder="Vaccination Reminder — SMS" />
            </Field>
            <Field label="Category">
              <Select value={state.category} onValueChange={(v) => setState((s) => ({ ...s, category: v as TemplateCategory }))}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {TEMPLATE_CATEGORIES.map((c) => <SelectItem key={c.key} value={c.key}>{c.label}</SelectItem>)}
                </SelectContent>
              </Select>
            </Field>
            <Field label="Language">
              <Select value={state.language} onValueChange={(v) => setState((s) => ({ ...s, language: v }))}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {LANGUAGES.map((l) => <SelectItem key={l.code} value={l.code}>{l.label}</SelectItem>)}
                </SelectContent>
              </Select>
            </Field>
            <Field label="Status">
              <Select value={state.status} onValueChange={(v) => setState((s) => ({ ...s, status: v as TemplateInput["status"] }))}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="draft">Draft</SelectItem>
                  <SelectItem value="published">Published</SelectItem>
                </SelectContent>
              </Select>
            </Field>
            <Field label="Subject" className="md:col-span-2">
              <Input value={state.subject ?? ""} onChange={(e) => setState((s) => ({ ...s, subject: e.target.value }))} placeholder="For email templates" />
            </Field>
            <Field label="Content" className="md:col-span-2" required>
              <RichTextToolbar targetRef={bodyRef} />
              <Textarea
                ref={bodyRef}
                value={state.body}
                onChange={(e) => setState((s) => ({ ...s, body: e.target.value }))}
                placeholder={"Hello {{first_name}}, ..."}
                className="min-h-[220px] rounded-t-none font-mono text-sm"
              />
              <div className="mt-1 flex items-center justify-between text-xs text-muted-foreground">
                <span>{detected.length} variable(s) detected</span>
                <span className={cn(overLimit && "text-destructive font-medium")}>
                  {state.body.length}{limit != null ? ` / ${limit}` : ""} characters
                </span>
              </div>
            </Field>
          </CardContent>
        </Card>

        <div className="space-y-4">
          <VariableEditor
            detected={detected}
            extras={state.variables ?? []}
            onInsert={insertVariable}
            onAddExtra={(v) => setState((s) => ({ ...s, variables: [...(s.variables ?? []), v] }))}
            onRemoveExtra={(k) => setState((s) => ({ ...s, variables: (s.variables ?? []).filter((v) => v.key !== k) }))}
          />
          <PreviewPanel
            body={state.body}
            subject={state.subject}
            values={previewValues}
            preview={preview}
            onChange={setPreview}
          />
        </div>
      </div>
    </div>
  );
}

function Field({ label, required, className, children }: { label: string; required?: boolean; className?: string; children: React.ReactNode }) {
  return (
    <div className={cn("space-y-1.5", className)}>
      <Label className="text-xs uppercase tracking-wide text-muted-foreground">
        {label}{required && <span className="ml-0.5 text-destructive">*</span>}
      </Label>
      {children}
    </div>
  );
}

function PreviewPanel({
  body, subject, values, preview, onChange,
}: {
  body: string; subject?: string; values: Record<string, string>;
  preview: "desktop" | "mobile"; onChange: (v: "desktop" | "mobile") => void;
}) {
  const rendered = interpolate(body, values);
  return (
    <div className="rounded-xl border bg-card shadow-card">
      <Tabs value={preview} onValueChange={(v) => onChange(v as "desktop" | "mobile")}>
        <div className="flex items-center justify-between border-b px-3 py-2">
          <p className="text-sm font-semibold">Live preview</p>
          <TabsList className="h-8">
            <TabsTrigger value="desktop" className="h-6 gap-1 px-2 text-xs">
              <Monitor className="h-3.5 w-3.5" /> Desktop
            </TabsTrigger>
            <TabsTrigger value="mobile" className="h-6 gap-1 px-2 text-xs">
              <Smartphone className="h-3.5 w-3.5" /> Mobile
            </TabsTrigger>
          </TabsList>
        </div>
        <TabsContent value="desktop" className="p-4">
          {subject && <p className="mb-2 font-semibold">{subject}</p>}
          <p className="whitespace-pre-line text-sm">{rendered || <span className="text-muted-foreground">Nothing to preview yet.</span>}</p>
        </TabsContent>
        <TabsContent value="mobile" className="p-4">
          <div className="mx-auto w-64 rounded-2xl border bg-background p-3 shadow-inner">
            {subject && <p className="mb-1 text-sm font-semibold">{subject}</p>}
            <p className="whitespace-pre-line text-xs">{rendered || <span className="text-muted-foreground">Nothing to preview yet.</span>}</p>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
