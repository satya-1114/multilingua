import { useMemo, useState } from "react";
import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  Copy,
  Eye,
  Globe,
  Pencil,
  QrCode,
  RefreshCw,
  Save,
  ShieldOff,
  Timer,
  
} from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import { toast } from "sonner";
import { SectionHeader } from "@/components/common/section-header";
import { ErrorState } from "@/components/common/error-state";
import { SkeletonBlock } from "@/components/common/skeleton-block";
import { EmptyState } from "@/components/common/empty-state";
import { PermissionGuard } from "@/components/common/permission-guard";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { publicAccessService } from "@/services/public-access.service";
import { PERMISSIONS } from "@/constants/rbac";
import { usePermissions } from "@/hooks/use-permissions";
import {
  QR_FORMATS,
  VISIBILITIES,
  type PublicResource,
  type PublicResourceUpdateInput,
  type QRCode,
  type QRFormat,
  type Visibility,
} from "@/types/public-access";

export const Route = createFileRoute("/_authenticated/public-resources/$id")({
  head: () => ({
    meta: [
      { title: "Public resource — Multilingua" },
      { name: "robots", content: "noindex" },
    ],
  }),
  component: PublicResourceDetail,
});

function PublicResourceDetail() {
  const { id } = Route.useParams();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const { hasPermission } = usePermissions();
  const canManage = hasPermission(PERMISSIONS.PUBLIC_MANAGE);
  const canManageQr = hasPermission(PERMISSIONS.QR_MANAGE) || canManage;

  const [editOpen, setEditOpen] = useState(false);
  const [slugOpen, setSlugOpen] = useState(false);
  const [qrCreateOpen, setQrCreateOpen] = useState(false);

  const resourceQ = useQuery({
    queryKey: ["public-resource", id],
    queryFn: () => publicAccessService.get(id),
  });
  const qrQ = useQuery({
    queryKey: ["public-resource", id, "qr"],
    queryFn: () => publicAccessService.listQr(id),
  });
  const viewsQ = useQuery({
    queryKey: ["public-resource", id, "views"],
    queryFn: () => publicAccessService.listViews(id, 50),
  });
  const summaryQ = useQuery({
    queryKey: ["public-resource", id, "views-summary"],
    queryFn: () => publicAccessService.viewsSummary(id),
  });

  const invalidateAll = () => {
    qc.invalidateQueries({ queryKey: ["public-resource", id] });
    qc.invalidateQueries({ queryKey: ["public-resources"] });
  };

  const publishMut = useMutation({
    mutationFn: () => publicAccessService.publish(id),
    onSuccess: () => { invalidateAll(); toast.success("Resource published"); },
    onError: (e: Error) => toast.error(e.message),
  });
  const unpublishMut = useMutation({
    mutationFn: (v: Visibility) => publicAccessService.unpublish(id, v),
    onSuccess: () => { invalidateAll(); toast.success("Resource unpublished"); },
    onError: (e: Error) => toast.error(e.message),
  });
  const expireMut = useMutation({
    mutationFn: () => publicAccessService.expire(id),
    onSuccess: () => { invalidateAll(); toast.success("Resource expired"); },
    onError: (e: Error) => toast.error(e.message),
  });
  const regenTokenMut = useMutation({
    mutationFn: () => publicAccessService.regenerateQrToken(id),
    onSuccess: () => { invalidateAll(); toast.success("QR token regenerated"); },
    onError: (e: Error) => toast.error(e.message),
  });

  if (resourceQ.isLoading) return <SkeletonBlock rows={10} />;
  if (resourceQ.isError || !resourceQ.data) {
    return (
      <ErrorState
        title="Could not load resource"
        description={(resourceQ.error as Error | undefined)?.message ?? "Unknown error"}
        onRetry={() => resourceQ.refetch()}
      />
    );
  }
  const r = resourceQ.data;

  return (
    <div className="space-y-6">
      <SectionHeader
        title={r.title}
        description={r.description ?? undefined}
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <Button variant="outline" size="sm" onClick={() => navigate({ to: "/public-resources" })}>
              <ArrowLeft className="mr-1.5 h-4 w-4" /> Back
            </Button>
            {canManage && (
              <>
                <Button size="sm" variant="outline" className="gap-1.5" onClick={() => setEditOpen(true)}>
                  <Pencil className="h-4 w-4" /> Edit
                </Button>
                {r.visibility === "public" || r.visibility === "unlisted" ? (
                  <Button size="sm" variant="outline" className="gap-1.5" onClick={() => unpublishMut.mutate("private")}>
                    <ShieldOff className="h-4 w-4" /> Unpublish
                  </Button>
                ) : (
                  <Button size="sm" className="gap-1.5" onClick={() => publishMut.mutate()}>
                    <Globe className="h-4 w-4" /> Publish
                  </Button>
                )}
                <Button size="sm" variant="outline" className="gap-1.5" onClick={() => expireMut.mutate()}>
                  <Timer className="h-4 w-4" /> Expire
                </Button>
              </>
            )}
          </div>
        }
      />

      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="shadow-card lg:col-span-2">
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Overview</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-4 text-sm">
            <Field label="Slug">
              <div className="flex items-center gap-2">
                <code className="rounded bg-muted px-2 py-1 text-xs">/p/{r.slug}</code>
                <CopyBtn value={`${window.location.origin}/p/${r.slug}`} label="Copy public URL" />
                {canManage && (
                  <Button size="sm" variant="ghost" onClick={() => setSlugOpen(true)}>
                    <RefreshCw className="mr-1 h-3 w-3" /> Change
                  </Button>
                )}
              </div>
            </Field>
            <Field label="QR token">
              <div className="flex items-center gap-2">
                {r.qrToken ? (
                  <>
                    <code className="rounded bg-muted px-2 py-1 text-xs">/q/{r.qrToken}</code>
                    <CopyBtn value={`${window.location.origin}/q/${r.qrToken}`} label="Copy QR URL" />
                  </>
                ) : (
                  <span className="text-muted-foreground">No QR token</span>
                )}
                {canManage && (
                  <Button size="sm" variant="ghost" onClick={() => regenTokenMut.mutate()} disabled={regenTokenMut.isPending}>
                    <RefreshCw className="mr-1 h-3 w-3" /> Regenerate
                  </Button>
                )}
              </div>
            </Field>
            <Field label="Visibility">
              <Badge variant="outline" className="capitalize">{r.visibility}</Badge>
            </Field>
            <Field label="Resource type">
              <span className="capitalize">{r.resourceType.replace(/_/g, " ")}</span>
            </Field>
            <Field label="Expires">
              <span className="text-muted-foreground">
                {r.expiresAt ? new Date(r.expiresAt).toLocaleString() : "Never"}
              </span>
            </Field>
            <Field label="Created">
              <span className="text-muted-foreground">
                {r.createdAt ? formatDistanceToNow(new Date(r.createdAt), { addSuffix: true }) : "—"}
              </span>
            </Field>
          </CardContent>
        </Card>

        <Card className="shadow-card">
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Views</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            {summaryQ.isLoading ? (
              <SkeletonBlock rows={3} />
            ) : summaryQ.isError ? (
              <ErrorState title="Could not load summary" onRetry={() => summaryQ.refetch()} />
            ) : (
              <>
                <div className="rounded-lg border p-3">
                  <p className="text-xs uppercase tracking-wide text-muted-foreground">Total views</p>
                  <p className="mt-1 text-2xl font-semibold">
                    {(summaryQ.data?.total as number | undefined) ?? 0}
                  </p>
                </div>
                <SummaryBreakdown title="By device" data={summaryQ.data?.byDevice} />
                <SummaryBreakdown title="By country" data={summaryQ.data?.byCountry} />
              </>
            )}
          </CardContent>
        </Card>
      </div>

      {/* QR metadata section */}
      <Card className="shadow-card">
        <CardHeader className="flex flex-row items-center justify-between pb-2">
          <CardTitle className="text-base flex items-center gap-2">
            <QrCode className="h-4 w-4" /> QR metadata
          </CardTitle>
          <PermissionGuard anyOf={[PERMISSIONS.QR_MANAGE, PERMISSIONS.PUBLIC_MANAGE]}>
            <Button size="sm" onClick={() => setQrCreateOpen(true)} className="gap-1.5">
              <QrCode className="h-4 w-4" /> Register metadata
            </Button>
          </PermissionGuard>
        </CardHeader>
        <CardContent>
          {qrQ.isLoading ? (
            <SkeletonBlock rows={4} />
          ) : qrQ.isError ? (
            <ErrorState
              title="Could not load QR metadata"
              description={(qrQ.error as Error).message}
              onRetry={() => qrQ.refetch()}
            />
          ) : (qrQ.data ?? []).length === 0 ? (
            <EmptyState
              icon={QrCode}
              title="No QR metadata"
              description="Register QR format/version entries to track versions of generated codes."
            />
          ) : (
            <QRList items={qrQ.data ?? []} resourceId={id} canManage={canManageQr} />
          )}
        </CardContent>
      </Card>

      {/* Recent views */}
      <Card className="shadow-card">
        <CardHeader className="pb-2">
          <CardTitle className="text-base flex items-center gap-2">
            <Eye className="h-4 w-4" /> Recent views
          </CardTitle>
        </CardHeader>
        <CardContent>
          {viewsQ.isLoading ? (
            <SkeletonBlock rows={4} />
          ) : viewsQ.isError ? (
            <ErrorState
              title="Could not load views"
              description={(viewsQ.error as Error).message}
              onRetry={() => viewsQ.refetch()}
            />
          ) : (viewsQ.data ?? []).length === 0 ? (
            <EmptyState
              icon={Eye}
              title="No views recorded yet"
              description="Anonymous views appear here once the resource is accessed."
            />
          ) : (
            <ul className="divide-y">
              {(viewsQ.data ?? []).map((v) => (
                <li key={v.id} className="flex items-center justify-between py-2 text-sm">
                  <span className="text-muted-foreground">
                    {formatDistanceToNow(new Date(v.viewedAt), { addSuffix: true })}
                  </span>
                  <div className="flex items-center gap-2 text-xs">
                    {v.country && <Badge variant="outline">{v.country}</Badge>}
                    {v.deviceType && <Badge variant="outline" className="capitalize">{v.deviceType}</Badge>}
                    {v.referrer && (
                      <span className="max-w-[280px] truncate text-muted-foreground" title={v.referrer}>
                        {v.referrer}
                      </span>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>

      <EditResourceDialog
        open={editOpen}
        onOpenChange={setEditOpen}
        resource={r}
        onSaved={() => { setEditOpen(false); invalidateAll(); }}
      />
      <RegenerateSlugDialog
        open={slugOpen}
        onOpenChange={setSlugOpen}
        resource={r}
        onSaved={() => { setSlugOpen(false); invalidateAll(); }}
      />
      <CreateQrDialog
        open={qrCreateOpen}
        onOpenChange={setQrCreateOpen}
        resourceId={id}
        onCreated={() => {
          setQrCreateOpen(false);
          qc.invalidateQueries({ queryKey: ["public-resource", id, "qr"] });
        }}
      />
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="grid grid-cols-[140px_1fr] items-start gap-3">
      <span className="text-xs uppercase tracking-wide text-muted-foreground">{label}</span>
      <div>{children}</div>
    </div>
  );
}

function CopyBtn({ value, label }: { value: string; label: string }) {
  return (
    <Button
      size="sm"
      variant="ghost"
      className="h-7 px-2"
      onClick={() => {
        navigator.clipboard.writeText(value).then(() => toast.success(`${label}`));
      }}
    >
      <Copy className="h-3 w-3" />
    </Button>
  );
}

function SummaryBreakdown({
  title,
  data,
}: {
  title: string;
  data?: unknown;
}) {
  const entries = useMemo(() => {
    if (!data || typeof data !== "object") return [];
    return Object.entries(data as Record<string, number>).sort((a, b) => b[1] - a[1]);
  }, [data]);
  if (entries.length === 0) return null;
  return (
    <div>
      <p className="mb-1 text-xs uppercase tracking-wide text-muted-foreground">{title}</p>
      <ul className="space-y-1">
        {entries.slice(0, 5).map(([k, v]) => (
          <li key={k} className="flex items-center justify-between">
            <span className="capitalize">{k || "unknown"}</span>
            <span className="text-muted-foreground">{v}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function QRList({
  items,
  resourceId,
  canManage,
}: {
  items: QRCode[];
  resourceId: string;
  canManage: boolean;
}) {
  const qc = useQueryClient();
  const invalidate = () =>
    qc.invalidateQueries({ queryKey: ["public-resource", resourceId, "qr"] });

  const activate = useMutation({
    mutationFn: (qrId: string) => publicAccessService.activateQr(qrId),
    onSuccess: () => { invalidate(); toast.success("QR activated"); },
    onError: (e: Error) => toast.error(e.message),
  });
  const deactivate = useMutation({
    mutationFn: (qrId: string) => publicAccessService.deactivateQr(qrId),
    onSuccess: () => { invalidate(); toast.success("QR deactivated"); },
    onError: (e: Error) => toast.error(e.message),
  });
  const regenerate = useMutation({
    mutationFn: (qrId: string) => publicAccessService.regenerateQr(qrId, {}),
    onSuccess: () => { invalidate(); toast.success("QR regenerated"); },
    onError: (e: Error) => toast.error(e.message),
  });

  return (
    <ul className="divide-y">
      {items.map((q) => (
        <li key={q.id} className="flex flex-wrap items-center justify-between gap-2 py-3 text-sm">
          <div className="flex items-center gap-2">
            <Badge variant="outline" className="uppercase">{q.format}</Badge>
            <span className="text-muted-foreground">v{q.version}</span>
            <Badge
              variant="outline"
              className={
                q.status === "active"
                  ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-200"
                  : q.status === "revoked" || q.status === "expired"
                  ? "bg-rose-100 text-rose-800 dark:bg-rose-900/40 dark:text-rose-200"
                  : "bg-muted text-muted-foreground"
              }
            >
              {q.status}
            </Badge>
          </div>
          {canManage && (
            <div className="flex items-center gap-1.5">
              {q.status !== "active" && (
                <Button size="sm" variant="outline" onClick={() => activate.mutate(q.id)} disabled={activate.isPending}>
                  Activate
                </Button>
              )}
              {q.status === "active" && (
                <Button size="sm" variant="outline" onClick={() => deactivate.mutate(q.id)} disabled={deactivate.isPending}>
                  Deactivate
                </Button>
              )}
              <Button size="sm" variant="ghost" onClick={() => regenerate.mutate(q.id)} disabled={regenerate.isPending}>
                <RefreshCw className="mr-1 h-3 w-3" /> Regenerate
              </Button>
            </div>
          )}
        </li>
      ))}
    </ul>
  );
}

function EditResourceDialog({
  open,
  onOpenChange,
  resource,
  onSaved,
}: {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  resource: PublicResource;
  onSaved: () => void;
}) {
  const [form, setForm] = useState<PublicResourceUpdateInput>({
    title: resource.title,
    description: resource.description ?? "",
    visibility: resource.visibility,
  });
  const update = useMutation({
    mutationFn: (patch: PublicResourceUpdateInput) =>
      publicAccessService.update(resource.id, patch),
    onSuccess: () => { toast.success("Resource updated"); onSaved(); },
    onError: (e: Error) => toast.error(e.message),
  });
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader><DialogTitle>Edit resource</DialogTitle></DialogHeader>
        <div className="grid gap-3">
          <div className="grid gap-1.5">
            <Label>Title</Label>
            <Input
              value={form.title ?? ""}
              onChange={(e) => setForm({ ...form, title: e.target.value })}
            />
          </div>
          <div className="grid gap-1.5">
            <Label>Description</Label>
            <Textarea
              rows={4}
              value={form.description ?? ""}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
            />
          </div>
          <div className="grid gap-1.5">
            <Label>Visibility</Label>
            <Select
              value={form.visibility}
              onValueChange={(v) => setForm({ ...form, visibility: v as Visibility })}
            >
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                {VISIBILITIES.map((v) => (
                  <SelectItem key={v} value={v} className="capitalize">{v}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button>
          <Button onClick={() => update.mutate(form)} disabled={update.isPending}>
            <Save className="mr-1.5 h-4 w-4" /> Save
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function RegenerateSlugDialog({
  open,
  onOpenChange,
  resource,
  onSaved,
}: {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  resource: PublicResource;
  onSaved: () => void;
}) {
  const [slug, setSlug] = useState(resource.slug);
  const mut = useMutation({
    mutationFn: () => publicAccessService.regenerateSlug(resource.id, slug.trim()),
    onSuccess: () => { toast.success("Slug updated"); onSaved(); },
    onError: (e: Error) => toast.error(e.message),
  });
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader><DialogTitle>Change slug</DialogTitle></DialogHeader>
        <div className="grid gap-2">
          <Label>New slug</Label>
          <Input
            value={slug}
            onChange={(e) => setSlug(e.target.value)}
            pattern="^[a-z0-9][a-z0-9\-]{0,118}[a-z0-9]$|^[a-z0-9]$"
          />
          <p className="text-xs text-muted-foreground">
            Existing links using the old slug will stop resolving.
          </p>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button>
          <Button onClick={() => mut.mutate()} disabled={mut.isPending || !slug.trim()}>
            <RefreshCw className="mr-1.5 h-4 w-4" /> Update
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function CreateQrDialog({
  open,
  onOpenChange,
  resourceId,
  onCreated,
}: {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  resourceId: string;
  onCreated: () => void;
}) {
  const [format, setFormat] = useState<QRFormat>("png");
  const [version, setVersion] = useState<number>(1);
  const mut = useMutation({
    mutationFn: () => publicAccessService.createQr(resourceId, { format, version }),
    onSuccess: () => { toast.success("QR metadata registered"); onCreated(); },
    onError: (e: Error) => toast.error(e.message),
  });
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader><DialogTitle>Register QR metadata</DialogTitle></DialogHeader>
        <div className="grid gap-3">
          <div className="grid gap-1.5">
            <Label>Format</Label>
            <Select value={format} onValueChange={(v) => setFormat(v as QRFormat)}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                {QR_FORMATS.map((f) => (
                  <SelectItem key={f} value={f} className="uppercase">{f}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="grid gap-1.5">
            <Label>Version</Label>
            <Input
              type="number"
              min={1}
              max={40}
              value={version}
              onChange={(e) => setVersion(Math.max(1, Math.min(40, Number(e.target.value) || 1)))}
            />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button>
          <Button onClick={() => mut.mutate()} disabled={mut.isPending}>Register</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

