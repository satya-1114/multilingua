import { useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { Plus, MoreHorizontal, Users, Pencil, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { SectionHeader } from "@/components/common/section-header";
import { EmptyState } from "@/components/common/empty-state";
import { SkeletonBlock } from "@/components/common/skeleton-block";
import { PermissionGuard } from "@/components/common/permission-guard";
import { ConfirmDialog } from "@/components/common/confirm-dialog";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/components/ui/dialog";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { groupService } from "@/services/tag.service";
import { PERMISSIONS } from "@/constants/rbac";
import type { AudienceGroup } from "@/types/audience";

export const Route = createFileRoute("/_authenticated/audience-groups")({
  head: () => ({ meta: [{ title: "Audience groups — Multilingua" }, { name: "robots", content: "noindex" }] }),
  component: AudienceGroupsPage,
});

const COLORS = ["#2563EB", "#8B5CF6", "#22C55E", "#F59E0B", "#EC4899", "#0EA5E9", "#EF4444"];

function AudienceGroupsPage() {
  const qc = useQueryClient();
  const groupsQuery = useQuery({ queryKey: ["groups"], queryFn: () => groupService.list() });
  const [editing, setEditing] = useState<AudienceGroup | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<AudienceGroup | null>(null);

  function invalidate() { qc.invalidateQueries({ queryKey: ["groups"] }); }

  return (
    <div className="space-y-6">
      <SectionHeader
        title="Audience groups"
        description="Organize contacts into groups for faster campaign targeting."
        actions={
          <PermissionGuard anyOf={[PERMISSIONS.GROUP_MANAGE]}>
            <Button size="sm" onClick={() => { setEditing(null); setDialogOpen(true); }} className="gap-2">
              <Plus className="h-4 w-4" /> New group
            </Button>
          </PermissionGuard>
        }
      />

      {groupsQuery.isLoading ? (
        <SkeletonBlock rows={6} />
      ) : (groupsQuery.data ?? []).length === 0 ? (
        <EmptyState title="No groups yet" description="Create your first group to segment audiences." />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {(groupsQuery.data ?? []).map((g, i) => (
            <motion.div key={g.id} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.03 }}>
              <Card className="shadow-card p-5">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3 min-w-0">
                    <div className="flex h-10 w-10 items-center justify-center rounded-xl" style={{ background: `${g.color}20`, color: g.color }}>
                      <Users className="h-5 w-5" />
                    </div>
                    <div className="min-w-0">
                      <p className="truncate font-semibold text-sm">{g.name}</p>
                      <p className="text-xs text-muted-foreground">{g.memberCount.toLocaleString()} members</p>
                    </div>
                  </div>
                  <PermissionGuard anyOf={[PERMISSIONS.GROUP_MANAGE]}>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="ghost" size="icon" className="h-8 w-8"><MoreHorizontal className="h-4 w-4" /></Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem onClick={() => { setEditing(g); setDialogOpen(true); }} className="gap-2">
                          <Pencil className="h-3.5 w-3.5" /> Edit
                        </DropdownMenuItem>
                        <DropdownMenuItem onClick={() => setDeleteTarget(g)} className="gap-2 text-destructive">
                          <Trash2 className="h-3.5 w-3.5" /> Delete
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </PermissionGuard>
                </div>
                {g.description && <p className="mt-3 text-xs text-muted-foreground line-clamp-2">{g.description}</p>}
              </Card>
            </motion.div>
          ))}
        </div>
      )}

      <GroupDialog open={dialogOpen} onOpenChange={setDialogOpen} initial={editing} onSaved={invalidate} />
      <ConfirmDialog
        open={!!deleteTarget}
        onOpenChange={(o) => !o && setDeleteTarget(null)}
        title={`Delete ${deleteTarget?.name}?`}
        description="This does not delete member contacts."
        destructive
        confirmLabel="Delete"
        onConfirm={async () => {
          if (!deleteTarget) return;
          await groupService.remove(deleteTarget.id);
          toast.success("Group deleted");
          setDeleteTarget(null);
          invalidate();
        }}
      />
    </div>
  );
}

function GroupDialog({
  open, onOpenChange, initial, onSaved,
}: { open: boolean; onOpenChange: (v: boolean) => void; initial: AudienceGroup | null; onSaved: () => void }) {
  const [name, setName] = useState(initial?.name ?? "");
  const [description, setDescription] = useState(initial?.description ?? "");
  const [color, setColor] = useState(initial?.color ?? COLORS[0]!);
  const [saving, setSaving] = useState(false);

  const reset = () => { setName(initial?.name ?? ""); setDescription(initial?.description ?? ""); setColor(initial?.color ?? COLORS[0]!); };

  async function submit() {
    if (!name.trim()) return;
    setSaving(true);
    try {
      if (initial) await groupService.update(initial.id, { name, description, color });
      else await groupService.create({ name, description, color });
      toast.success(initial ? "Group updated" : "Group created");
      onSaved(); onOpenChange(false);
    } finally { setSaving(false); }
  }

  return (
    <Dialog open={open} onOpenChange={(v) => { onOpenChange(v); if (v) reset(); }}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{initial ? "Edit group" : "Create group"}</DialogTitle>
          <DialogDescription>Groups let you target audiences quickly during campaign setup.</DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <div>
            <Label>Name</Label>
            <Input value={name} onChange={(e) => setName(e.target.value)} className="mt-1.5" maxLength={80} />
          </div>
          <div>
            <Label>Description</Label>
            <Textarea value={description} onChange={(e) => setDescription(e.target.value)} className="mt-1.5" rows={2} maxLength={200} />
          </div>
          <div>
            <Label>Color</Label>
            <div className="mt-1.5 flex gap-2">
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
