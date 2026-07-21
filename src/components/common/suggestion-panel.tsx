import { AlertTriangle, CheckCircle2, Info, Sparkles } from "lucide-react";
import type { AiSuggestion } from "@/types/ai";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const ICONS = {
  info: Info,
  warning: AlertTriangle,
  error: AlertTriangle,
} as const;

const SEVERITY_TONES: Record<AiSuggestion["severity"], string> = {
  info: "text-primary",
  warning: "text-warning",
  error: "text-destructive",
};

interface SuggestionPanelProps {
  suggestions: AiSuggestion[];
  onApply?: (suggestion: AiSuggestion) => void;
  onDismiss?: (suggestion: AiSuggestion) => void;
}

export function SuggestionPanel({
  suggestions,
  onApply,
  onDismiss,
}: SuggestionPanelProps) {
  return (
    <Card>
      <CardContent className="p-4">
        <div className="mb-3 flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-primary" />
          <p className="text-sm font-semibold text-foreground">AI suggestions</p>
          <span className="ml-auto text-xs text-muted-foreground">
            {suggestions.length} findings
          </span>
        </div>
        {suggestions.length === 0 ? (
          <div className="flex flex-col items-center gap-2 rounded-lg border border-dashed border-border/70 py-8 text-center">
            <CheckCircle2 className="h-6 w-6 text-success" />
            <p className="text-sm text-muted-foreground">
              No suggestions. Content looks ready to publish.
            </p>
          </div>
        ) : (
          <ul className="space-y-2">
            {suggestions.map((s) => {
              const Icon = ICONS[s.severity];
              return (
                <li
                  key={s.id}
                  className="rounded-lg border border-border/70 bg-card p-3"
                >
                  <div className="flex items-start gap-2">
                    <Icon className={cn("h-4 w-4 shrink-0", SEVERITY_TONES[s.severity])} />
                    <div className="min-w-0 flex-1">
                      <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                        {s.kind}
                      </p>
                      <p className="mt-0.5 text-sm text-foreground">{s.message}</p>
                      {s.suggestion && (
                        <p className="mt-1 text-xs text-muted-foreground">
                          Try: {s.suggestion}
                        </p>
                      )}
                    </div>
                  </div>
                  {(onApply || onDismiss) && (
                    <div className="mt-2 flex justify-end gap-2">
                      {onDismiss && (
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => onDismiss(s)}
                        >
                          Dismiss
                        </Button>
                      )}
                      {onApply && s.suggestion && (
                        <Button size="sm" variant="secondary" onClick={() => onApply(s)}>
                          Apply
                        </Button>
                      )}
                    </div>
                  )}
                </li>
              );
            })}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
