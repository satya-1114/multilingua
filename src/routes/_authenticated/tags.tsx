import { useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, MoreHorizontal, Pencil, Trash2, Merge } from "lucide-react";
import { toast } from "sonner";
import { SectionHeader } from "@/components/common/section-header";
import { EmptyState } from "@/components/common/empty-state";
import { SkeletonBlock } from "@/components/common/skeleton-block";
import { PermissionGuard } from "@/components/common/permission-guard";
import { ConfirmDialog } from "@/components/common/confirm-dialog";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from "@/components/ui/dialog";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { tagService } from "@/services/tag.service";
import { PERMISSIONS } from "@/constants/rbac";
import type { AudienceTag } from "@/types/audience";

export const Route = createFileRoute("/_authenticated/tags")({
  head: () => ({ meta: [{ title: "Tags — Multilingua" }, { name: "robots", content: "noindex" }] }),
  component: TagsPage,
});

const COLORS = ["#2563EB", "#8B5CF6", "#22C55E", "#F59E0B", "#EC4899", "#0EA5E9", "#EF4444", "#14B8A6"];

function TagsPage() {
  const qc = useQueryClient();
  const tagsQuery = useQuery({ queryKey: ["tags"], queryFn: () => tagService.list() });
  const [editing, setEditing] = useState<AudienceTag | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [selected, setSelected] = useState<string[]>([]);
  const [mergeOpen, setMergeOpen] = useState(false);
  const [mergeTarget, setMergeTarget] = useState<string>("");
  const [deleteTarget, setDeleteTarget] = useState<AudienceTag | null>(null);

  const tags = tagsQuery.data ?? [];
  const invalidate = () => qc.invalidateQueries({ queryKey: ["tags"] });

  return (
    <div className="space-y-6">
      <SectionHeader
        title="Tags"
        description="Attach labels to contacts for flexible segmentation."
        actions={
          <PermissionGuard anyOf={[PERMISSIONS.TAG_MANAGE]}>
            <div className="flex gap-2">
              {selected.length >= 2 && (
                <Button size="sm" variant="outline" onClick={() => setMergeOpen(true)} className="gap-2">
                  <Merge className="h-4 w-4" /> Merge {selected.length}
                </Button>
              )}
              <Button size="sm" onClick={() => { setEditing(null); setDialogOpen(true); }} className="gap-2">
                <Plus className="h-4 w-4" /> New tag
              </Button>
            </div>
          </PermissionGuard>
        }
      />

      {tagsQuery.isLoading ? (
        <SkeletonBlock rows={5} />
      ) : tags.length === 0 ? (
        <EmptyState title="No tags yet" />
      ) : (
        <Card className="shadow-card">
          <CardContent className="p-0">
            <ul className="divide-y">
              {tags.map((t) => {
                const checked = selected.includes(t.id);
                return (
                  <li key={t.id} className="flex items-center gap-3 px-4 py-3 hover:bg-muted/30">
                    <PermissionGuard anyOf={[PERMISSIONS.TAG_MANAGE]}>
                      <Checkbox
                        checked={checked}
                        onCheckedChange={() => setSelected((s) => (s.includes(t.id) ? s.filter((v) => v !== t.id) : [...s, t.id]))}
                      />
                    </PermissionGuard>
                    <span className="h-3 w-3 rounded-full" style={{ background: t.color }} />
                    <span className="flex-1 text-sm font-medium">{t.name}</span>
                    <span className="text-xs text-muted-foreground">{t.audienceCount} contacts</span>
                    <PermissionGuard anyOf={[PERMISSIONS.TAG_MANAGE]}>
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="icon" className="h-8 w-8"><MoreHorizontal className="h-4 w-4" /></Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem onClick={() => { setEditing(t); setDialogOpen(true); }} className="gap-2">
                            <Pencil className="h-3.5 w-3.5" /> Edit
                          </DropdownMenuItem>
                          <DropdownMenuItem onClick={() => setDeleteTarget(t)} className="gap-2 text-destructive">
                            <Trash2 className="h-3.5 w-3.5" /> Delete
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </PermissionGuard>
                  </li>
                );
              })}
            </ul>
          </CardContent>
        </Card>
      )}

      <TagDialog open={dialogOpen} onOpenChange={setDialogOpen} initial={editing} onSaved={invalidate} />

      <Dialog open={mergeOpen} onOpenChange={setMergeOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Merge tags</DialogTitle>
            <DialogDescription>Choose the tag to keep. The others will be merged into it.</DialogDescription>
          </DialogHeader>
          <Select value={mergeTarget} onValueChange={setMergeTarget}>
            <SelectTrigger><SelectValue placeholder="Select target tag" /></SelectTrigger>
            <SelectContent>
              {tags.filter((t) => selected.includes(t.id)).map((t) => <SelectItem key={t.id} value={t.id}>{t.name}</SelectItem>)}
            </SelectContent>
          </Select>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setMergeOpen(false)}>Cancel</Button>
            <Button
              disabled={!mergeTarget}
              onClick={async () => {
                await tagService.merge(selected.filter((id) => id !== mergeTarget), mergeTarget);
                toast.success("Tags merged");
                setSelected([]); setMergeOpen(false); setMergeTarget(""); invalidate();
              }}
            >
              Merge
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <ConfirmDialog
        open={!!deleteTarget}
        onOpenChange={(o) => !o && setDeleteTarget(null)}
        title={`Delete ${deleteTarget?.name}?`}
        destructive
        confirmLabel="Delete"
        onConfirm={async () => {
          if (!deleteTarget) return;
          await tagService.remove(deleteTarget.id);
          toast.success("Tag deleted");
          setDeleteTarget(null); invalidate();
        }}
      />
    </div>
  );
}

function TagDialog({
  open, onOpenChange, initial, onSaved,
}: { open: boolean; onOpenChange: (v: boolean) => void; initial: AudienceTag | null; onSaved: () => void }) {
  const [name, setName] = useState(initial?.name ?? "");
  const [color, setColor] = useState(initial?.color ?? COLORS[0]!);
  const [saving, setSaving] = useState(false);

  const reset = () => { setName(initial?.name ?? ""); setColor(initial?.color ?? COLORS[0]!); };

  async function submit() {
    if (!name.trim()) return;
    setSaving(true);
    try {
      if (initial) await tagService.update(initial.id, { name, color });
      else await tagService.create({ name, color });
      toast.success(initial ? "Tag updated" : "Tag created");
      onSaved(); onOpenChange(false);
    } finally { setSaving(false); }
  }

  return (
    <Dialog open={open} onOpenChange={(v) => { onOpenChange(v); if (v) reset(); }}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{initial ? "Edit tag" : "Create tag"}</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <div>
            <Label>Name</Label>
            <Input value={name} onChange={(e) => setName(e.target.value)} className="mt-1.5" maxLength={40} />
          </div>
          <div>
            <Label>Color</Label>
            <div className="mt-1.5 flex flex-wrap gap-2">
              {COLORS.map((c) => (
                <button
                  key={c}
                  type="button"
                  onClick={() => setColor(c)}
                  className={`h-7 w-7 rounded-full ring-offset-2 ${color === c ? "ring-2 ring-primary" : ""}`}
                  style={{ background: c }}
                  aria-label={`Color ${c}`}
                />
              ))}
            </div>
          </div>
        </div>
        <DialogFooter>
          <Button variant="ghost" onClick={() => onOpenChange(false)}>Cancel</Button>
          <Button onClick={submit} disabled={saving || !name.trim()}>{initial ? "Save" : "Create"}</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
