import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { useMemo, useState } from "react";
import {
  Pencil,
  CheckCircle2,
  PlayCircle,
  Users,
  ShieldCheck,
  PackageOpen,
  RotateCcw,
  XCircle,
  Paperclip,
  Trash2,
  Plus,
} from "lucide-react";
import { formatDistanceToNow } from "date-fns";

import { SectionHeader } from "@/components/common/section-header";
import { SkeletonBlock } from "@/components/common/skeleton-block";
import { ErrorState } from "@/components/common/error-state";
import { EmptyState } from "@/components/common/empty-state";
import { AnalyticsCard } from "@/components/common/analytics-card";
import { PermissionGuard } from "@/components/common/permission-guard";
import {
  DisasterSeverityBadge,
  DisasterStatusBadge,
  DisasterTypeBadge,
  AssignmentStatusBadge,
} from "@/components/common/disaster-badges";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
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
  DialogTrigger,
} from "@/components/ui/dialog";
import { disasterService } from "@/services/disaster.service";
import { volunteerService } from "@/services/volunteer.service";
import { PERMISSIONS } from "@/constants/rbac";
import {
  ATTACHMENT_KINDS,
  ASSIGNMENT_STATUSES,
  type AssignmentStatus,
  type AttachmentCreateInput,
  type AttachmentKind,
  type DisasterAssignment,
  type DisasterAttachment,
} from "@/types/disaster";

export const Route = createFileRoute("/_authenticated/disasters/$id/")({
  head: () => ({
    meta: [
      { title: "Disaster — Multilingua" },
      { name: "robots", content: "noindex" },
    ],
  }),
  component: DisasterDetailPage,
});

