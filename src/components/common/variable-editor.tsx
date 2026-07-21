import { Plus, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { BUILTIN_VARIABLES } from "@/constants/template";
import type { TemplateVariable } from "@/types/template";
import { cn } from "@/lib/utils";

interface Props {
  detected: string[];
  extras: TemplateVariable[];
  onInsert: (key: string) => void;
  onAddExtra: (v: TemplateVariable) => void;
  onRemoveExtra: (key: string) => void;
  className?: string;
}

export function VariableEditor({ detected, extras, onInsert, onAddExtra, onRemoveExtra, className }: Props) {
  return (
    <div className={cn("space-y-4 rounded-lg border bg-card/60 p-4", className)}>
      <div>
        <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          Built-in variables
        </p>
        <div className="mt-2 flex flex-wrap gap-1.5">
          {BUILTIN_VARIABLES.map((v) => (
            <button
              key={v.key}
              type="button"
              onClick={() => onInsert(v.key)}
              className="rounded-full border bg-background px-2 py-0.5 text-xs text-foreground hover:border-primary hover:text-primary"
            >
              {`{{${v.key}}}`}
            </button>
          ))}
        </div>
      </div>

      <div>
        <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          Detected in content ({detected.length})
        </p>
        <div className="mt-2 flex flex-wrap gap-1.5">
          {detected.length === 0 ? (
            <span className="text-xs text-muted-foreground">None yet — add {`{{variable_name}}`} in your content.</span>
          ) : (
            detected.map((k) => (
              <span
                key={k}
                className="rounded-full bg-primary/10 px-2 py-0.5 text-xs font-medium text-primary"
              >
                {`{{${k}}}`}
              </span>
            ))
          )}
        </div>
      </div>

      <div>
        <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          Custom variables
        </p>
        <div className="mt-2 space-y-2">
          {extras.map((v) => (
            <div key={v.key} className="flex items-center gap-2 rounded-md border bg-background px-2 py-1.5 text-sm">
              <span className="font-mono text-xs text-primary">{`{{${v.key}}}`}</span>
              <span className="text-muted-foreground">{v.label}</span>
              <Button
                type="button"
                size="icon"
                variant="ghost"
                className="ml-auto h-6 w-6"
                onClick={() => onRemoveExtra(v.key)}
                aria-label={`Remove ${v.key}`}
              >
                <X className="h-3.5 w-3.5" />
              </Button>
            </div>
          ))}
          <AddCustom onAdd={onAddExtra} />
        </div>
      </div>
    </div>
  );
}

function AddCustom({ onAdd }: { onAdd: (v: TemplateVariable) => void }) {
  return (
    <form
      className="flex items-center gap-2"
      onSubmit={(e) => {
        e.preventDefault();
        const form = e.currentTarget;
        const key = (form.elements.namedItem("key") as HTMLInputElement).value.trim();
        const label = (form.elements.namedItem("label") as HTMLInputElement).value.trim();
        if (!key) return;
        onAdd({ key: key.replace(/[^a-zA-Z0-9_]/g, "_"), label: label || key });
        form.reset();
      }}
    >
      <Input name="key" placeholder="key_name" className="h-8" aria-label="Variable key" />
      <Input name="label" placeholder="Label" className="h-8" aria-label="Variable label" />
      <Button type="submit" variant="outline" size="sm" className="gap-1">
        <Plus className="h-3.5 w-3.5" /> Add
      </Button>
    </form>
  );
}
