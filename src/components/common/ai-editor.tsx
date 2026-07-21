import { useEffect, useMemo, useRef, useState } from "react";
import { motion } from "framer-motion";
import { Redo2, Undo2 } from "lucide-react";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";

interface AiEditorProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  className?: string;
  wordLimit?: number;
}

/**
 * Rich AI editor with autosave, undo/redo, and live counters.
 * Kept UI-only: business logic (saving, review, generation) is delegated to
 * services by the parent workspace.
 */
export function AiEditor({
  value,
  onChange,
  placeholder,
  className,
  wordLimit,
}: AiEditorProps) {
  const [history, setHistory] = useState<string[]>([value]);
  const [cursor, setCursor] = useState(0);
  const skipHistoryRef = useRef(false);
  const [lastSavedAt, setLastSavedAt] = useState<Date | null>(null);

  useEffect(() => {
    if (skipHistoryRef.current) {
      skipHistoryRef.current = false;
      return;
    }
    const t = setTimeout(() => {
      setHistory((prev) => {
        const next = prev.slice(0, cursor + 1);
        if (next[next.length - 1] === value) return prev;
        next.push(value);
        return next.slice(-40);
      });
      setCursor((c) => Math.min(c + 1, 39));
      setLastSavedAt(new Date());
    }, 500);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value]);

  const stats = useMemo(() => {
    const words = value.trim().split(/\s+/).filter(Boolean).length;
    const characters = value.length;
    return { words, characters, tokens: Math.round(words * 1.35) };
  }, [value]);

  const undo = () => {
    if (cursor === 0) return;
    const next = cursor - 1;
    skipHistoryRef.current = true;
    setCursor(next);
    onChange(history[next] ?? "");
  };

  const redo = () => {
    if (cursor >= history.length - 1) return;
    const next = cursor + 1;
    skipHistoryRef.current = true;
    setCursor(next);
    onChange(history[next] ?? "");
  };

  const overLimit = wordLimit ? stats.words > wordLimit : false;

  return (
    <div className={cn("flex h-full flex-col rounded-xl border border-border/70 bg-card", className)}>
      <div className="flex items-center justify-between border-b border-border/70 px-3 py-2">
        <div className="flex items-center gap-1">
          <button
            type="button"
            onClick={undo}
            disabled={cursor === 0}
            className="rounded-md p-1.5 text-muted-foreground hover:bg-muted disabled:cursor-not-allowed disabled:opacity-40"
            aria-label="Undo"
          >
            <Undo2 className="h-4 w-4" />
          </button>
          <button
            type="button"
            onClick={redo}
            disabled={cursor >= history.length - 1}
            className="rounded-md p-1.5 text-muted-foreground hover:bg-muted disabled:cursor-not-allowed disabled:opacity-40"
            aria-label="Redo"
          >
            <Redo2 className="h-4 w-4" />
          </button>
        </div>
        <div className="flex items-center gap-3 text-[11px] text-muted-foreground">
          <span className={cn(overLimit && "font-semibold text-destructive")}>
            {stats.words} words{wordLimit ? ` / ${wordLimit}` : ""}
          </span>
          <span>{stats.characters} chars</span>
          <span>{stats.tokens} tokens</span>
          {lastSavedAt && (
            <motion.span
              key={lastSavedAt.toISOString()}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="text-success"
            >
              Saved
            </motion.span>
          )}
        </div>
      </div>
      <Textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="min-h-[360px] flex-1 resize-none rounded-none border-0 bg-transparent p-4 font-mono text-sm leading-relaxed focus-visible:ring-0"
      />
    </div>
  );
}
