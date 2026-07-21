import { useMemo, useState } from "react";
import { createFileRoute, Link } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { ArrowUpDown, HeartHandshake, Plus, Search } from "lucide-react";
import { SectionHeader } from "@/components/common/section-header";
import { EmptyState } from "@/components/common/empty-state";
import { ErrorState } from "@/components/common/error-state";
import { SkeletonBlock } from "@/components/common/skeleton-block";
import { StatusBadge } from "@/components/common/status-badge";
import { DataTable, type DataTableColumn } from "@/components/common/data-table";
import { PermissionGuard } from "@/components/common/permission-guard";
import { Pagination } from "@/components/common/pagination";
import { VolunteerFormDialog } from "@/components/common/volunteer-form-dialog";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { volunteerService } from "@/services/volunteer.service";
import { useDebouncedValue } from "@/hooks/use-debounced-value";
import { PERMISSIONS, VOLUNTEER_AVAILABILITY } from "@/constants/rbac";
import { LANGUAGES } from "@/constants/india";
import type { TaskStatus, Volunteer, VolunteerListQuery, VolunteerStatus } from "@/types/volunteer";

export const Route = createFileRoute("/_authenticated/volunteers/")({
  head: () => ({
    meta: [
      { title: "Volunteers — Multilingua" },
      { name: "description", content: "Browse, search, and manage volunteers." },
      { name: "robots", content: "noindex" },
    ],
  }),
  component: VolunteersPage,
});

const STATUS_OPTIONS: { value: VolunteerStatus | "all"; label: string }[] = [
  { value: "all", label: "All statuses" },
  { value: "available", label: "Available" },
  { value: "busy", label: "Busy" },
  { value: "on_leave", label: "On leave" },
  { value: "inactive", label: "Inactive" },
];

const TASK_STATUS_OPTIONS: { value: TaskStatus | "all"; label: string }[] = [
  { value: "all", label: "Any task status" },
  { value: "pending", label: "Pending" },
  { value: "accepted", label: "Accepted" },
  { value: "in_progress", label: "In progress" },
  { value: "completed", label: "Completed" },
  { value: "rejected", label: "Rejected" },
];

