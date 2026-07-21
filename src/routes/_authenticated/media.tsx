import { useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { FileText, Image as ImageIcon, Music, Star, Upload, Video, Trash2 } from "lucide-react";
import { SectionHeader } from "@/components/common/section-header";
import { DataTableToolbar } from "@/components/common/data-table-toolbar";
import { EmptyState } from "@/components/common/empty-state";
import { SkeletonBlock } from "@/components/common/skeleton-block";
import { ErrorState } from "@/components/common/error-state";
import { PermissionGuard } from "@/components/common/permission-guard";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { mediaService } from "@/services/media.service";
import { useDebouncedValue } from "@/hooks/use-debounced-value";
import { PERMISSIONS } from "@/constants/rbac";
import type { MediaKind } from "@/types/media";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/_authenticated/media")({
  head: () => ({
    meta: [
      { title: "Media library — Multilingua" },
      { name: "description", content: "Reusable media assets for your campaigns." },
      { name: "robots", content: "noindex" },
    ],
  }),
  component: MediaPage,
});

const KIND_ICON: Record<MediaKind, typeof FileText> = {
  document: FileText,
  image: ImageIcon,
  video: Video,
  audio: Music,
};

const KINDS: { key: MediaKind | "all"; label: string }[] = [
  { key: "all", label: "All" },
  { key: "document", label: "Documents" },
  { key: "image", label: "Images" },
  { key: "video", label: "Videos" },
  { key: "audio", label: "Audio" },
];

function MediaPage() {
  const qc = useQueryClient();
  const [search, setSearch] = useState("");
  const [kind, setKind] = useState<MediaKind | "all">("all");
  const [favoritesOnly, setFavoritesOnly] = useState(false);
  const debounced = useDebouncedValue(search, 250);

  const q = useQuery({
    queryKey: ["media", { search: debounced, kind, favoritesOnly }],
    queryFn: () => mediaService.list({
      search: debounced || undefined,
      kind: kind === "all" ? undefined : [kind],
      favorite: favoritesOnly || undefined,
      pageSize: 60,
    }),
  });

  async function onUpload(file: File) {
    await mediaService.upload({ name: file.name, type: file.type, size: file.size });
    toast.success(`Uploaded ${file.name}`);
    qc.invalidateQueries({ queryKey: ["media"] });
  }

  const items = q.data?.items ?? [];
  const totalSize = items.reduce((s, m) => s + m.sizeBytes, 0);

  return (
    <div className="space-y-6">
      <SectionHeader
        title="Media library"
        description="Reusable images, documents, and rich media across your campaigns."
        actions={
          <PermissionGuard anyOf={[PERMISSIONS.MEDIA_UPLOAD]}>
            <label>
              <input
                type="file"
                className="hidden"
                onChange={(e) => {
                  const f = e.target.files?.[0];
                  if (f) onUpload(f);
                  e.target.value = "";
                }}
              />
              <Button size="sm" asChild>
                <span className="gap-2"><Upload className="h-4 w-4" /> Upload</span>
              </Button>
            </label>
          </PermissionGuard>
        }
      />

      <Card className="shadow-card">
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-3">
          <CardTitle className="text-base">Library</CardTitle>
          <span className="text-xs text-muted-foreground">
            {items.length} assets · {(totalSize / 1024 / 1024).toFixed(2)} MB shown
          </span>
        </CardHeader>
        <CardContent className="space-y-4">
          <DataTableToolbar
            search={search}
            onSearchChange={setSearch}
            placeholder="Search files…"
            actions={
              <>
                <div className="flex items-center rounded-md border p-0.5">
                  {KINDS.map((k) => (
                    <button
                      key={k.key}
                      type="button"
                      onClick={() => setKind(k.key)}
                      className={cn(
                        "rounded px-2 py-1 text-xs font-medium transition-colors",
                        kind === k.key ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:text-foreground",
                      )}
                    >
                      {k.label}
                    </button>
                  ))}
                </div>
                <Button
                  variant={favoritesOnly ? "default" : "outline"}
                  size="sm"
                  onClick={() => setFavoritesOnly((v) => !v)}
                  className="gap-1.5"
                >
                  <Star className="h-4 w-4" /> Favorites
                </Button>
              </>
            }
          />

          {q.isError ? (
            <ErrorState onRetry={() => q.refetch()} />
          ) : q.isLoading ? (
            <SkeletonBlock rows={4} />
          ) : items.length === 0 ? (
            <EmptyState title="No files" description="Upload assets to reuse them across campaigns." />
          ) : (
            <div className="grid gap-3 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
              {items.map((m) => {
                const Icon = KIND_ICON[m.kind];
                return (
                  <div key={m.id} className="group relative rounded-xl border bg-card p-3 shadow-card transition-shadow hover:shadow-md">
                    <div className="flex h-24 items-center justify-center rounded-lg bg-muted text-muted-foreground">
                      <Icon className="h-8 w-8" />
                    </div>
                    <p className="mt-2 line-clamp-2 text-sm font-medium">{m.name}</p>
                    <p className="text-xs text-muted-foreground">
                      {(m.sizeBytes / 1024).toFixed(1)} KB · {m.kind}
                    </p>
                    <p className="mt-1 text-[11px] text-muted-foreground">By {m.uploadedByName}</p>
                    <div className="mt-2 flex items-center gap-1">
                      <Button
                        size="icon"
                        variant="ghost"
                        className="h-7 w-7"
                        aria-label={m.favorite ? "Unfavorite" : "Favorite"}
                        onClick={async () => {
                          await mediaService.toggleFavorite(m.id);
                          qc.invalidateQueries({ queryKey: ["media"] });
                        }}
                      >
                        <Star className={cn("h-3.5 w-3.5", m.favorite && "fill-amber-500 text-amber-500")} />
                      </Button>
                      <PermissionGuard anyOf={[PERMISSIONS.MEDIA_DELETE]}>
                        <Button
                          size="icon"
                          variant="ghost"
                          className="h-7 w-7 text-muted-foreground hover:text-destructive"
                          aria-label="Delete"
                          onClick={async () => {
                            await mediaService.remove(m.id);
                            toast.success("File deleted");
                            qc.invalidateQueries({ queryKey: ["media"] });
                          }}
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </Button>
                      </PermissionGuard>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
