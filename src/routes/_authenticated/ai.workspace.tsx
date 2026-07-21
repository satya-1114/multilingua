import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { Sparkles, Wand2, Save, RefreshCw } from "lucide-react";
import { toast } from "sonner";
import { SectionHeader } from "@/components/common/section-header";
import { AiEditor } from "@/components/common/ai-editor";
import { SuggestionPanel } from "@/components/common/suggestion-panel";
import { ContentScoreCard } from "@/components/common/content-score-card";
import { LanguageBadge } from "@/components/common/language-badge";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Slider } from "@/components/ui/slider";
import { Badge } from "@/components/ui/badge";
import { LANGUAGES, COMMUNICATION_CHANNELS } from "@/constants/india";
import {
  AI_CONTENT_TYPES,
  AI_GENERATION_MODES,
  AI_TONES,
  AI_READING_LEVELS,
  AI_COMPLIANCE_RULES,
} from "@/constants/ai";
import { aiService } from "@/services/ai.service";
import { contentReviewService } from "@/services/content-review.service";
import { draftService } from "@/services/draft.service";
import { environmentService } from "@/services/environment.service";
import type {
  AiContentScores,
  AiContentType,
  AiGenerationMode,
  AiSuggestion,
  AiTone,
} from "@/types/ai";

export const Route = createFileRoute("/_authenticated/ai/workspace")({
  component: AiWorkspacePage,
});

