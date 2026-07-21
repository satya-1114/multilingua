import { ArrowRight, RotateCcw } from "lucide-react";
import type { TranslationResult } from "@/types/translation";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { LanguageBadge } from "./language-badge";

interface TranslationComparisonProps {
  result: TranslationResult;
  onReTranslate?: () => void;
}

export function TranslationComparison({
  result,
  onReTranslate,
}: TranslationComparisonProps) {
  return (
    <Card>
      <CardContent className="p-4">
        <div className="mb-3 flex items-center gap-2">
          <LanguageBadge code={result.sourceLanguage} />
          <ArrowRight className="h-3.5 w-3.5 text-muted-foreground" />
          <LanguageBadge code={result.targetLanguage} />
          {onReTranslate && (
            <Button
              size="sm"
              variant="ghost"
              className="ml-auto"
              onClick={onReTranslate}
            >
              <RotateCcw className="mr-1.5 h-3.5 w-3.5" /> Re-translate
            </Button>
          )}
        </div>
        <div className="grid gap-3 md:grid-cols-2">
          <div className="rounded-lg border border-border/70 bg-muted/30 p-3">
            <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
              Source
            </p>
            <p className="mt-2 whitespace-pre-wrap text-sm text-foreground">
              {result.sourceContent}
            </p>
          </div>
          <div className="rounded-lg border border-border/70 bg-card p-3">
            <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
              Target
            </p>
            <p className="mt-2 whitespace-pre-wrap text-sm text-foreground">
              {result.translatedContent}
            </p>
          </div>
        </div>
        <div className="mt-3 grid grid-cols-3 gap-2 text-center md:grid-cols-6">
          {Object.entries(result.scores).map(([key, value]) => (
            <div key={key} className="rounded-md bg-muted/40 px-2 py-1.5">
              <p className="text-[10px] uppercase tracking-wide text-muted-foreground">
                {key}
              </p>
              <p className="text-sm font-semibold tabular-nums text-foreground">{value}</p>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
