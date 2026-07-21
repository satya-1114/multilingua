import { useEffect, useMemo, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Building2, Check, ChevronDown, Search, Star, StarOff } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { workspaceService } from "@/services/workspace.service";
import { eventBus } from "@/services/event-bus.service";
import { cn } from "@/lib/utils";
import type { Workspace } from "@/types/workspace";

function Avatar({ w, size = 32 }: { w: Workspace; size?: number }) {
  const initials = w.name
    .split(" ")
    .map((s) => s[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();
  return (
    <div
      className="flex shrink-0 items-center justify-center rounded-lg text-xs font-semibold text-white"
      style={{ width: size, height: size, background: w.colorAccent }}
      aria-hidden
    >
      {initials}
    </div>
  );
}

export function WorkspaceSwitcher() {
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState("");
  const current = useQuery({ queryKey: ["workspace", "current"], queryFn: () => workspaceService.current() });
  const all = useQuery({ queryKey: ["workspace", "all"], queryFn: () => workspaceService.list() });
  const recent = useQuery({ queryKey: ["workspace", "recent"], queryFn: () => workspaceService.recent() });

  useEffect(() => {
    const off = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.shiftKey && e.key.toLowerCase() === "o") {
        e.preventDefault();
        setOpen((v) => !v);
      }
    };
    window.addEventListener("keydown", off);
    return () => window.removeEventListener("keydown", off);
  }, []);

  const filtered = useMemo(() => {
    const list = all.data ?? [];
    if (!q) return list;
    const s = q.toLowerCase();
    return list.filter((w) => w.name.toLowerCase().includes(s) || w.organizationType.toLowerCase().includes(s));
  }, [all.data, q]);

  const favorites = (all.data ?? []).filter((w) => w.isFavorite);

  async function pick(w: Workspace) {
    await workspaceService.switchTo(w.id);
    eventBus.emit("workspace:switched", { workspaceId: w.id });
    await qc.invalidateQueries({ queryKey: ["workspace"] });
    setOpen(false);
  }
  async function star(w: Workspace, e: React.MouseEvent) {
    e.stopPropagation();
    await workspaceService.toggleFavorite(w.id);
    await qc.invalidateQueries({ queryKey: ["workspace"] });
  }

  const cur = current.data;

  return (
    <DropdownMenu open={open} onOpenChange={setOpen}>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" className="h-10 gap-2 px-2">
          {cur ? <Avatar w={cur} size={28} /> : <Building2 className="h-4 w-4" />}
          <div className="hidden text-left leading-tight md:block">
            <p className="text-xs font-medium text-muted-foreground">Workspace</p>
            <p className="max-w-[180px] truncate text-sm font-semibold">{cur?.name ?? "Select"}</p>
          </div>
          <ChevronDown className="h-4 w-4 text-muted-foreground" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start" className="w-80 p-0">
        <div className="p-2">
          <div className="relative">
            <Search className="pointer-events-none absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search workspaces…" className="pl-8" />
          </div>
        </div>
        {favorites.length > 0 && (
          <>
            <DropdownMenuLabel className="text-[11px] uppercase text-muted-foreground">Favorites</DropdownMenuLabel>
            <ScrollArea className="max-h-40">
              {favorites.map((w) => (
                <Row key={w.id} w={w} current={cur?.id === w.id} onPick={pick} onStar={star} />
              ))}
            </ScrollArea>
            <DropdownMenuSeparator />
          </>
        )}
        {(recent.data?.length ?? 0) > 0 && (
          <>
            <DropdownMenuLabel className="text-[11px] uppercase text-muted-foreground">Recent</DropdownMenuLabel>
            {(recent.data ?? []).slice(0, 4).map((w) => (
              <Row key={w.id} w={w} current={cur?.id === w.id} onPick={pick} onStar={star} />
            ))}
            <DropdownMenuSeparator />
          </>
        )}
        <DropdownMenuLabel className="text-[11px] uppercase text-muted-foreground">All workspaces</DropdownMenuLabel>
        <ScrollArea className="max-h-64">
          {filtered.map((w) => (
            <Row key={w.id} w={w} current={cur?.id === w.id} onPick={pick} onStar={star} />
          ))}
        </ScrollArea>
        <div className="border-t px-2 py-1.5 text-[11px] text-muted-foreground">
          Quick switch <kbd className="ml-1 rounded bg-muted px-1 py-0.5 font-mono text-[10px]">⌘⇧O</kbd>
        </div>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

function Row({
  w,
  current,
  onPick,
  onStar,
}: {
  w: Workspace;
  current: boolean;
  onPick: (w: Workspace) => void;
  onStar: (w: Workspace, e: React.MouseEvent) => void;
}) {
  return (
    <button
      type="button"
      onClick={() => onPick(w)}
      className={cn(
        "flex w-full items-center gap-3 px-3 py-2 text-left hover:bg-accent/60",
        current && "bg-accent",
      )}
    >
      <Avatar w={w} />
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium">{w.name}</p>
        <p className="truncate text-xs text-muted-foreground">
          {w.organizationType} · {w.memberCount} members
        </p>
      </div>
      <button
        type="button"
        onClick={(e) => onStar(w, e)}
        className="rounded p-1 text-muted-foreground hover:bg-background hover:text-foreground"
        aria-label={w.isFavorite ? "Remove favorite" : "Add favorite"}
      >
        {w.isFavorite ? <Star className="h-3.5 w-3.5 fill-current text-warning" /> : <StarOff className="h-3.5 w-3.5" />}
      </button>
      {current && <Check className="h-4 w-4 text-primary" />}
    </button>
  );
}
