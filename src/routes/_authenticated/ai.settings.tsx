import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { SectionHeader } from "@/components/common/section-header";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Slider } from "@/components/ui/slider";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { AI_TONES } from "@/constants/ai";
import { LANGUAGES } from "@/constants/india";
import { aiService } from "@/services/ai.service";
import type { WorkspaceAiSettingsDto } from "@/services/ai.service";

export const Route = createFileRoute("/_authenticated/ai/settings")({
  component: AiSettingsPage,
});

const SUPPORTED_PROVIDERS: { key: string; label: string; help: string }[] = [
  { key: "gemini", label: "Google Gemini (free)", help: "Free tier — default. Set GEMINI_API_KEY or enter a workspace key below." },
  { key: "ollama", label: "Ollama (local)", help: "Runs against a local Ollama daemon. No API key required." },
  { key: "huggingface", label: "Hugging Face (free)", help: "Free inference API. Requires a HF token." },
  { key: "watsonx", label: "IBM watsonx.ai", help: "Requires WATSONX_API_KEY + project ID." },
  { key: "openai", label: "OpenAI (paid)", help: "Optional. Never the default." },
];

function AiSettingsPage() {
  const qc = useQueryClient();
  const [form, setForm] = useState<WorkspaceAiSettingsDto | null>(null);
  const [apiKey, setApiKey] = useState<string | null>(null); // null = unchanged

  const query = useQuery({
    queryKey: ["ai-workspace-settings"],
    queryFn: () => aiService.getWorkspaceSettings(),
  });

  useEffect(() => {
    if (query.data && !form) setForm(query.data);
  }, [query.data, form]);

  const save = useMutation({
    mutationFn: () => {
      if (!form) throw new Error("form not ready");
      return aiService.saveWorkspaceSettings({
        provider: form.provider,
        model: form.model,
        apiKey,
        baseUrl: form.baseUrl,
        projectId: form.projectId,
        temperature: form.temperature,
        maxTokens: form.maxTokens,
        autoReview: form.autoReview,
        autoSave: form.autoSave,
        defaultTone: form.defaultTone,
        defaultLanguage: form.defaultLanguage,
      });
    },
    onSuccess: (updated) => {
      setForm(updated);
      setApiKey(null);
      qc.invalidateQueries({ queryKey: ["ai-workspace-settings"] });
      toast.success("AI settings saved");
    },
    onError: (e) => toast.error(`Save failed: ${(e as Error).message}`),
  });

  const test = useMutation({
    mutationFn: () => aiService.testWorkspaceSettings(),
    onSuccess: (r) =>
      r.ok
        ? toast.success(`Connection OK · ${r.provider}/${r.model}`)
        : toast.error(`Provider check failed: ${r.error ?? "unknown error"}`),
  });

  if (!form) {
    return (
      <div className="space-y-4">
        <SectionHeader title="AI settings" description="Loading workspace AI configuration…" />
      </div>
    );
  }

  const providerHelp = SUPPORTED_PROVIDERS.find((p) => p.key === form.provider)?.help ?? "";
  const creativity = Math.round(form.temperature * 50);

  return (
    <div className="space-y-5">
        <SectionHeader
          title="AI settings"
          description="Workspace AI provider, defaults and safety guardrails. API keys are encrypted at rest and never sent to the browser."
          actions={
            <div className="flex gap-2">
              <Button variant="outline" onClick={() => test.mutate()} disabled={test.isPending}>
                {test.isPending ? "Testing…" : "Test connection"}
              </Button>
              <Button onClick={() => save.mutate()} disabled={save.isPending}>
                {save.isPending ? "Saving…" : "Save"}
              </Button>
            </div>
          }
        />
        <div className="grid gap-4 lg:grid-cols-2">
          <Card>
            <CardContent className="space-y-4 p-5">
              <p className="text-sm font-semibold text-foreground">Provider</p>
              <div>
                <Label className="text-xs">Provider</Label>
                <Select value={form.provider} onValueChange={(v) => setForm({ ...form, provider: v })}>
                  <SelectTrigger className="mt-1"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {SUPPORTED_PROVIDERS.map((p) => (
                      <SelectItem key={p.key} value={p.key}>{p.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <p className="mt-1 text-[11px] text-muted-foreground">{providerHelp}</p>
              </div>
              <div>
                <Label className="text-xs">Model</Label>
                <Input
                  value={form.model}
                  onChange={(e) => setForm({ ...form, model: e.target.value })}
                  placeholder={
                    form.provider === "gemini"
                      ? "gemini-2.5-flash-lite"
                      : form.provider === "ollama"
                        ? "llama3.1"
                        : form.provider === "huggingface"
                          ? "mistralai/Mistral-7B-Instruct-v0.3"
                          : form.provider === "watsonx"
                            ? "ibm/granite-13b-chat-v2"
                            : "gpt-4o-mini"
                  }
                  className="mt-1"
                />
              </div>
              <div>
                <Label className="text-xs">API key {form.hasApiKey && "(stored — leave blank to keep)"}</Label>
                <Input
                  type="password"
                  value={apiKey ?? ""}
                  onChange={(e) => setApiKey(e.target.value)}
                  placeholder={form.apiKeyMasked || "sk-…"}
                  className="mt-1"
                />
                <p className="mt-1 text-[11px] text-muted-foreground">
                  Stored encrypted. Never returned to the browser or logs.
                </p>
              </div>
              {form.provider === "watsonx" && (
                <div>
                  <Label className="text-xs">watsonx project ID</Label>
                  <Input
                    value={form.projectId}
                    onChange={(e) => setForm({ ...form, projectId: e.target.value })}
                    className="mt-1"
                  />
                </div>
              )}
              {(form.provider === "ollama" || form.provider === "watsonx") && (
                <div>
                  <Label className="text-xs">Base URL</Label>
                  <Input
                    value={form.baseUrl}
                    onChange={(e) => setForm({ ...form, baseUrl: e.target.value })}
                    placeholder={form.provider === "ollama" ? "http://localhost:11434" : "https://us-south.ml.cloud.ibm.com"}
                    className="mt-1"
                  />
                </div>
              )}
              <div>
                <Label className="text-xs">Temperature · {form.temperature.toFixed(2)}</Label>
                <Slider
                  value={[Math.round(form.temperature * 100)]}
                  min={0}
                  max={200}
                  step={5}
                  onValueChange={(v) => setForm({ ...form, temperature: (v[0] ?? 40) / 100 })}
                  className="mt-2"
                />
              </div>
              <div>
                <Label className="text-xs">Max tokens · {form.maxTokens}</Label>
                <Slider
                  value={[form.maxTokens]}
                  min={128}
                  max={4096}
                  step={64}
                  onValueChange={(v) => setForm({ ...form, maxTokens: v[0] ?? 1024 })}
                  className="mt-2"
                />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="space-y-4 p-5">
              <p className="text-sm font-semibold text-foreground">Editor defaults</p>
              <div>
                <Label className="text-xs">Default tone</Label>
                <Select value={form.defaultTone} onValueChange={(v) => setForm({ ...form, defaultTone: v })}>
                  <SelectTrigger className="mt-1">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {AI_TONES.map((t) => (
                      <SelectItem key={t.key} value={t.key}>
                        {t.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label className="text-xs">Default language</Label>
                <Select value={form.defaultLanguage} onValueChange={(v) => setForm({ ...form, defaultLanguage: v })}>
                  <SelectTrigger className="mt-1">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {LANGUAGES.map((l) => (
                      <SelectItem key={l.code} value={l.code}>
                        {l.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label className="text-xs">Creativity · {creativity}%</Label>
                <Slider
                  value={[creativity]}
                  onValueChange={(v) => setForm({ ...form, temperature: (v[0] ?? 50) / 50 })}
                  className="mt-2"
                />
                <p className="mt-1 text-[11px] text-muted-foreground">
                  Higher values produce more varied phrasing; lower values stay closer to source.
                </p>
              </div>
              <p className="text-sm font-semibold text-foreground">Automation</p>
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-foreground">Auto review after generation</p>
                  <p className="text-xs text-muted-foreground">
                    Automatically compute grammar, tone and compliance findings.
                  </p>
                </div>
                <Switch checked={form.autoReview} onCheckedChange={(v) => setForm({ ...form, autoReview: v })} />
              </div>
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-foreground">Autosave drafts</p>
                  <p className="text-xs text-muted-foreground">
                    Keeps a rolling autosave of workspace content.
                  </p>
                </div>
                <Switch checked={form.autoSave} onCheckedChange={(v) => setForm({ ...form, autoSave: v })} />
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
  );
}
