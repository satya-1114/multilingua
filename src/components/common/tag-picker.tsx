import { useState } from "react";
import { Check, ChevronDown, Plus, X } from "lucide-react";
import type { AudienceTag } from "@/types/audience";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

interface TagPickerProps {
  tags: AudienceTag[];
  value: string[];
  onChange: (ids: string[]) => void;
  onCreate?: (name: string) => Promise<AudienceTag> | AudienceTag;
  placeholder?: string;
}

export function TagPicker({ tags, value, onChange, onCreate, placeholder = "Select tags" }: TagPickerProps) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  const selected = tags.filter((t) => value.includes(t.id));
  const filtered = tags.filter((t) => t.name.toLowerCase().includes(search.toLowerCase()));

  const toggle = (id: string) => {
    onChange(value.includes(id) ? value.filter((v) => v !== id) : [...value, id]);
  };

  const remove = (id: string) => onChange(value.filter((v) => v !== id));

  const create = async () => {
    if (!onCreate || !search.trim()) return;
    const created = await onCreate(search.trim());
    onChange([...value, created.id]);
    setSearch("");
  };

  return (
    <div className="space-y-2">
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger asChild>
          <Button variant="outline" role="combobox" className="w-full justify-between font-normal">
            <span className="text-muted-foreground">{selected.length ? `${selected.length} tag(s) selected` : placeholder}</span>
            <ChevronDown className="ml-2 h-4 w-4 opacity-50" />
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-[--radix-popover-trigger-width] p-0" align="start">
          <div className="border-b p-2">
            <Input
              placeholder="Search or create tag"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="h-8"
            />
          </div>
          <ul className="max-h-56 overflow-y-auto py-1">
            {filtered.map((t) => {
              const active = value.includes(t.id);
              return (
                <li key={t.id}>
                  <button
                    type="button"
                    onClick={() => toggle(t.id)}
                    className="flex w-full items-center gap-2 px-3 py-1.5 text-sm hover:bg-accent"
                  >
                    <span className={cn("flex h-4 w-4 items-center justify-center rounded border", active ? "border-primary bg-primary text-primary-foreground" : "border-border")}>
                      {active && <Check className="h-3 w-3" />}
                    </span>
                    <span className="h-2 w-2 rounded-full" style={{ background: t.color }} />
                    <span className="flex-1 text-left">{t.name}</span>
                    <span className="text-xs text-muted-foreground">{t.audienceCount}</span>
                  </button>
                </li>
              );
            })}
            {onCreate && search.trim() && !filtered.some((t) => t.name.toLowerCase() === search.trim().toLowerCase()) && (
              <li>
                <button
                  type="button"
                  onClick={create}
                  className="flex w-full items-center gap-2 px-3 py-1.5 text-sm hover:bg-accent text-primary"
                >
                  <Plus className="h-3.5 w-3.5" /> Create "{search.trim()}"
                </button>
              </li>
            )}
          </ul>
        </PopoverContent>
      </Popover>

      {selected.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {selected.map((t) => (
            <span
              key={t.id}
              className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs"
              style={{ background: `${t.color}1a`, color: t.color }}
            >
              {t.name}
              <button
                type="button"
                onClick={() => remove(t.id)}
                className="rounded-full hover:bg-black/10 dark:hover:bg-white/10"
                aria-label={`Remove ${t.name}`}
              >
                <X className="h-3 w-3" />
              </button>
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
