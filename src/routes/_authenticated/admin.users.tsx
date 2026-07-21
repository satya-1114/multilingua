import { useEffect, useMemo, useState } from "react";
import { createFileRoute, Navigate } from "@tanstack/react-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { format } from "date-fns";
import { toast } from "sonner";
import { Users2, ShieldCheck, UserCog } from "lucide-react";
import { SectionHeader } from "@/components/common/section-header";
import { DataTable, type DataTableColumn } from "@/components/common/data-table";
import { DataTableToolbar } from "@/components/common/data-table-toolbar";
import { EmptyState } from "@/components/common/empty-state";
import { SkeletonBlock } from "@/components/common/skeleton-block";
import { RoleBadge } from "@/components/common/role-badge";
import { StatusBadge } from "@/components/common/status-badge";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { userService, type PlatformUser } from "@/services/user.service";
import { useAuth } from "@/contexts/auth-context";
import { useDebouncedValue } from "@/hooks/use-debounced-value";
import {
  PERMISSIONS,
  ROLE_METADATA,
  ROLES,
  type Role,
} from "@/constants/rbac";

export const Route = createFileRoute("/_authenticated/admin/users")({
  head: () => ({
    meta: [
      { title: "Users — Multilingua" },
      { name: "description", content: "Manage platform users, account status, and role assignments." },
      { name: "robots", content: "noindex" },
    ],
  }),
  component: AdminUsersPage,
});

const ALL_ROLES: Role[] = [
  ROLES.SUPER_ADMIN,
  ROLES.CAMPAIGN_MANAGER,
  ROLES.VOLUNTEER,
  ROLES.VIEWER,
];

function initials(name: string): string {
  return (
    name
      .split(/\s+/)
      .filter(Boolean)
      .slice(0, 2)
      .map((p) => p[0]?.toUpperCase() ?? "")
      .join("") || "?"
  );
}

function isKnownRole(value: string): value is Role {
  return (ALL_ROLES as string[]).includes(value);
}

function AdminUsersPage() {
  const { hasRole } = useAuth();

  // Route-level protection: platform-wide user role management is restricted
  // to the super_admin role. Backend RBAC remains authoritative.
  if (!hasRole(ROLES.SUPER_ADMIN)) {
    return <Navigate to="/forbidden" />;
  }

  return <AdminUsersContent />;
}

