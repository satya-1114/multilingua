import { useMemo, useState } from "react";
import { createFileRoute, Link } from "@tanstack/react-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Languages, Plus, Search } from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import { EmptyState } from "@/components/common/empty-state";
import { ErrorState } from "@/components/common/error-state";
import { SkeletonBlock } from "@/components/common/skeleton-block";
import { DataTable, type DataTableColumn } from "@/components/common/data-table";
import { PermissionGuard } from "@/components/common/permission-guard";
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
import { useDebouncedValue } from "@/hooks/use-debounced-value";
import { PERMISSIONS } from "@/constants/rbac";
import { translationService } from "@/services/translation.service";
import { queryKeys } from "@/lib/queryKeys";
import {
  LocaleBadge,
  TranslationStatusBadge,
} from "@/components/translations/translation-badges";
import { TranslationEditorDialog } from "@/components/translations/translation-editor-dialog";
import {
  TRANSLATION_ENTITY_TYPES,
  TRANSLATION_STATUSES,
  type EntityTranslation,
  type EntityTranslationInput,
  type TranslationListQuery,
} from "@/types/translation";

export const Route = createFileRoute("/_authenticated/translations/")({
  head: () => ({
    meta: [
      { title: "Translations — Multilingua" },
      { name: "robots", content: "noindex" },
    ],
  }),
  component: TranslationsListPage,
});

const PAGE_SIZE = 25;

function TranslationsListPage() {
  const qc = useQueryClient();
  const [search, setSearch] = useState("");
  const [entityType, setEntityType] = useState("all");
  const [locale, setLocale] = useState("all");
  const [status, setStatus] = useState("all");
  const [page, setPage] = useState(1);
  const [dialogOpen, setDialogOpen] = useState(false);
  const debouncedSearch = useDebouncedValue(search, 300);

  const query = useMemo<TranslationListQuery>(
    () => ({
      page,
      pageSize: PAGE_SIZE,
      query: debouncedSearch || undefined,
      entityType: entityType !== "all" ? entityType : undefined,
      locale: locale !== "all" ? locale : undefined,
      status: status !== "all" ? (status as TranslationListQuery["status"]) : undefined,
      sortBy: "updatedAt",
      sortDir: "desc",
    }),
    [debouncedSearch, entityType, locale, status, page],
  );

  const listQ = useQuery({
    queryKey: queryKeys.translations.list(query as unknown as Record<string, unknown>),
    queryFn: () => translationService.listTranslations(query),
  });

  const localesQ = useQuery({
    queryKey: queryKeys.translationLocales.list(true),
    queryFn: () => translationService.listLocales(true),
  });

  const createMutation = useMutation({
    mutationFn: (payload: EntityTranslationInput) =>
      translationService.createTranslation(payload),
    onSuccess: () => {
      toast.success("Translation created");
      qc.invalidateQueries({ queryKey: queryKeys.translations.all });
      setDialogOpen(false);
    },
    onError: (err: Error) => toast.error(err.message || "Failed to create"),
  });

  const items: EntityTranslation[] = listQ.data?.items ?? [];
  const total = listQ.data?.total ?? 0;
  const pageCount = Math.max(1, Math.ceil(total / PAGE_SIZE));

  const columns: DataTableColumn<EntityTranslation>[] = [
    {
      key: "entity",
      header: "Entity",
      render: (t) => (
        <div className="min-w-0">
          <Link
            to="/translations/$id"
            params={{ id: t.id }}
            className="font-medium text-foreground hover:underline"
          >
            {t.entityType}
          </Link>
          <p className="truncate text-xs text-muted-foreground font-mono">{t.entityId}</p>
        </div>
      ),
    },
    { key: "field", header: "Field", render: (t) => <span className="text-sm">{t.fieldName}</span> },
    { key: "locale", header: "Locale", render: (t) => <LocaleBadge locale={t.locale} /> },
    {
      key: "value",
      header: "Value",
      render: (t) => (
        <span className="line-clamp-2 max-w-[360px] text-sm text-foreground">
          {t.translatedValue || <span className="italic text-muted-foreground">(empty)</span>}
        </span>
      ),
    },
    { key: "status", header: "Status", render: (t) => <TranslationStatusBadge status={t.status} /> },
    {
      key: "updated",
      header: "Updated",
      render: (t) => (
        <span className="text-xs text-muted-foreground">
          {t.updatedAt
            ? formatDistanceToNow(new Date(t.updatedAt), { addSuffix: true })
            : "—"}
        </span>
      ),
    },
  ];

  return (
    <div className="space-y-5">
      <Card className="shadow-card">
        <CardContent className="flex flex-col gap-3 py-4 md:flex-row md:flex-wrap md:items-center">
          <div className="relative flex-1 min-w-[220px]">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder="Search translated text or field…"
              className="pl-9"
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setPage(1);
              }}
            />
          </div>
          <Select value={entityType} onValueChange={(v) => { setEntityType(v); setPage(1); }}>
            <SelectTrigger className="w-[170px]"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All entities</SelectItem>
              {TRANSLATION_ENTITY_TYPES.map((t) => (
                <SelectItem key={t} value={t} className="capitalize">
                  {t.replace(/_/g, " ")}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select value={locale} onValueChange={(v) => { setLocale(v); setPage(1); }}>
            <SelectTrigger className="w-[170px]"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All locales</SelectItem>
              {(localesQ.data ?? []).map((l) => (
                <SelectItem key={l.locale} value={l.locale}>
                  {l.locale} — {l.displayName}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select value={status} onValueChange={(v) => { setStatus(v); setPage(1); }}>
            <SelectTrigger className="w-[150px]"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Any status</SelectItem>
              {TRANSLATION_STATUSES.map((s) => (
                <SelectItem key={s} value={s} className="capitalize">{s}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          <PermissionGuard anyOf={[PERMISSIONS.TRANSLATION_USE]}>
            <Button size="sm" className="gap-1.5" onClick={() => setDialogOpen(true)}>
              <Plus className="h-4 w-4" /> New translation
            </Button>
          </PermissionGuard>
        </CardContent>
      </Card>

      {listQ.isLoading ? (
        <SkeletonBlock rows={8} />
      ) : listQ.isError ? (
        <ErrorState
          title="Could not load translations"
          description={(listQ.error as Error).message}
          onRetry={() => listQ.refetch()}
        />
      ) : items.length === 0 ? (
        <EmptyState
          icon={Languages}
          title="No translations yet"
          description="Create your first translation or request a translation job from the Jobs tab."
        />
      ) : (
        <>
          <DataTable<EntityTranslation>
            rows={items}
            columns={columns}
            rowKey={(t) => t.id}
          />
          {pageCount > 1 && (
            <div className="flex items-center justify-between text-sm text-muted-foreground">
              <span>Page {page} of {pageCount} · {total} total</span>
              <div className="flex gap-2">
                <Button
                  size="sm"
                  variant="outline"
                  disabled={page <= 1}
                  onClick={() => setPage((p) => p - 1)}
                >
                  Previous
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  disabled={page >= pageCount}
                  onClick={() => setPage((p) => p + 1)}
                >
                  Next
                </Button>
              </div>
            </div>
          )}
        </>
      )}

      <TranslationEditorDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        locales={localesQ.data ?? []}
        submitting={createMutation.isPending}
        onSubmit={(payload) => createMutation.mutateAsync(payload as EntityTranslationInput).then(() => undefined)}
      />
    </div>
  );
}
