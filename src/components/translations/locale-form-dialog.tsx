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
import { Switch } from "@/components/ui/switch";
import { Button } from "@/components/ui/button";
import type {
  TranslationLocale,
  TranslationLocaleInput,
  TranslationLocaleUpdate,
} from "@/types/translation";

interface Props {
  open: boolean;
  onOpenChange: (o: boolean) => void;
  existing?: TranslationLocale | null;
  submitting?: boolean;
  onSubmit: (
    input: TranslationLocaleInput | TranslationLocaleUpdate,
    mode: "create" | "update",
  ) => void | Promise<void>;
}

export function LocaleFormDialog({
  open,
  onOpenChange,
  existing,
  submitting,
  onSubmit,
}: Props) {
  const editing = Boolean(existing);
  const [locale, setLocale] = useState(existing?.locale ?? "");
  const [displayName, setDisplayName] = useState(existing?.displayName ?? "");
  const [nativeName, setNativeName] = useState(existing?.nativeName ?? "");
  const [rtl, setRtl] = useState(Boolean(existing?.rtl));
  const [enabled, setEnabled] = useState(existing?.enabled ?? true);
  const [sortOrder, setSortOrder] = useState<number>(existing?.sortOrder ?? 0);

  useEffect(() => {
    if (!open) return;
    setLocale(existing?.locale ?? "");
    setDisplayName(existing?.displayName ?? "");
    setNativeName(existing?.nativeName ?? "");
    setRtl(Boolean(existing?.rtl));
    setEnabled(existing?.enabled ?? true);
    setSortOrder(existing?.sortOrder ?? 0);
  }, [open, existing]);

  const canSubmit =
    (editing || locale.trim().length >= 2) &&
    displayName.trim().length > 0 &&
    !submitting;

  const handle = () => {
    const payload = {
      displayName,
      nativeName: nativeName || null,
      rtl,
      enabled,
      sortOrder,
    };
    if (editing) {
      void onSubmit(payload, "update");
    } else {
      void onSubmit({ locale, ...payload }, "create");
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>{editing ? "Update locale" : "Register locale"}</DialogTitle>
          <DialogDescription>
            {editing
              ? "Update display metadata. Enable/disable and default flags are set from the list actions."
              : "Register a locale that the platform can translate content into."}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-3">
          <div>
            <Label>Locale code</Label>
            <Input
              className="mt-1 font-mono"
              value={locale}
              onChange={(e) => setLocale(e.target.value)}
              disabled={editing}
              placeholder="e.g. hi, ta, en-IN"
            />
          </div>
          <div>
            <Label>Display name</Label>
            <Input
              className="mt-1"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              placeholder="Hindi"
            />
          </div>
          <div>
            <Label>Native name</Label>
            <Input
              className="mt-1"
              value={nativeName ?? ""}
              onChange={(e) => setNativeName(e.target.value)}
              placeholder="हिन्दी"
            />
          </div>
          <div className="flex items-center justify-between">
            <Label className="mb-0">Right-to-left</Label>
            <Switch checked={rtl} onCheckedChange={setRtl} />
          </div>
          <div className="flex items-center justify-between">
            <Label className="mb-0">Enabled</Label>
            <Switch checked={enabled} onCheckedChange={setEnabled} />
          </div>
          <div>
            <Label>Sort order</Label>
            <Input
              type="number"
              className="mt-1"
              value={sortOrder}
              onChange={(e) => setSortOrder(Number(e.target.value) || 0)}
            />
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button>
          <Button onClick={handle} disabled={!canSubmit}>
            {submitting ? "Saving…" : editing ? "Save" : "Register"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