function AdminUsersContent() {
  const { hasPermission, user: currentUser } = useAuth();
  const canManage = hasPermission(PERMISSIONS.USER_MANAGE);
  const currentUserId = currentUser?.id ?? null;
  const queryClient = useQueryClient();

  const [search, setSearch] = useState("");
  const [roleFilter, setRoleFilter] = useState<Role | "all">("all");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [editing, setEditing] = useState<PlatformUser | null>(null);
  const debouncedSearch = useDebouncedValue(search, 250);

  const usersQuery = useQuery({
    queryKey: ["admin", "users"],
    queryFn: () => userService.getUsers(),
  });

  const users = usersQuery.data ?? [];

  const statuses = useMemo(() => {
    const set = new Set<string>();
    for (const u of users) if (u.status) set.add(u.status);
    return Array.from(set).sort();
  }, [users]);

  const filtered = useMemo(() => {
    const q = debouncedSearch.trim().toLowerCase();
    return users.filter((u) => {
      if (q) {
        const hay = `${u.fullName} ${u.email}`.toLowerCase();
        if (!hay.includes(q)) return false;
      }
      if (roleFilter !== "all" && !u.roles.includes(roleFilter)) return false;
      if (statusFilter !== "all" && u.status !== statusFilter) return false;
      return true;
    });
  }, [users, debouncedSearch, roleFilter, statusFilter]);

  const columns: DataTableColumn<PlatformUser>[] = [
    {
      key: "user",
      header: "User",
      render: (u) => (
        <div className="flex items-center gap-3">
          <Avatar className="h-9 w-9">
            {u.avatarUrl ? <AvatarImage src={u.avatarUrl} alt={u.fullName} /> : null}
            <AvatarFallback className="bg-primary/10 text-primary text-xs font-semibold">
              {initials(u.fullName || u.email)}
            </AvatarFallback>
          </Avatar>
          <div className="min-w-0">
            <p className="truncate text-sm font-medium text-foreground">
              {u.fullName || "—"}
            </p>
            <p className="truncate text-xs text-muted-foreground">{u.email}</p>
          </div>
        </div>
      ),
    },
    {
      key: "roles",
      header: "Role",
      render: (u) => (
        <div className="flex flex-wrap gap-1">
          {u.roles.length === 0 ? (
            <span className="text-xs text-muted-foreground">None</span>
          ) : (
            u.roles.map((r) =>
              isKnownRole(r) ? (
                <RoleBadge key={r} role={r} />
              ) : (
                <span
                  key={r}
                  className="inline-flex items-center rounded-md bg-muted px-2 py-0.5 text-[11px] font-semibold text-muted-foreground"
                >
                  {r}
                </span>
              ),
            )
          )}
        </div>
      ),
    },
    {
      key: "status",
      header: "Status",
      render: (u) => (u.status ? <StatusBadge status={u.status} /> : <span className="text-xs text-muted-foreground">—</span>),
    },
    {
      key: "createdAt",
      header: "Created",
      render: (u) => (
        <span className="text-xs text-muted-foreground">
          {u.createdAt ? format(new Date(u.createdAt), "PP") : "—"}
        </span>
      ),
    },
    {
      key: "actions",
      header: "",
      align: "right",
      render: (u) => {
        const isSelf = currentUserId !== null && u.id === currentUserId;
        const disabled = !canManage || isSelf;
        const button = (
          <Button
            variant="ghost"
            size="sm"
            className="gap-2"
            onClick={() => setEditing(u)}
            disabled={disabled}
            aria-label={`Manage role for ${u.fullName || u.email}`}
          >
            <UserCog className="h-4 w-4" />
            Manage role
          </Button>
        );
        if (isSelf) {
          return (
            <TooltipProvider delayDuration={100}>
              <Tooltip>
                <TooltipTrigger asChild>
                  {/* wrapper needed because disabled buttons don't fire pointer events */}
                  <span tabIndex={0} className="inline-flex">{button}</span>
                </TooltipTrigger>
                <TooltipContent side="left">You cannot change your own role.</TooltipContent>
              </Tooltip>
            </TooltipProvider>
          );
        }
        return button;
      },
    },
  ];

  return (
    <div className="space-y-6">
      <SectionHeader
        title="Users"
        description="Manage platform users, account status, and role assignments."
        actions={
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Users2 className="h-4 w-4" />
            {users.length} total
          </div>
        }
      />

      <DataTableToolbar
        search={search}
        onSearchChange={setSearch}
        placeholder="Search by name or email…"
        actions={
          <>
            <Select value={roleFilter} onValueChange={(v) => setRoleFilter(v as Role | "all")}>
              <SelectTrigger className="h-9 w-44">
                <SelectValue placeholder="Role" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All roles</SelectItem>
                {ALL_ROLES.map((r) => (
                  <SelectItem key={r} value={r}>
                    {ROLE_METADATA[r].label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {statuses.length > 0 && (
              <Select value={statusFilter} onValueChange={setStatusFilter}>
                <SelectTrigger className="h-9 w-36">
                  <SelectValue placeholder="Status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All status</SelectItem>
                  {statuses.map((s) => (
                    <SelectItem key={s} value={s}>
                      {s.charAt(0).toUpperCase() + s.slice(1)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
          </>
        }
      />

      {usersQuery.isLoading ? (
        <SkeletonBlock rows={6} />
      ) : usersQuery.isError ? (
        <EmptyState
          title="Couldn't load users"
          description={
            usersQuery.error instanceof Error
              ? usersQuery.error.message
              : "An unexpected error occurred."
          }
        />
      ) : filtered.length === 0 ? (
        <EmptyState
          title="No users found"
          description="Try adjusting your search or filters."
        />
      ) : (
        <div className="rounded-xl border border-border bg-card p-4">
          <DataTable
            columns={columns}
            rows={filtered}
            rowKey={(u) => u.id}
          />
        </div>
      )}

      <RoleManagementDialog
        user={editing}
        open={!!editing}
        canManage={canManage}
        onClose={() => setEditing(null)}
        onSaved={() => {
          setEditing(null);
          void queryClient.invalidateQueries({ queryKey: ["admin", "users"] });
        }}
      />
    </div>
  );
}

interface RoleManagementDialogProps {
  user: PlatformUser | null;
  open: boolean;
  canManage: boolean;
  onClose: () => void;
  onSaved: () => void;
}

function RoleManagementDialog({ user, open, canManage, onClose, onSaved }: RoleManagementDialogProps) {
  const [selected, setSelected] = useState<Role | null>(null);

  // Reset selection when the target user changes. Milestone 1 enforces one
  // role per user; if the backend returns multiple, prefer the first known.
  useEffect(() => {
    if (user) {
      const first = user.roles.find(isKnownRole) as Role | undefined;
      setSelected(first ?? null);
    } else {
      setSelected(null);
    }
  }, [user]);

  const mutation = useMutation({
    mutationFn: (role: Role) => {
      if (!user) throw new Error("No user selected");
      return userService.updateUser(user.id, { roles: [role] });
    },
    onSuccess: () => {
      toast.success("User role updated successfully");
      onSaved();
    },
    onError: (err: unknown) => {
      const message =
        err instanceof Error && err.message ? err.message : "Failed to update user role";
      toast.error(message);
    },
  });

  return (
    <Dialog open={open} onOpenChange={(o) => (!o && !mutation.isPending ? onClose() : undefined)}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <ShieldCheck className="h-4 w-4 text-primary" />
            Manage role
          </DialogTitle>
          <DialogDescription>
            {user ? (
              <>
                Update the role assignment for{" "}
                <span className="font-medium text-foreground">{user.fullName || user.email}</span>{" "}
                <span className="text-muted-foreground">({user.email})</span>.
              </>
            ) : null}
          </DialogDescription>
        </DialogHeader>

        <RadioGroup
          value={selected ?? ""}
          onValueChange={(v) => setSelected(v as Role)}
          className="space-y-2 py-2"
          disabled={!canManage || mutation.isPending}
        >
          {ALL_ROLES.map((role) => {
            const meta = ROLE_METADATA[role];
            const inputId = `role-${role}`;
            return (
              <label
                key={role}
                htmlFor={inputId}
                className="flex cursor-pointer items-start gap-3 rounded-lg border border-border p-3 transition-colors hover:bg-accent/40"
              >
                <RadioGroupItem id={inputId} value={role} className="mt-0.5" />
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-foreground">{meta.label}</span>
                    <span className="font-mono text-[10px] text-muted-foreground">{role}</span>
                  </div>
                  <p className="mt-0.5 text-xs text-muted-foreground">{meta.description}</p>
                </div>
              </label>
            );
          })}
        </RadioGroup>

        <DialogFooter>
          <Button variant="ghost" onClick={onClose} disabled={mutation.isPending}>
            Cancel
          </Button>
          <Button
            onClick={() => selected && mutation.mutate(selected)}
            disabled={!canManage || mutation.isPending || !selected}
          >
            {mutation.isPending ? "Saving…" : "Save role"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
