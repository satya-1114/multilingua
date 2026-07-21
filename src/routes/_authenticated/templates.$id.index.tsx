import { useState } from "react";
import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { ArrowLeft, Copy, Edit3, Trash2, RotateCcw } from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import { SectionHeader } from "@/components/common/section-header";
import { SkeletonBlock } from "@/components/common/skeleton-block";
import { ErrorState } from "@/components/common/error-state";
import { ConfirmDialog } from "@/components/common/confirm-dialog";
import { PermissionGuard } from "@/components/common/permission-guard";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { templateService } from "@/services/template.service";
import { TEMPLATE_CATEGORY_META, interpolate, BUILTIN_VARIABLES } from "@/constants/template";
import { PERMISSIONS } from "@/constants/rbac";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/_authenticated/templates/$id/")({
  head: () => ({
    meta: [
      { title: "Template details — Multilingua" },
      { name: "robots", content: "noindex" },
    ],
  }),
  component: TemplateDetailPage,
});

function TemplateDetailPage() {
  const { id } = Route.useParams();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ["template", id], queryFn: () => templateService.get(id) });
  const [deleteOpen, setDeleteOpen] = useState(false);

  if (q.isLoading) return <SkeletonBlock rows={6} />;
  if (q.isError || !q.data) return <ErrorState onRetry={() => q.refetch()} />;
  const t = q.data;

  const preview: Record<string, string> = {};
  BUILTIN_VARIABLES.forEach((v) => { preview[v.key] = v.example ?? v.key; });
  t.variables.forEach((v) => { if (!preview[v.key]) preview[v.key] = v.example ?? `[${v.key}]`; });

  async function invalidate() {
    await qc.invalidateQueries({ queryKey: ["templates"] });
    await qc.invalidateQueries({ queryKey: ["template", id] });
  }

  return (
    <div className="space-y-6">
      <SectionHeader
        title={t.name}
        description={`${TEMPLATE_CATEGORY_META[t.category].label} · ${t.language.toUpperCase()} · v${t.version}`}
        actions={
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" size="sm" onClick={() => navigate({ to: "/templates" })} className="gap-1.5">
              <ArrowLeft className="h-4 w-4" /> Back
            </Button>
            <PermissionGuard anyOf={[PERMISSIONS.TEMPLATE_EDIT]}>
              <Button variant="outline" size="sm" onClick={() => navigate({ to: "/templates/$id/edit", params: { id } })} className="gap-1.5">
                <Edit3 className="h-4 w-4" /> Edit
              </Button>
            </PermissionGuard>
            <Button variant="outline" size="sm" className="gap-1.5" onClick={async () => {
              const dup = await templateService.duplicate(id);
              toast.success("Template duplicated");
              invalidate();
              navigate({ to: "/templates/$id", params: { id: dup.id } });
            }}>
              <Copy className="h-4 w-4" /> Duplicate
            </Button>
            <PermissionGuard anyOf={[PERMISSIONS.TEMPLATE_DELETE]}>
              <Button variant="destructive" size="sm" className="gap-1.5" onClick={() => setDeleteOpen(true)}>
                <Trash2 className="h-4 w-4" /> Delete
              </Button>
            </PermissionGuard>
          </div>
        }
      />

      <Tabs defaultValue="preview" className="space-y-4">
        <TabsList>
          <TabsTrigger value="preview">Preview</TabsTrigger>
          <TabsTrigger value="variables">Variables</TabsTrigger>
          <TabsTrigger value="versions">Version history</TabsTrigger>
        </TabsList>

        <TabsContent value="preview">
          <div className="grid gap-4 lg:grid-cols-2">
            <Card className="shadow-card">
              <CardHeader className="pb-2"><CardTitle className="text-base">Desktop</CardTitle></CardHeader>
              <CardContent>
                {t.subject && <p className="mb-2 font-semibold">{t.subject}</p>}
                <p className="whitespace-pre-line text-sm">{interpolate(t.body, preview)}</p>
              </CardContent>
            </Card>
            <Card className="shadow-card">
              <CardHeader className="pb-2"><CardTitle className="text-base">Mobile</CardTitle></CardHeader>
              <CardContent>
                <div className="mx-auto w-64 rounded-2xl border bg-background p-3 shadow-inner">
                  {t.subject && <p className="mb-1 text-sm font-semibold">{t.subject}</p>}
                  <p className="whitespace-pre-line text-xs">{interpolate(t.body, preview)}</p>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="variables">
          <Card className="shadow-card">
            <CardHeader className="pb-2"><CardTitle className="text-base">Variables</CardTitle></CardHeader>
            <CardContent>
              {t.variables.length === 0 ? (
                <p className="text-sm text-muted-foreground">No variables in this template.</p>
              ) : (
                <ul className="grid gap-2 sm:grid-cols-2">
                  {t.variables.map((v) => (
                    <li key={v.key} className="rounded-md border bg-card p-2 text-sm">
                      <p className="font-mono text-xs text-primary">{`{{${v.key}}}`}</p>
                      <p className="text-xs text-muted-foreground">{v.label}</p>
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="versions">
          <Card className="shadow-card">
            <CardHeader className="pb-2"><CardTitle className="text-base">Version history</CardTitle></CardHeader>
            <CardContent>
              <ul className="divide-y">
                {t.versions.map((v) => (
                  <li key={v.id} className={cn("flex flex-wrap items-center justify-between gap-2 py-3", v.version === t.version && "bg-primary/5 -mx-3 px-3 rounded-md")}>
                    <div>
                      <p className="text-sm font-medium">
                        Version {v.version} {v.version === t.version && <span className="ml-1 text-xs text-primary">Current</span>}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {v.authorName} · {formatDistanceToNow(new Date(v.createdAt), { addSuffix: true })}
                        {v.note && ` · ${v.note}`}
                      </p>
                    </div>
                    {v.version !== t.version && (
                      <Button size="sm" variant="outline" className="gap-1.5" onClick={async () => {
                        await templateService.restoreVersion(id, v.id);
                        toast.success(`Restored v${v.version}`);
                        invalidate();
                      }}>
                        <RotateCcw className="h-3.5 w-3.5" /> Restore
                      </Button>
                    )}
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      <ConfirmDialog
        open={deleteOpen}
        onOpenChange={setDeleteOpen}
        title="Delete template?"
        description="This template will be removed. Campaigns already using it retain their copy."
        destructive
        confirmLabel="Delete"
        onConfirm={async () => {
          await templateService.remove(id);
          toast.success("Template deleted");
          invalidate();
          navigate({ to: "/templates" });
        }}
      />
    </div>
  );
}