function VolunteersPage() {
  const [search, setSearch] = useState("");
  const [language, setLanguage] = useState<string>("all");
  const [skill, setSkill] = useState("");
  const [location, setLocation] = useState("");
  const [availability, setAvailability] = useState<string>("all");
  const [status, setStatus] = useState<VolunteerStatus | "all">("all");
  const [taskStatus, setTaskStatus] = useState<TaskStatus | "all">("all");
  const [sortBy, setSortBy] = useState<VolunteerListQuery["sortBy"]>("fullName");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");
  const [page, setPage] = useState(1);
  const [pageSize] = useState(25);
  const [createOpen, setCreateOpen] = useState(false);
  const debouncedSearch = useDebouncedValue(search, 300);
  const debouncedSkill = useDebouncedValue(skill, 300);
  const debouncedLocation = useDebouncedValue(location, 300);

  const query = useMemo<VolunteerListQuery>(
    () => ({
      search: debouncedSearch || undefined,
      language: language !== "all" ? language : undefined,
      skill: debouncedSkill || undefined,
      location: debouncedLocation || undefined,
      availability: availability !== "all" ? availability : undefined,
      status: status !== "all" ? status : undefined,
      taskStatus: taskStatus !== "all" ? taskStatus : undefined,
      sortBy,
      sortDir,
      page,
      pageSize,
    }),
    [debouncedSearch, language, debouncedSkill, debouncedLocation, availability, status, taskStatus, sortBy, sortDir, page, pageSize],
  );

  const listQuery = useQuery({
    queryKey: ["volunteers", query],
    queryFn: () => volunteerService.list(query),
  });

  const columns: DataTableColumn<Volunteer>[] = [
    {
      key: "name",
      header: "Volunteer",
      render: (v) => (
        <Link to="/volunteers/$id" params={{ id: v.id }} className="font-medium text-foreground hover:underline">
          {v.fullName}
        </Link>
      ),
    },
    { key: "email", header: "Email", render: (v) => <span className="text-muted-foreground">{v.email}</span> },
    { key: "phone", header: "Phone", render: (v) => <span className="text-muted-foreground">{v.phone}</span> },
    {
      key: "languages",
      header: "Languages",
      render: (v) => <span className="text-muted-foreground">{v.languages.join(", ") || "—"}</span>,
    },
    {
      key: "skills",
      header: "Skills",
      render: (v) => <span className="text-muted-foreground">{v.skills.slice(0, 3).join(", ") || "—"}</span>,
    },
    { key: "location", header: "Location", render: (v) => v.currentLocation || "—" },
    { key: "availability", header: "Availability", render: (v) => v.availability || "—" },
    { key: "status", header: "Status", render: (v) => <StatusBadge status={v.status} /> },
    {
      key: "tasks",
      header: "Tasks",
      align: "right",
      render: (v) => (
        <span className="tabular-nums text-muted-foreground">
          {v.activeTaskCount} active · {v.completedTaskCount} done
        </span>
      ),
    },
  ];

  return (
    <PermissionGuard anyOf={[PERMISSIONS.VOLUNTEER_VIEW]}>
      <div className="space-y-6">
        <SectionHeader
          title="Volunteers"
          description="Browse volunteers, review profiles, and assign tasks."
          actions={
            <PermissionGuard anyOf={[PERMISSIONS.VOLUNTEER_MANAGE]}>
              <Button size="sm" className="gap-1" onClick={() => setCreateOpen(true)}>
                <Plus className="h-4 w-4" /> New volunteer
              </Button>
            </PermissionGuard>
          }
        />

        <Card className="shadow-card">
          <CardContent className="space-y-3 p-4">
            <div className="flex flex-wrap items-center gap-2">
              <div className="relative min-w-[220px] flex-1">
                <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="Search by name or email"
                  className="pl-9"
                />
              </div>
              <Input
                value={skill}
                onChange={(e) => setSkill(e.target.value)}
                placeholder="Skill"
                className="max-w-[160px]"
              />
              <Input
                value={location}
                onChange={(e) => setLocation(e.target.value)}
                placeholder="Location"
                className="max-w-[160px]"
              />
              <Select value={language} onValueChange={setLanguage}>
                <SelectTrigger className="w-[150px]"><SelectValue placeholder="Language" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All languages</SelectItem>
                  {LANGUAGES.map((l) => (
                    <SelectItem key={l.code} value={l.code}>{l.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Select value={availability} onValueChange={setAvailability}>
                <SelectTrigger className="w-[150px]"><SelectValue placeholder="Availability" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Any availability</SelectItem>
                  {VOLUNTEER_AVAILABILITY.map((a) => (
                    <SelectItem key={a} value={a}>{a}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Select value={status} onValueChange={(v) => setStatus(v as VolunteerStatus | "all")}>
                <SelectTrigger className="w-[150px]"><SelectValue placeholder="Status" /></SelectTrigger>
                <SelectContent>
                  {STATUS_OPTIONS.map((o) => (
                    <SelectItem key={o.value} value={o.value}>{o.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Select value={taskStatus} onValueChange={(v) => setTaskStatus(v as TaskStatus | "all")}>
                <SelectTrigger className="w-[160px]"><SelectValue placeholder="Task status" /></SelectTrigger>
                <SelectContent>
                  {TASK_STATUS_OPTIONS.map((o) => (
                    <SelectItem key={o.value} value={o.value}>{o.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Button
                variant="outline"
                size="sm"
                className="gap-1"
                onClick={() => {
                  if (sortBy === "fullName") setSortDir((d) => (d === "asc" ? "desc" : "asc"));
                  else { setSortBy("fullName"); setSortDir("asc"); }
                }}
              >
                <ArrowUpDown className="h-3.5 w-3.5" />
                Sort: {sortBy ?? "name"} {sortDir}
              </Button>
            </div>
          </CardContent>
        </Card>

        <Card className="shadow-card">
          <CardContent className="space-y-3 p-4">
            {listQuery.isLoading ? (
              <SkeletonBlock rows={8} />
            ) : listQuery.isError ? (
              <ErrorState onRetry={() => listQuery.refetch()} />
            ) : !listQuery.data || listQuery.data.items.length === 0 ? (
              <EmptyState
                icon={HeartHandshake}
                title="No volunteers yet"
                description="Volunteers who register on the platform will appear here."
              />
            ) : (
              <>
                <DataTable rows={listQuery.data.items} columns={columns} rowKey={(v) => v.id} />
                <Pagination
                  page={listQuery.data.page}
                  pageSize={listQuery.data.pageSize}
                  total={listQuery.data.total}
                  onPageChange={setPage}
                />
              </>
            )}
          </CardContent>
        </Card>

        <VolunteerFormDialog
          open={createOpen}
          onOpenChange={setCreateOpen}
          onSaved={() => listQuery.refetch()}
        />
      </div>
    </PermissionGuard>
  );
}
