import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { toast } from "sonner";
import { Languages, Wand2 } from "lucide-react";

import { SectionHeader } from "@/components/common/section-header";
import { TranslationComparison } from "@/components/common/translation-comparison";
import { LanguageBadge } from "@/components/common/language-badge";

import { Card, CardContent } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

import { LANGUAGES } from "@/constants/india";
import { translationService } from "@/services/translation.service";
import { environmentService } from "@/services/environment.service";
import type { TranslationResult } from "@/types/translation";

export const Route = createFileRoute("/_authenticated/translation")({
  component: TranslationPage,
});

function TranslationPage() {
  const workspaceId = environmentService.get("DEFAULT_WORKSPACE");

  const [mode, setMode] = useState<"single" | "batch">("single");
  const [source, setSource] = useState("en");
  const [target, setTarget] = useState("hi");

  const [batchTargets, setBatchTargets] = useState([
    "hi",
    "ta",
    "te",
  ]);

  const [content, setContent] = useState(
    "Dear resident, please ensure all vaccination cards are updated by 30 November. Contact the district health office for assistance.",
  );

  const [result, setResult] = useState<TranslationResult | null>(null);
  const [batchResults, setBatchResults] = useState<TranslationResult[]>([]);

  const translate = useMutation({
    mutationFn: () =>
      translationService.translate({
        sourceLanguage: source,
        targetLanguage: target,
        content,
        workspaceId,
      }),

    onSuccess: (res) => {
      setResult(res.data);
      toast.success("Translation completed.");
    },

    onError: (error: any) => {
      console.error(error);
      toast.error(error?.message ?? "Translation failed.");
    },
  });

  const batchTranslate = useMutation({
    mutationFn: () =>
      translationService.batch({
        sourceLanguage: source,
        targetLanguages: batchTargets,
        content,
        workspaceId,
      }),

    onSuccess: (res) => {
      setBatchResults(res.data.entries);
      toast.success(
        `Translated into ${res.data.entries.length} languages.`,
      );
    },

    onError: (error: any) => {
      console.error(error);
      toast.error(error?.message ?? "Batch translation failed.");
    },
  });

  const toggleBatch = (code: string) => {
    setBatchTargets((prev) =>
      prev.includes(code)
        ? prev.filter((c) => c !== code)
        : [...prev, code],
    );
  };

  return (
    <div className="space-y-5">
      <SectionHeader
        title="Translation Workspace"
        description="Translate content across Indian languages using AI."
        actions={
          mode === "single" ? (
            <Button
              onClick={() => translate.mutate()}
              disabled={translate.isPending}
            >
              <Wand2 className="mr-2 h-4 w-4" />
              {translate.isPending ? "Translating..." : "Translate"}
            </Button>
          ) : (
            <Button
              onClick={() => batchTranslate.mutate()}
              disabled={
                batchTranslate.isPending ||
                batchTargets.length === 0
              }
            >
              <Languages className="mr-2 h-4 w-4" />
              {batchTranslate.isPending
                ? "Translating..."
                : "Batch Translate"}
            </Button>
          )
        }
      />

      <Tabs
        value={mode}
        onValueChange={(v) => setMode(v as "single" | "batch")}
      >
        <TabsList>
          <TabsTrigger value="single">
            Single Language
          </TabsTrigger>

          <TabsTrigger value="batch">
            Batch Translate
          </TabsTrigger>
        </TabsList>
      </Tabs>

      <Card>
        <CardContent className="grid gap-4 p-4 md:grid-cols-[240px_1fr]">
          <div className="space-y-3">
            <div>
              <Label>Source Language</Label>

              <Select value={source} onValueChange={setSource}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>

                <SelectContent>
                  {LANGUAGES.map((lang) => (
                    <SelectItem
                      key={lang.code}
                      value={lang.code}
                    >
                      {lang.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {mode === "single" ? (
              <div>
                <Label>Target Language</Label>

                <Select
                  value={target}
                  onValueChange={setTarget}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>

                  <SelectContent>
                    {LANGUAGES.filter(
                      (l) => l.code !== source,
                    ).map((lang) => (
                      <SelectItem
                        key={lang.code}
                        value={lang.code}
                      >
                        {lang.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            ) : (
              <div>
                <Label>Target Languages</Label>

                <div className="mt-2 flex flex-wrap gap-2">
                  {LANGUAGES.filter(
                    (l) => l.code !== source,
                  ).map((lang) => (
                    <Button
                      key={lang.code}
                      size="sm"
                      type="button"
                      variant={
                        batchTargets.includes(lang.code)
                          ? "default"
                          : "outline"
                      }
                      onClick={() =>
                        toggleBatch(lang.code)
                      }
                    >
                      {lang.label}
                    </Button>
                  ))}
                </div>
              </div>
            )}
          </div>

          <div>
            <Label>Source Content</Label>

            <Textarea
              className="mt-2 min-h-[220px]"
              value={content}
              onChange={(e) =>
                setContent(e.target.value)
              }
            />

            <p className="mt-2 text-xs text-muted-foreground">
              {content.length} characters
            </p>
          </div>
        </CardContent>
      </Card>

      {mode === "single" && result && (
        <TranslationComparison
          result={result}
          onReTranslate={() => translate.mutate()}
        />
      )}

      {mode === "batch" &&
        batchResults.length > 0 && (
          <div className="grid gap-3">
            {batchResults.map((r) => (
              <Card key={r.id}>
                <CardContent className="p-4">
                  <div className="mb-3 flex items-center gap-2">
                    <LanguageBadge code={r.sourceLanguage} />

                    <span>→</span>

                    <LanguageBadge code={r.targetLanguage} />

                    <span className="ml-auto text-xs text-muted-foreground">
                      Accuracy {r.scores.accuracy}
                    </span>
                  </div>

                  <p className="whitespace-pre-wrap">
                    {r.translatedContent}
                  </p>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
    </div>
  );
}