function AiWorkspacePage() {
  const [contentType, setContentType] = useState<AiContentType>("campaign_announcement");
  const [mode, setMode] = useState<AiGenerationMode>("create");
  const [tone, setTone] = useState<AiTone>("professional");
  const [language, setLanguage] = useState("en");
  const [channel, setChannel] = useState<string>("sms");
  const [wordLimit, setWordLimit] = useState<number>(120);
  const [objective, setObjective] = useState("");
  const [audience, setAudience] = useState("");
  const [prompt, setPrompt] = useState(() => {
    if (typeof window === "undefined") return "";
    const seed = sessionStorage.getItem("ai:prompt");
    if (seed) sessionStorage.removeItem("ai:prompt");
    return seed ?? "";
  });
  const [keywords, setKeywords] = useState("");
  const [cta, setCta] = useState("");
  const [compliance, setCompliance] = useState<string[]>([]);
  const [content, setContent] = useState("");
  const [suggestions, setSuggestions] = useState<AiSuggestion[]>([]);
  const [scores, setScores] = useState<AiContentScores | null>(null);

  const generate = useMutation({
    mutationFn: () =>
      aiService.generate({
        contentType,
        mode,
        tone,
        language,
        channel: channel as never,
        wordLimit,
        objective,
        audience,
        prompt: prompt || `Draft a ${contentType.replace(/_/g, " ")} for our audience.`,
        keywords: keywords ? keywords.split(",").map((k) => k.trim()) : [],
        callToAction: cta,
        compliance,
      }),
    onSuccess: (res) => {
      setContent(res.data.content);
      setSuggestions(res.data.suggestions);
      setScores(res.data.scores);
      toast.success("Content generated");
    },
    onError: (err) => {
      const msg = (err as Error)?.message || "Generation failed. Please try again.";
      toast.error(msg);
    },
  });

  const review = useMutation({
    mutationFn: () => contentReviewService.review(content),
    onSuccess: (res) => {
      setSuggestions(res.data.suggestions);
      setScores(res.data.scores);
      toast.success("Content reviewed");
    },
  });

  const save = useMutation({
    mutationFn: () =>
      draftService.upsert({
        title: `Draft — ${AI_CONTENT_TYPES.find((c) => c.key === contentType)?.label ?? "Untitled"}`,
        content,
        language,
        contentType,
        autoSaved: false,
      }),
    onSuccess: () => toast.success("Draft saved"),
  });

  const toggleCompliance = (id: string) =>
    setCompliance((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));

  return (
    <div className="space-y-5">
        <SectionHeader
          title="AI Workspace"
          description="Compose, review and translate multilingual communications with full campaign context."
          actions={
            <div className="flex gap-2">
              {environmentService.isAiMockEnabled() && (
                <Badge variant="outline" className="border-amber-500/60 text-amber-600">
                  Demo mocks
                </Badge>
              )}
              <Button variant="outline" onClick={() => review.mutate()} disabled={!content}>
                <RefreshCw className="mr-1.5 h-4 w-4" /> Review
              </Button>
              <Button variant="outline" onClick={() => save.mutate()} disabled={!content}>
                <Save className="mr-1.5 h-4 w-4" /> Save draft
              </Button>
              <Button onClick={() => generate.mutate()} disabled={generate.isPending}>
                <Wand2 className="mr-1.5 h-4 w-4" />
                {generate.isPending ? "Generating…" : "Generate"}
              </Button>
            </div>
          }
        />

        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="grid gap-4 lg:grid-cols-12"
        >
          {/* Left panel: context */}
          <Card className="lg:col-span-3">
            <CardContent className="space-y-4 p-4">
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                Campaign context
              </p>

              <FieldSelect
                label="Content type"
                value={contentType}
                onValueChange={(v) => setContentType(v as AiContentType)}
                options={AI_CONTENT_TYPES.map((c) => ({ value: c.key, label: c.label }))}
              />
              <FieldSelect
                label="Mode"
                value={mode}
                onValueChange={(v) => setMode(v as AiGenerationMode)}
                options={AI_GENERATION_MODES.map((m) => ({ value: m.key, label: m.label }))}
              />
              <FieldSelect
                label="Tone"
                value={tone}
                onValueChange={(v) => setTone(v as AiTone)}
                options={AI_TONES.map((t) => ({ value: t.key, label: t.label }))}
              />
              <FieldSelect
                label="Language"
                value={language}
                onValueChange={setLanguage}
                options={LANGUAGES.map((l) => ({ value: l.code, label: l.label }))}
              />
              <FieldSelect
                label="Channel"
                value={channel}
                onValueChange={setChannel}
                options={COMMUNICATION_CHANNELS.map((c) => ({ value: c.key, label: c.label }))}
              />
              <FieldSelect
                label="Reading level"
                value="professional"
                onValueChange={() => {}}
                options={AI_READING_LEVELS.map((l) => ({ value: l.key, label: l.label }))}
              />
              <div>
                <Label className="text-xs">Word limit: {wordLimit}</Label>
                <Slider
                  value={[wordLimit]}
                  min={40}
                  max={500}
                  step={10}
                  onValueChange={(v) => setWordLimit(v[0] ?? 120)}
                  className="mt-2"
                />
              </div>
              <div>
                <Label className="text-xs">Objective</Label>
                <Input
                  value={objective}
                  onChange={(e) => setObjective(e.target.value)}
                  placeholder="e.g. Encourage flu vaccination"
                  className="mt-1"
                />
              </div>
              <div>
                <Label className="text-xs">Target audience</Label>
                <Input
                  value={audience}
                  onChange={(e) => setAudience(e.target.value)}
                  placeholder="e.g. Senior citizens, Bengaluru Urban"
                  className="mt-1"
                />
              </div>
              <div>
                <Label className="text-xs">Keywords</Label>
                <Input
                  value={keywords}
                  onChange={(e) => setKeywords(e.target.value)}
                  placeholder="comma separated"
                  className="mt-1"
                />
              </div>
              <div>
                <Label className="text-xs">Call to action</Label>
                <Input
                  value={cta}
                  onChange={(e) => setCta(e.target.value)}
                  placeholder="e.g. Register at portal.gov"
                  className="mt-1"
                />
              </div>
              <div>
                <Label className="text-xs">Compliance</Label>
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {AI_COMPLIANCE_RULES.map((rule) => (
                    <button
                      key={rule.id}
                      type="button"
                      onClick={() => toggleCompliance(rule.id)}
                      className={
                        "rounded-md border px-2 py-1 text-[11px] font-medium transition-colors " +
                        (compliance.includes(rule.id)
                          ? "border-primary bg-primary/10 text-primary"
                          : "border-border/70 text-muted-foreground hover:border-primary/40")
                      }
                    >
                      {rule.label}
                    </button>
                  ))}
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Center: editor */}
          <div className="flex flex-col gap-3 lg:col-span-6">
            <Card>
              <CardContent className="space-y-2 p-4">
                <Label className="text-xs">Prompt</Label>
                <Textarea
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                  placeholder="Describe what you'd like to communicate…"
                  className="min-h-[80px]"
                />
                <div className="flex flex-wrap items-center gap-2 pt-1 text-[11px] text-muted-foreground">
                  <Badge variant="secondary" className="gap-1">
                    <Sparkles className="h-3 w-3" /> Mode: {mode}
                  </Badge>
                  <LanguageBadge code={language} />
                  <span>
                    Tone: <span className="font-medium text-foreground">{tone}</span>
                  </span>
                </div>
              </CardContent>
            </Card>
            <AiEditor
              value={content}
              onChange={setContent}
              wordLimit={wordLimit}
              placeholder="Generated content will appear here. You can also draft directly."
              className="flex-1"
            />
          </div>

          {/* Right: suggestions + scores */}
          <div className="space-y-3 lg:col-span-3">
            <SuggestionPanel suggestions={suggestions} />
            {scores && <ContentScoreCard scores={scores} />}
          </div>
        </motion.div>
      </div>
  );
}

interface FieldSelectProps {
  label: string;
  value: string;
  onValueChange: (v: string) => void;
  options: { value: string; label: string }[];
}

function FieldSelect({ label, value, onValueChange, options }: FieldSelectProps) {
  return (
    <div>
      <Label className="text-xs">{label}</Label>
      <Select value={value} onValueChange={onValueChange}>
        <SelectTrigger className="mt-1">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {options.map((o) => (
            <SelectItem key={o.value} value={o.value}>
              {o.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}
