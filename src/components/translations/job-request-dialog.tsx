import { useEffect, useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
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
  type TranslationJobInput,
  type TranslationLocale,
} from "@/types/translation";

interface Props {
  open: boolean;
  onOpenChange: (o: boolean) => void;
  locales: TranslationLocale[];
  submitting?: boolean;
  onSubmit: (input: TranslationJobInput) => void | Promise<void>;
  preset?: { entityType?: string; entityId?: string; sourceLocale?: string };
}

export function JobRequestDialog({
  open,
  onOpenChange,
  locales,
  submitting,
  onSubmit,
  preset,
}: Props) {
  const defaultLocale = locales.find((l) => l.defaultLocale)?.locale ?? "en";
  const [entityType, setEntityType] = useState<string>(
    preset?.entityType ?? TRANSLATION_ENTITY_TYPES[0],
  );
  const [entityId, setEntityId] = useState(preset?.entityId ?? "");
  const [sourceLocale, setSourceLocale] = useState(
    preset?.sourceLocale ?? defaultLocale,
  );
  const [targetLocale, setTargetLocale] = useState(
    locales.find((l) => l.locale !== defaultLocale)?.locale ?? "hi",
  );
  const [provider, setProvider] = useState<string>("manual");

  useEffect(() => {
    if (!open) return;
    setEntityType(preset?.entityType ?? TRANSLATION_ENTITY_TYPES[0]);
    setEntityId(preset?.entityId ?? "");
    setSourceLocale(preset?.sourceLocale ?? defaultLocale);
    setTargetLocale(
      locales.find((l) => l.locale !== (preset?.sourceLocale ?? defaultLocale))
        ?.locale ?? "hi",
    );
    setProvider("manual");
  }, [open, preset, defaultLocale, locales]);

  const canSubmit =
    entityType.trim() &&
    entityId.trim() &&
    sourceLocale.trim() &&
    targetLocale.trim() &&
    sourceLocale !== targetLocale &&
    !submitting;

  const handle = () => {
    void onSubmit({
      entityType,
      entityId,
      sourceLocale,
      targetLocale,
      provider,
    });
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Request translation job</DialogTitle>
          <DialogDescription>
            Queue a translation job for an entity into a target locale. The job
            transitions through pending → processing → completed as work happens.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-3">
          <div className="grid gap-2 md:grid-cols-2">
            <div>
              <Label>Entity type</Label>
              <Select value={entityType} onValueChange={setEntityType}>
                <SelectTrigger className="mt-1"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {TRANSLATION_ENTITY_TYPES.map((t) => (
                    <SelectItem key={t} value={t}>{t}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Provider</Label>
              <Input
                className="mt-1"
                value={provider}
                onChange={(e) => setProvider(e.target.value)}
                placeholder="manual"
              />
            </div>
          </div>

          <div>
            <Label>Entity ID</Label>
            <Input
              className="mt-1 font-mono text-xs"
              value={entityId}
              onChange={(e) => setEntityId(e.target.value)}
              placeholder="uuid"
            />
          </div>

          <div className="grid gap-2 md:grid-cols-2">
            <div>
              <Label>Source locale</Label>
              <Select value={sourceLocale} onValueChange={setSourceLocale}>
                <SelectTrigger className="mt-1"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {locales.map((l) => (
                    <SelectItem key={l.locale} value={l.locale}>
                      {l.locale} — {l.displayName}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Target locale</Label>
              <Select value={targetLocale} onValueChange={setTargetLocale}>
                <SelectTrigger className="mt-1"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {locales
                    .filter((l) => l.locale !== sourceLocale)
                    .map((l) => (
                      <SelectItem key={l.locale} value={l.locale}>
                        {l.locale} — {l.displayName}
                      </SelectItem>
                    ))}
                </SelectContent>
              </Select>
            </div>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button>
          <Button onClick={handle} disabled={!canSubmit}>
            {submitting ? "Requesting…" : "Request job"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
