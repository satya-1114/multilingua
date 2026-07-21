import { useEffect, useState } from "react";
import { FileText, Image as ImageIcon, Music, Video, Star, Upload, Search } from "lucide-react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { mediaService } from "@/services/media.service";
import { SkeletonBlock } from "@/components/common/skeleton-block";
import { EmptyState } from "@/components/common/empty-state";
import type { MediaAsset, MediaKind } from "@/types/media";
import { cn } from "@/lib/utils";

const KIND_ICON: Record<MediaKind, typeof FileText> = {
  document: FileText,
  image: ImageIcon,
  video: Video,
  audio: Music,
};

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSelect: (asset: MediaAsset) => void;
  title?: string;
}

export function MediaPicker({ open, onOpenChange, onSelect, title = "Select media" }: Props) {
  const qc = useQueryClient();
  const [search, setSearch] = useState("");
  const [favorites, setFavorites] = useState(false);
  const listQuery = useQuery({
    queryKey: ["media", { search, favorites }],
    queryFn: () => mediaService.list({ search, favorite: favorites || undefined }),
    enabled: open,
  });

  useEffect(() => {
    if (!open) {
      setSearch("");
      setFavorites(false);
    }
  }, [open]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl">
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription>
            Pick an asset from your media library or upload a new one.
          </DialogDescription>
        </DialogHeader>

        <div className="flex flex-wrap items-center gap-2">
          <div className="relative flex-1 min-w-[220px]">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search assets…"
              className="h-9 pl-9"
            />
          </div>
          <Button
            variant={favorites ? "default" : "outline"}
            size="sm"
            onClick={() => setFavorites((v) => !v)}
            className="gap-1.5"
          >
            <Star className="h-4 w-4" /> Favorites
          </Button>
          <label className="ml-auto">
            <input
              type="file"
              className="hidden"
              onChange={async (e) => {
                const file = e.target.files?.[0];
                if (!file) return;
                await mediaService.upload({ name: file.name, type: file.type, size: file.size });
                qc.invalidateQueries({ queryKey: ["media"] });
              }}
            />
            <Button variant="outline" size="sm" asChild>
              <span className="gap-1.5"><Upload className="h-4 w-4" /> Upload</span>
            </Button>
          </label>
        </div>

        <div className="max-h-[420px] overflow-y-auto">
          {listQuery.isLoading ? (
            <SkeletonBlock rows={4} />
          ) : (listQuery.data?.items.length ?? 0) === 0 ? (
            <EmptyState title="No media" description="Upload your first asset to reuse across campaigns." />
          ) : (
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 md:grid-cols-4">
              {listQuery.data!.items.map((m) => {
                const Icon = KIND_ICON[m.kind];
                return (
                  <button
                    type="button"
                    key={m.id}
                    onClick={() => {
                      onSelect(m);
                      onOpenChange(false);
                    }}
                    className={cn(
                      "group relative flex flex-col items-start gap-1 rounded-lg border bg-card p-3 text-left transition hover:border-primary hover:shadow-md",
                    )}
                  >
                    <div className="flex h-10 w-10 items-center justify-center rounded-md bg-muted text-muted-foreground">
                      <Icon className="h-5 w-5" />
                    </div>
                    <p className="line-clamp-2 text-xs font-medium text-foreground">{m.name}</p>
                    <p className="text-[10px] text-muted-foreground">
                      {(m.sizeBytes / 1024).toFixed(1)} KB · {m.kind}
                    </p>
                    {m.favorite && (
                      <Star className="absolute right-2 top-2 h-3.5 w-3.5 text-amber-500" fill="currentColor" />
                    )}
                  </button>
                );
              })}
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
