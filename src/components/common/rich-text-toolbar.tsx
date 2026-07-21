import { Bold, Italic, Underline, Link2, List, ListOrdered, Quote, Heading, Undo2, Redo2 } from "lucide-react";
import type { RefObject } from "react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface Props {
  targetRef: RefObject<HTMLTextAreaElement | null>;
  onInsert?: (before: string, after?: string) => void;
  className?: string;
}

function surround(el: HTMLTextAreaElement, before: string, after = before) {
  const { selectionStart, selectionEnd, value } = el;
  const sel = value.slice(selectionStart, selectionEnd) || "text";
  const next = value.slice(0, selectionStart) + before + sel + after + value.slice(selectionEnd);
  el.value = next;
  el.dispatchEvent(new Event("input", { bubbles: true }));
  el.focus();
  const caret = selectionStart + before.length;
  el.setSelectionRange(caret, caret + sel.length);
}

export function RichTextToolbar({ targetRef, onInsert, className }: Props) {
  const wrap = (before: string, after = before) => {
    if (targetRef.current) surround(targetRef.current, before, after);
    onInsert?.(before, after);
  };

  const btn = "h-8 w-8";
  return (
    <div className={cn("flex flex-wrap items-center gap-1 rounded-t-md border border-b-0 bg-muted/40 p-1", className)}>
      <Button type="button" variant="ghost" size="icon" className={btn} onClick={() => wrap("**")} aria-label="Bold">
        <Bold className="h-3.5 w-3.5" />
      </Button>
      <Button type="button" variant="ghost" size="icon" className={btn} onClick={() => wrap("*")} aria-label="Italic">
        <Italic className="h-3.5 w-3.5" />
      </Button>
      <Button type="button" variant="ghost" size="icon" className={btn} onClick={() => wrap("__")} aria-label="Underline">
        <Underline className="h-3.5 w-3.5" />
      </Button>
      <div className="mx-1 h-5 w-px bg-border" />
      <Button type="button" variant="ghost" size="icon" className={btn} onClick={() => wrap("## ", "")} aria-label="Heading">
        <Heading className="h-3.5 w-3.5" />
      </Button>
      <Button type="button" variant="ghost" size="icon" className={btn} onClick={() => wrap("> ", "")} aria-label="Quote">
        <Quote className="h-3.5 w-3.5" />
      </Button>
      <Button type="button" variant="ghost" size="icon" className={btn} onClick={() => wrap("- ", "")} aria-label="Bulleted list">
        <List className="h-3.5 w-3.5" />
      </Button>
      <Button type="button" variant="ghost" size="icon" className={btn} onClick={() => wrap("1. ", "")} aria-label="Numbered list">
        <ListOrdered className="h-3.5 w-3.5" />
      </Button>
      <Button type="button" variant="ghost" size="icon" className={btn} onClick={() => wrap("[", "](https://)")} aria-label="Link">
        <Link2 className="h-3.5 w-3.5" />
      </Button>
      <div className="ml-auto flex items-center gap-1">
        <Button
          type="button"
          variant="ghost"
          size="icon"
          className={btn}
          onClick={() => targetRef.current && document.execCommand("undo")}
          aria-label="Undo"
        >
          <Undo2 className="h-3.5 w-3.5" />
        </Button>
        <Button
          type="button"
          variant="ghost"
          size="icon"
          className={btn}
          onClick={() => targetRef.current && document.execCommand("redo")}
          aria-label="Redo"
        >
          <Redo2 className="h-3.5 w-3.5" />
        </Button>
      </div>
    </div>
  );
}
