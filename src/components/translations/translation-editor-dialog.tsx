import { useEffect, useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  TRANSLATION_ENTITY_TYPES,
  type EntityTranslation,
  type EntityTranslationInput,
  type EntityTranslationUpdate,
  type TranslationLocale,
} from "@/types/translation";

interface Props {
  open: boolean;
  onOpenChange: (o: boolean) => void;
  locales: TranslationLocale[];
  existing?: EntityTranslation | null;
  submitting?: boolean;
  onSubmit: (
    input: EntityTranslationInput | EntityTranslationUpdate,
    mode: "create" | "update",
  ) => void | Promise<void>;
  /** Preset entity context (used from entity translation views). */
  preset?: { entityType?: string; entityId?: string; locale?: string; fieldName?: string };
}

/**
 * Dialog to create or edit an entity translation. Reuses shadcn primitives
 * so it matches the existing form language across the app.
 */
export function TranslationEditorDialog({
  open,
  onOpenChange,
  locales,
  existing,
  submitting,
  onSubmit,
  preset,
}: Props) {
  const editing = Boolean(existing);
  const [entityType, setEntityType] = useState<string>(
    existing?.entityType ?? preset?.entityType ?? TRANSLATION_ENTITY_TYPES[0],
  );
  const [entityId, setEntityId] = useState<string>(
    existing?.entityId ?? preset?.entityId ?? "",
  );
  const [locale, setLocale] = useState<string>(
    existing?.locale ?? preset?.locale ?? locales[0]?.locale ?? "en",
  );
  const [fieldName, setFieldName] = useState<string>(
    existing?.fieldName ?? preset?.fieldName ?? "title",
  );
  const [translatedValue, setTranslatedValue] = useState<string>(
    existing?.translatedValue ?? "",
  );

  useEffect(() => {
    if (!open) return;
    setEntityType(existing?.entityType ?? preset?.entityType ?? TRANSLATION_ENTITY_TYPES[0]);
    setEntityId(existing?.entityId ?? preset?.entityId ?? "");
    setLocale(existing?.locale ?? preset?.locale ?? locales[0]?.locale ?? "en");
    setFieldName(existing?.fieldName ?? preset?.fieldName ?? "title");
    setTranslatedValue(existing?.translatedValue ?? "");
  }, [open, existing, preset, locales]);

  const canSubmit =
    entityType.trim() &&
    entityId.trim() &&
    locale.trim() &&
    fieldName.trim() &&
    translatedValue.trim() &&
    !submitting;

  const handle = () => {
    if (editing) {
      void onSubmit({ translatedValue }, "update");
    } else {
      void onSubmit(
        { entityType, entityId, locale, fieldName, translatedValue },
        "create",
      );
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>{editing ? "Edit translation" : "New translation"}</DialogTitle>
          <DialogDescription>
            {editing
              ? "Update the translated value. Status and workflow are managed via the review / publish actions."
              : "Record a translated value for an entity field in the target locale."}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-3">
          <div className="grid gap-2 md:grid-cols-2">
            <div>
              <Label>Entity type</Label>
              <Select
                value={entityType}
                onValueChange={setEntityType}
                disabled={editing}
              >
                <SelectTrigger className="mt-1"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {TRANSLATION_ENTITY_TYPES.map((t) => (
                    <SelectItem key={t} value={t}>{t}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Locale</Label>
              <Select value={locale} onValueChange={setLocale} disabled={editing}>
                <SelectTrigger className="mt-1"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {locales.length === 0 ? (
                    <SelectItem value={locale}>{locale}</SelectItem>
                  ) : (
                    locales.map((l) => (
                      <SelectItem key={l.locale} value={l.locale}>
                        {l.locale} — {l.displayName}
                      </SelectItem>
                    ))
                  )}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div>
            <Label>Entity ID</Label>
            <Input
              className="mt-1 font-mono text-xs"
              value={entityId}
              onChange={(e) => setEntityId(e.target.value)}
              disabled={editing}
              placeholder="uuid"
            />
          </div>

          <div>
            <Label>Field name</Label>
            <Input
              className="mt-1"
              value={fieldName}
              onChange={(e) => setFieldName(e.target.value)}
              disabled={editing}
              placeholder="title | description | body"
            />
          </div>

          <div>
            <Label>Translated value</Label>
            <Textarea
              className="mt-1 min-h-[140px]"
              value={translatedValue}
              onChange={(e) => setTranslatedValue(e.target.value)}
            />
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button>
          <Button onClick={handle} disabled={!canSubmit}>
            {submitting ? "Saving…" : editing ? "Save changes" : "Create translation"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