function DisasterDetailPage() {
  const { id } = Route.useParams();
  const qc = useQueryClient();

  const q = useQuery({ queryKey: ["disaster", id], queryFn: () => disasterService.get(id) });
  const assignmentsQ = useQuery({
    queryKey: ["disaster", id, "assignments"],
    queryFn: () => disasterService.assignments(id),
    enabled: !!q.data,
  });
  const attachmentsQ = useQuery({
    queryKey: ["disaster", id, "attachments"],
    queryFn: () => disasterService.attachments(id),
    enabled: !!q.data,
  });

  function invalidateDetail() {
    qc.invalidateQueries({ queryKey: ["disaster", id] });
    qc.invalidateQueries({ queryKey: ["disasters"] });
  }
  function invalidateAssignments() {
    qc.invalidateQueries({ queryKey: ["disaster", id, "assignments"] });
  }
  function invalidateAttachments() {
    qc.invalidateQueries({ queryKey: ["disaster", id, "attachments"] });
  }

  const verifyM = useMutation({
    mutationFn: () => disasterService.verify(id),
    onSuccess: () => { invalidateDetail(); toast.success("Disaster verified"); },
    onError: (e: Error) => toast.error(e.message),
  });
  const activateM = useMutation({
    mutationFn: () => disasterService.activate(id),
    onSuccess: () => { invalidateDetail(); toast.success("Disaster activated"); },
    onError: (e: Error) => toast.error(e.message),
  });
  const containM = useMutation({
    mutationFn: () => disasterService.contain(id),
    onSuccess: () => { invalidateDetail(); toast.success("Marked as contained"); },
    onError: (e: Error) => toast.error(e.message),
  });
  const resolveM = useMutation({
    mutationFn: () => disasterService.resolve(id),
    onSuccess: () => { invalidateDetail(); toast.success("Marked as resolved"); },
    onError: (e: Error) => toast.error(e.message),
  });
  const closeM = useMutation({
    mutationFn: () => disasterService.close(id),
    onSuccess: () => { invalidateDetail(); toast.success("Disaster closed"); },
    onError: (e: Error) => toast.error(e.message),
  });
  const reopenM = useMutation({
    mutationFn: () => disasterService.reopen(id),
    onSuccess: () => { invalidateDetail(); toast.success("Disaster reopened"); },
    onError: (e: Error) => toast.error(e.message),
  });

  if (q.isLoading) return <SkeletonBlock rows={12} />;
  if (q.isError || !q.data)
    return <ErrorState title="Disaster not found" onRetry={() => q.refetch()} />;

  const d = q.data;
  const assignments = assignmentsQ.data ?? [];
  const attachments = attachmentsQ.data ?? [];
  const activeAssignments = assignments.filter((a) => a.status !== "cancelled" && a.status !== "completed").length;

  return (
    <div className="space-y-6">
      <SectionHeader
        title={d.title}
        description={d.description ?? undefined}
        actions={
          <PermissionGuard anyOf={[PERMISSIONS.DISASTER_MANAGE]}>
            <div className="flex flex-wrap gap-2">
              {d.status === "reported" && (
                <Button size="sm" className="gap-1.5" onClick={() => verifyM.mutate()}>
                  <ShieldCheck className="h-4 w-4" /> Verify
                </Button>
              )}
              {(d.status === "verified" || d.status === "contained") && (
                <Button size="sm" className="gap-1.5" onClick={() => activateM.mutate()}>
                  <PlayCircle className="h-4 w-4" /> Activate
                </Button>
              )}
              {d.status === "active" && (
                <Button size="sm" variant="outline" className="gap-1.5" onClick={() => containM.mutate()}>
                  <PackageOpen className="h-4 w-4" /> Contain
                </Button>
              )}
              {(d.status === "active" || d.status === "contained") && (
                <Button size="sm" variant="outline" className="gap-1.5" onClick={() => resolveM.mutate()}>
                  <CheckCircle2 className="h-4 w-4" /> Resolve
                </Button>
              )}
              {d.status === "resolved" && (
                <Button size="sm" variant="outline" className="gap-1.5" onClick={() => closeM.mutate()}>
                  <XCircle className="h-4 w-4" /> Close
                </Button>
              )}
              {d.status === "closed" && (
                <Button size="sm" variant="outline" className="gap-1.5" onClick={() => reopenM.mutate()}>
                  <RotateCcw className="h-4 w-4" /> Reopen
                </Button>
              )}
              <Button asChild size="sm" variant="outline" className="gap-1.5">
                <Link to="/disasters/$id/edit" params={{ id }}>
                  <Pencil className="h-4 w-4" /> Edit
                </Link>
              </Button>
            </div>
          </PermissionGuard>
        }
      />

      <div className="flex flex-wrap items-center gap-2">
        <DisasterStatusBadge status={d.status} />
        <DisasterSeverityBadge severity={d.severity} />
        <DisasterTypeBadge type={d.disasterType} />
      </div>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <AnalyticsCard label="Active assignments" value={activeAssignments} icon={Users} />
        <AnalyticsCard label="Total assignments" value={assignments.length} />
        <AnalyticsCard label="Attachments" value={attachments.length} icon={Paperclip} />
        <AnalyticsCard
          label="Started"
          value={d.startedAt ? formatDistanceToNow(new Date(d.startedAt), { addSuffix: true }) : "—"}
        />
      </div>

      <Tabs defaultValue="overview">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="assignments">Assignments</TabsTrigger>
          <TabsTrigger value="attachments">Attachments</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-4">
          <Card className="shadow-card">
            <CardHeader className="pb-2"><CardTitle className="text-base">Location</CardTitle></CardHeader>
            <CardContent className="grid gap-2 text-sm md:grid-cols-2">
              <Row label="Address" value={d.address} />
              <Row label="City" value={d.city} />
              <Row label="District" value={d.district} />
              <Row label="State" value={d.state} />
              <Row label="Country" value={d.country} />
              <Row label="Postal code" value={d.postalCode} />
              {(d.latitude != null || d.longitude != null) && (
                <Row
                  label="Coordinates"
                  value={`${d.latitude ?? "—"}, ${d.longitude ?? "—"}`}
                />
              )}
            </CardContent>
          </Card>

          <Card className="shadow-card">
            <CardHeader className="pb-2"><CardTitle className="text-base">Timeline</CardTitle></CardHeader>
            <CardContent className="grid gap-2 text-sm md:grid-cols-2">
              <Row label="Started" value={d.startedAt ? new Date(d.startedAt).toLocaleString() : "—"} />
              <Row label="Resolved" value={d.resolvedAt ? new Date(d.resolvedAt).toLocaleString() : "—"} />
              <Row label="Created" value={new Date(d.createdAt).toLocaleString()} />
              <Row label="Updated" value={new Date(d.updatedAt).toLocaleString()} />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="assignments">
          <AssignmentsTab
            disasterId={id}
            assignments={assignments}
            loading={assignmentsQ.isLoading}
            onChanged={() => { invalidateAssignments(); invalidateDetail(); }}
          />
        </TabsContent>

        <TabsContent value="attachments">
          <AttachmentsTab
            disasterId={id}
            attachments={attachments}
            loading={attachmentsQ.isLoading}
            onChanged={invalidateAttachments}
          />
        </TabsContent>
      </Tabs>
    </div>
  );
}

