import { useEffect, useMemo, useRef, useState } from "react";
import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { ArrowLeft, Monitor, Smartphone } from "lucide-react";
import { SectionHeader } from "@/components/common/section-header";
import { SkeletonBlock } from "@/components/common/skeleton-block";
import { ErrorState } from "@/components/common/error-state";
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
import type { TemplateCategory, TemplateInput } from "@/types/template";
import { TEMPLATE_CATEGORIES, TEMPLATE_CHANNEL_LIMITS, extractVariables, interpolate, BUILTIN_VARIABLES } from "@/constants/template";
import { LANGUAGES } from "@/constants/india";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/_authenticated/templates/$id/edit")({
  head: () => ({
    meta: [
      { title: "Edit template — Multilingua" },
      { name: "robots", content: "noindex" },
    ],
  }),
  component: EditTemplatePage,
});

function EditTemplatePage() {
  const { id } = Route.useParams();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ["template", id], queryFn: () => templateService.get(id) });
  const [state, setState] = useState<TemplateInput | null>(null);
  const [saving, setSaving] = useState(false);
  const [preview, setPreview] = useState<"desktop" | "mobile">("desktop");
  const bodyRef = useRef<HTMLTextAreaElement | null>(null);

  useEffect(() => {
    if (q.data && !state) {
      setState({
        name: q.data.name,
        category: q.data.category,
        language: q.data.language,
        status: q.data.status,
        subject: q.data.subject,
        body: q.data.body,
        variables: q.data.variables,
      });
    }
  }, [q.data, state]);

  const detected = useMemo(() => extractVariables(state?.body ?? ""), [state?.body]);
  const limit = state ? TEMPLATE_CHANNEL_LIMITS[state.category] : undefined;
  const overLimit = state ? (limit != null && state.body.length > limit) : false;
  const previewValues = useMemo(() => {
    const map: Record<string, string> = {};
    BUILTIN_VARIABLES.forEach((v) => { map[v.key] = v.example ?? v.key; });
    detected.forEach((k) => { if (!map[k]) map[k] = `[${k}]`; });
    return map;
  }, [detected]);

  if (q.isLoading || !state) return <SkeletonBlock rows={6} />;
  if (q.isError) return <ErrorState onRetry={() => q.refetch()} />;

  function insertVariable(key: string) {
    const el = bodyRef.current;
    if (!el || !state) return;
    const before = state.body.slice(0, el.selectionStart);
    const after = state.body.slice(el.selectionEnd);
    const insertion = `{{${key}}}`;
    const next = before + insertion + after;
    setState((s) => (s ? { ...s, body: next } : s));
    requestAnimationFrame(() => {
      el.focus();
      el.setSelectionRange(before.length + insertion.length, before.length + insertion.length);
    });
  }

  async function submit() {
    if (!state) return;
    setSaving(true);
    try {
      await templateService.update(id, state);
      qc.invalidateQueries({ queryKey: ["templates"] });
      qc.invalidateQueries({ queryKey: ["template", id] });
      toast.success("Template updated");
      navigate({ to: "/templates/$id", params: { id } });
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="space-y-6">
      <SectionHeader
        title={`Edit — ${state.name}`}
        description="Any change to content creates a new version."
        actions={
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={() => navigate({ to: "/templates/$id", params: { id } })} className="gap-1.5">
              <ArrowLeft className="h-4 w-4" /> Cancel
            </Button>
            <Button size="sm" onClick={submit} disabled={saving}>
              {saving ? "Saving…" : "Save changes"}
            </Button>
          </div>
        }
      />

      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2 shadow-card">
          <CardHeader className="pb-2"><CardTitle className="text-base">Details</CardTitle></CardHeader>
          <CardContent className="grid gap-3 md:grid-cols-2">
            <Field label="Name" required>
              <Input value={state.name} onChange={(e) => setState((s) => (s ? { ...s, name: e.target.value } : s))} />
            </Field>
            <Field label="Category">
              <Select value={state.category} onValueChange={(v) => setState((s) => (s ? { ...s, category: v as TemplateCategory } : s))}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {TEMPLATE_CATEGORIES.map((c) => <SelectItem key={c.key} value={c.key}>{c.label}</SelectItem>)}
                </SelectContent>
              </Select>
            </Field>
            <Field label="Language">
              <Select value={state.language} onValueChange={(v) => setState((s) => (s ? { ...s, language: v } : s))}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {LANGUAGES.map((l) => <SelectItem key={l.code} value={l.code}>{l.label}</SelectItem>)}
                </SelectContent>
              </Select>
            </Field>
            <Field label="Status">
              <Select value={state.status ?? "draft"} onValueChange={(v) => setState((s) => (s ? { ...s, status: v as TemplateInput["status"] } : s))}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="draft">Draft</SelectItem>
                  <SelectItem value="published">Published</SelectItem>
                  <SelectItem value="archived">Archived</SelectItem>
                </SelectContent>
              </Select>
            </Field>
            <Field label="Subject" className="md:col-span-2">
              <Input value={state.subject ?? ""} onChange={(e) => setState((s) => (s ? { ...s, subject: e.target.value } : s))} />
            </Field>
            <Field label="Content" required className="md:col-span-2">
              <RichTextToolbar targetRef={bodyRef} />
              <Textarea
                ref={bodyRef}
                value={state.body}
                onChange={(e) => setState((s) => (s ? { ...s, body: e.target.value } : s))}
                className="min-h-[220px] rounded-t-none font-mono text-sm"
              />
              <div className="mt-1 flex items-center justify-between text-xs text-muted-foreground">
                <span>{detected.length} variable(s) detected</span>
                <span className={cn(overLimit && "text-destructive font-medium")}>
                  {state.body.length}{limit != null ? ` / ${limit}` : ""} characters
                </span>
              </div>
            </Field>
            <Field label="Version note" className="md:col-span-2">
              <Input
                value={state.versionNote ?? ""}
                onChange={(e) => setState((s) => (s ? { ...s, versionNote: e.target.value } : s))}
                placeholder="Describe what changed in this revision"
              />
            </Field>
          </CardContent>
        </Card>

        <div className="space-y-4">
          <VariableEditor
            detected={detected}
            extras={state.variables ?? []}
            onInsert={insertVariable}
            onAddExtra={(v) => setState((s) => (s ? { ...s, variables: [...(s.variables ?? []), v] } : s))}
            onRemoveExtra={(k) => setState((s) => (s ? { ...s, variables: (s.variables ?? []).filter((v) => v.key !== k) } : s))}
          />
          <div className="rounded-xl border bg-card shadow-card">
            <Tabs value={preview} onValueChange={(v) => setPreview(v as "desktop" | "mobile")}>
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
                {state.subject && <p className="mb-2 font-semibold">{state.subject}</p>}
                <p className="whitespace-pre-line text-sm">{interpolate(state.body, previewValues)}</p>
              </TabsContent>
              <TabsContent value="mobile" className="p-4">
                <div className="mx-auto w-64 rounded-2xl border bg-background p-3 shadow-inner">
                  {state.subject && <p className="mb-1 text-sm font-semibold">{state.subject}</p>}
                  <p className="whitespace-pre-line text-xs">{interpolate(state.body, previewValues)}</p>
                </div>
              </TabsContent>
            </Tabs>
          </div>
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
