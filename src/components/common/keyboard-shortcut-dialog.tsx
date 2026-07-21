import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { helpService } from "@/services/help.service";

interface KeyboardShortcutDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function KeyboardShortcutDialog({ open, onOpenChange }: KeyboardShortcutDialogProps) {
  const shortcuts = useQuery({ queryKey: ["help", "shortcuts"], queryFn: () => helpService.shortcuts(), enabled: open });
  const grouped = (shortcuts.data ?? []).reduce<Record<string, typeof shortcuts.data>>((acc, s) => {
    (acc[s.category] ||= []).push(s);
    return acc;
  }, {} as Record<string, typeof shortcuts.data>);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Keyboard shortcuts</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          {Object.entries(grouped).map(([cat, items]) => (
            <div key={cat}>
              <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">{cat}</p>
              <ul className="divide-y divide-border rounded-lg border">
                {items?.map((s, i) => (
                  <li key={i} className="flex items-center justify-between px-3 py-2 text-sm">
                    <span>{s.description}</span>
                    <span className="flex gap-1">
                      {s.keys.filter(Boolean).map((k) => (
                        <kbd key={k} className="rounded bg-muted px-1.5 py-0.5 font-mono text-[11px]">{k}</kbd>
                      ))}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </DialogContent>
    </Dialog>
  );
}

export function useKeyboardShortcutDialog(): [boolean, (open: boolean) => void] {
  const [open, setOpen] = useState(false);
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "?" && !e.metaKey && !e.ctrlKey && !e.altKey) {
        const t = e.target as HTMLElement | null;
        if (t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA" || t.isContentEditable)) return;
        e.preventDefault();
        setOpen(true);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);
  return [open, setOpen];
}