function Row({ label, value }: { label: string; value?: string | null }) {
  return (
    <div>
      <p className="text-xs uppercase tracking-wide text-muted-foreground">{label}</p>
      <p className="text-sm text-foreground">{value || "—"}</p>
    </div>
  );
}

// ─────────────────────────── Assignments ────────────────────────────────────

function AssignmentsTab({
  disasterId,
  assignments,
  loading,
  onChanged,
}: {
  disasterId: string;
  assignments: DisasterAssignment[];
  loading: boolean;
  onChanged: () => void;
}) {
  const [assignOpen, setAssignOpen] = useState(false);
  const [reassignFor, setReassignFor] = useState<DisasterAssignment | null>(null);

  const assignM = useMutation({
    mutationFn: (payload: { volunteerId: string; role?: string; notes?: string }) =>
      disasterService.assignVolunteer(disasterId, payload),
    onSuccess: () => { onChanged(); setAssignOpen(false); toast.success("Volunteer assigned"); },
    onError: (e: Error) => toast.error(e.message),
  });
  const reassignM = useMutation({
    mutationFn: ({ assignmentId, volunteerId }: { assignmentId: string; volunteerId: string }) =>
      disasterService.reassignAssignment(assignmentId, volunteerId),
    onSuccess: () => { onChanged(); setReassignFor(null); toast.success("Reassigned"); },
    onError: (e: Error) => toast.error(e.message),
  });
  const statusM = useMutation({
    mutationFn: ({ assignmentId, status }: { assignmentId: string; status: AssignmentStatus }) =>
      disasterService.setAssignmentStatus(assignmentId, status),
    onSuccess: () => { onChanged(); toast.success("Status updated"); },
    onError: (e: Error) => toast.error(e.message),
  });
  const cancelM = useMutation({
    mutationFn: (assignmentId: string) => disasterService.cancelAssignment(assignmentId),
    onSuccess: () => { onChanged(); toast.success("Assignment cancelled"); },
    onError: (e: Error) => toast.error(e.message),
  });

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">{assignments.length} total</p>
        <PermissionGuard anyOf={[PERMISSIONS.DISASTER_ASSIGN]}>
          <Dialog open={assignOpen} onOpenChange={setAssignOpen}>
            <DialogTrigger asChild>
              <Button size="sm" className="gap-1.5">
                <Plus className="h-4 w-4" /> Assign volunteer
              </Button>
            </DialogTrigger>
            <AssignDialog onSubmit={(p) => assignM.mutate(p)} submitting={assignM.isPending} />
          </Dialog>
        </PermissionGuard>
      </div>

      {loading ? (
        <SkeletonBlock rows={4} />
      ) : assignments.length === 0 ? (
        <EmptyState
          icon={Users}
          title="No assignments"
          description="Assign volunteers to coordinate this disaster response."
        />
      ) : (
        <Card className="shadow-card">
          <CardContent className="divide-y p-0">
            {assignments.map((a) => (
              <div key={a.id} className="flex flex-wrap items-center justify-between gap-3 p-4">
                <div>
                  <Link
                    to="/volunteers/$id"
                    params={{ id: a.volunteerId }}
                    className="font-medium text-foreground hover:underline"
                  >
                    {a.volunteerName ?? `Volunteer ${a.volunteerId.slice(0, 8)}`}
                  </Link>
                  <p className="text-xs text-muted-foreground">
                    {a.role ?? "Responder"}
                    {a.assignedAt && (
                      <> · assigned {formatDistanceToNow(new Date(a.assignedAt), { addSuffix: true })}</>
                    )}
                  </p>
                  {a.notes && <p className="mt-1 text-xs text-muted-foreground">{a.notes}</p>}
                </div>
                <div className="flex items-center gap-2">
                  <AssignmentStatusBadge status={a.status} />
                  <PermissionGuard anyOf={[PERMISSIONS.DISASTER_ASSIGN]}>
                    <Select
                      value={a.status}
                      onValueChange={(v) =>
                        statusM.mutate({ assignmentId: a.id, status: v as AssignmentStatus })
                      }
                    >
                      <SelectTrigger className="h-8 w-[140px]"><SelectValue /></SelectTrigger>
                      <SelectContent>
                        {ASSIGNMENT_STATUSES.map((s) => (
                          <SelectItem key={s} value={s} className="capitalize">
                            {s.replace(/_/g, " ")}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <Button size="sm" variant="ghost" onClick={() => setReassignFor(a)}>
                      Reassign
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      className="text-destructive"
                      onClick={() => cancelM.mutate(a.id)}
                    >
                      Cancel
                    </Button>
                  </PermissionGuard>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      <Dialog open={!!reassignFor} onOpenChange={(o) => !o && setReassignFor(null)}>
        {reassignFor && (
          <ReassignDialog
            current={reassignFor}
            submitting={reassignM.isPending}
            onSubmit={(volunteerId) =>
              reassignM.mutate({ assignmentId: reassignFor.id, volunteerId })
            }
          />
        )}
      </Dialog>
    </div>
  );
}

function AssignDialog({
  onSubmit,
  submitting,
}: {
  onSubmit: (payload: { volunteerId: string; role?: string; notes?: string }) => void;
  submitting: boolean;
}) {
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState<string>("");
  const [role, setRole] = useState("");
  const [notes, setNotes] = useState("");
  const listQ = useQuery({
    queryKey: ["volunteers", "picker", search],
    queryFn: () => volunteerService.list({ search: search || undefined, status: "available", pageSize: 20 }),
  });
  const items = listQ.data?.items ?? [];

  return (
    <DialogContent className="max-w-lg">
      <DialogHeader><DialogTitle>Assign volunteer</DialogTitle></DialogHeader>
      <div className="space-y-3">
        <Input
          placeholder="Search available volunteers…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <div className="max-h-56 overflow-y-auto rounded border">
          {items.length === 0 ? (
            <p className="p-3 text-sm text-muted-foreground">No matching volunteers.</p>
          ) : (
            <ul className="divide-y text-sm">
              {items.map((v) => (
                <li
                  key={v.id}
                  className={`cursor-pointer px-3 py-2 hover:bg-muted ${selected === v.id ? "bg-muted" : ""}`}
                  onClick={() => setSelected(v.id)}
                >
                  <p className="font-medium text-foreground">{v.fullName}</p>
                  <p className="text-xs text-muted-foreground">{v.email}</p>
                </li>
              ))}
            </ul>
          )}
        </div>
        <div>
          <Label htmlFor="role">Role (optional)</Label>
          <Input id="role" value={role} onChange={(e) => setRole(e.target.value)} />
        </div>
        <div>
          <Label htmlFor="notes">Notes (optional)</Label>
          <Textarea id="notes" rows={2} value={notes} onChange={(e) => setNotes(e.target.value)} />
        </div>
      </div>
      <DialogFooter>
        <Button
          disabled={!selected || submitting}
          onClick={() => onSubmit({ volunteerId: selected, role: role || undefined, notes: notes || undefined })}
        >
          Assign
        </Button>
      </DialogFooter>
    </DialogContent>
  );
}

function ReassignDialog({
  current,
  onSubmit,
  submitting,
}: {
  current: DisasterAssignment;
  onSubmit: (volunteerId: string) => void;
  submitting: boolean;
}) {
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState<string>("");
  const listQ = useQuery({
    queryKey: ["volunteers", "picker", search],
    queryFn: () => volunteerService.list({ search: search || undefined, status: "available", pageSize: 20 }),
  });
  const items = useMemo(
    () => (listQ.data?.items ?? []).filter((v) => v.id !== current.volunteerId),
    [listQ.data, current.volunteerId],
  );
  return (
    <DialogContent className="max-w-lg">
      <DialogHeader><DialogTitle>Reassign to another volunteer</DialogTitle></DialogHeader>
      <div className="space-y-3">
        <Input placeholder="Search…" value={search} onChange={(e) => setSearch(e.target.value)} />
        <div className="max-h-56 overflow-y-auto rounded border">
          {items.length === 0 ? (
            <p className="p-3 text-sm text-muted-foreground">No matching volunteers.</p>
          ) : (
            <ul className="divide-y text-sm">
              {items.map((v) => (
                <li
                  key={v.id}
                  className={`cursor-pointer px-3 py-2 hover:bg-muted ${selected === v.id ? "bg-muted" : ""}`}
                  onClick={() => setSelected(v.id)}
                >
                  <p className="font-medium text-foreground">{v.fullName}</p>
                  <p className="text-xs text-muted-foreground">{v.email}</p>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
      <DialogFooter>
        <Button disabled={!selected || submitting} onClick={() => onSubmit(selected)}>
          Reassign
        </Button>
      </DialogFooter>
    </DialogContent>
  );
}

// ─────────────────────────── Attachments ────────────────────────────────────

function AttachmentsTab({
  disasterId,
  attachments,
  loading,
  onChanged,
}: {
  disasterId: string;
  attachments: DisasterAttachment[];
  loading: boolean;
  onChanged: () => void;
}) {
  const [open, setOpen] = useState(false);

  const registerM = useMutation({
    mutationFn: (payload: AttachmentCreateInput) =>
      disasterService.registerAttachment(disasterId, payload),
    onSuccess: () => { onChanged(); setOpen(false); toast.success("Attachment registered"); },
    onError: (e: Error) => toast.error(e.message),
  });
  const deleteM = useMutation({
    mutationFn: (attachmentId: string) => disasterService.deleteAttachment(attachmentId),
    onSuccess: () => { onChanged(); toast.success("Attachment removed"); },
    onError: (e: Error) => toast.error(e.message),
  });

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">{attachments.length} total</p>
        <PermissionGuard anyOf={[PERMISSIONS.DISASTER_MANAGE]}>
          <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild>
              <Button size="sm" className="gap-1.5">
                <Plus className="h-4 w-4" /> Register attachment
              </Button>
            </DialogTrigger>
            <RegisterAttachmentDialog
              submitting={registerM.isPending}
              onSubmit={(p) => registerM.mutate(p)}
            />
          </Dialog>
        </PermissionGuard>
      </div>
      <p className="text-xs text-muted-foreground">
        Upload storage is not part of this milestone. Register metadata for files hosted elsewhere.
      </p>

      {loading ? (
        <SkeletonBlock rows={3} />
      ) : attachments.length === 0 ? (
        <EmptyState
          icon={Paperclip}
          title="No attachments"
          description="Register file metadata to link evidence to this disaster."
        />
      ) : (
        <Card className="shadow-card">
          <CardContent className="divide-y p-0">
            {attachments.map((a) => (
              <div key={a.id} className="flex items-center justify-between gap-3 p-4">
                <div className="min-w-0">
                  <a
                    href={a.fileUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="font-medium text-foreground hover:underline"
                  >
                    {a.fileName}
                  </a>
                  <p className="text-xs text-muted-foreground capitalize">
                    {a.kind}
                    {a.contentType ? ` · ${a.contentType}` : ""}
                    {a.sizeBytes ? ` · ${Math.round(a.sizeBytes / 1024)} KB` : ""}
                  </p>
                  {a.caption && <p className="mt-1 text-xs text-muted-foreground">{a.caption}</p>}
                </div>
                <PermissionGuard anyOf={[PERMISSIONS.DISASTER_MANAGE]}>
                  <Button
                    size="sm"
                    variant="ghost"
                    className="text-destructive"
                    onClick={() => deleteM.mutate(a.id)}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </PermissionGuard>
              </div>
            ))}
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function RegisterAttachmentDialog({
  onSubmit,
  submitting,
}: {
  onSubmit: (payload: AttachmentCreateInput) => void;
  submitting: boolean;
}) {
  const [fileName, setFileName] = useState("");
  const [fileUrl, setFileUrl] = useState("");
  const [kind, setKind] = useState<AttachmentKind>("document");
  const [caption, setCaption] = useState("");
  return (
    <DialogContent className="max-w-lg">
      <DialogHeader><DialogTitle>Register attachment</DialogTitle></DialogHeader>
      <div className="space-y-3">
        <div>
          <Label>Kind</Label>
          <Select value={kind} onValueChange={(v) => setKind(v as AttachmentKind)}>
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>
              {ATTACHMENT_KINDS.map((k) => (
                <SelectItem key={k} value={k} className="capitalize">{k}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div>
          <Label htmlFor="fileName">File name</Label>
          <Input id="fileName" value={fileName} onChange={(e) => setFileName(e.target.value)} />
        </div>
        <div>
          <Label htmlFor="fileUrl">File URL</Label>
          <Input id="fileUrl" value={fileUrl} onChange={(e) => setFileUrl(e.target.value)} placeholder="https://…" />
        </div>
        <div>
          <Label htmlFor="caption">Caption (optional)</Label>
          <Textarea id="caption" rows={2} value={caption} onChange={(e) => setCaption(e.target.value)} />
        </div>
      </div>
      <DialogFooter>
        <Button
          disabled={!fileName || !fileUrl || submitting}
          onClick={() => onSubmit({ fileName, fileUrl, kind, caption: caption || undefined })}
        >
          Register
        </Button>
      </DialogFooter>
    </DialogContent>
  );
}
