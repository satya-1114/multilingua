import { useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Globe, Pencil, Plus, Power, Star } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/common/empty-state";
import { ErrorState } from "@/components/common/error-state";
import { SkeletonBlock } from "@/components/common/skeleton-block";
import { DataTable, type DataTableColumn } from "@/components/common/data-table";
import { PermissionGuard } from "@/components/common/permission-guard";
import {
  LocaleBadge,
} from "@/components/translations/translation-badges";
import { LocaleFormDialog } from "@/components/translations/locale-form-dialog";
import { PERMISSIONS } from "@/constants/rbac";
import { translationService } from "@/services/translation.service";
import { queryKeys } from "@/lib/queryKeys";
import type {
  TranslationLocale,
  TranslationLocaleInput,
  TranslationLocaleUpdate,
} from "@/types/translation";

export const Route = createFileRoute("/_authenticated/translations/locales")({
  head: () => ({
    meta: [
      { title: "Translation locales — Multilingua" },
      { name: "robots", content: "noindex" },
    ],
  }),
  component: LocalesPage,
});

function LocalesPage() {
  const qc = useQueryClient();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<TranslationLocale | null>(null);

  const q = useQuery({
    queryKey: queryKeys.translationLocales.list(false),
    queryFn: () => translationService.listLocales(false),
  });

  const invalidate = () =>
    qc.invalidateQueries({ queryKey: queryKeys.translationLocales.all });

  const upsertMutation = useMutation({
    mutationFn: async (args: {
      payload: TranslationLocaleInput | TranslationLocaleUpdate;
      mode: "create" | "update";
    }) => {
      if (args.mode === "create") {
        return translationService.createLocale(args.payload as TranslationLocaleInput);
      }
      if (!editing) throw new Error("Missing locale");
      return translationService.updateLocaleMeta(
        editing.locale,
        args.payload as TranslationLocaleUpdate,
      );
    },
    onSuccess: () => {
      toast.success(editing ? "Locale updated" : "Locale registered");
      invalidate();
      setDialogOpen(false);
      setEditing(null);
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const enableMutation = useMutation({
    mutationFn: (locale: string) => translationService.enableLocale(locale),
    onSuccess: () => { toast.success("Locale enabled"); invalidate(); },
    onError: (err: Error) => toast.error(err.message),
  });
  const disableMutation = useMutation({
    mutationFn: (locale: string) => translationService.disableLocale(locale),
    onSuccess: () => { toast.success("Locale disabled"); invalidate(); },
    onError: (err: Error) => toast.error(err.message),
  });
  const defaultMutation = useMutation({
    mutationFn: (locale: string) => translationService.setDefaultLocale(locale),
    onSuccess: () => { toast.success("Default locale updated"); invalidate(); },
    onError: (err: Error) => toast.error(err.message),
  });

  const rows = q.data ?? [];

  const columns: DataTableColumn<TranslationLocale>[] = [
    { key: "locale", header: "Locale", render: (l) => <LocaleBadge locale={l.locale} isDefault={l.defaultLocale} /> },
    { key: "displayName", header: "Display name", render: (l) => <span className="text-sm">{l.displayName}</span> },
    { key: "nativeName", header: "Native", render: (l) => <span className="text-sm">{l.nativeName ?? "—"}</span> },
    { key: "flags", header: "Flags", render: (l) => (
      <span className="text-xs text-muted-foreground">
        {l.rtl ? "RTL · " : ""}{l.enabled ? "enabled" : "disabled"}
      </span>
    )},
    { key: "sortOrder", header: "Order", render: (l) => <span className="text-xs">{l.sortOrder}</span> },
    {
      key: "actions",
      header: "",
      align: "right",
      render: (l) => (
        <div className="flex justify-end gap-1">
          <PermissionGuard anyOf={[PERMISSIONS.TRANSLATION_MANAGE_GLOSSARY]}>
            <Button size="sm" variant="ghost" className="gap-1.5" onClick={() => { setEditing(l); setDialogOpen(true); }}>
              <Pencil className="h-3.5 w-3.5" />
            </Button>
            <Button
              size="sm"
              variant="ghost"
              className="gap-1.5"
              onClick={() => (l.enabled ? disableMutation.mutate(l.locale) : enableMutation.mutate(l.locale))}
              disabled={enableMutation.isPending || disableMutation.isPending}
              title={l.enabled ? "Disable" : "Enable"}
            >
              <Power className="h-3.5 w-3.5" />
            </Button>
            <Button
              size="sm"
              variant="ghost"
              className="gap-1.5"
              onClick={() => defaultMutation.mutate(l.locale)}
              disabled={l.defaultLocale || defaultMutation.isPending}
              title="Set as default"
            >
              <Star className={l.defaultLocale ? "h-3.5 w-3.5 fill-primary text-primary" : "h-3.5 w-3.5"} />
            </Button>
          </PermissionGuard>
        </div>
      ),
    },
  ];

  return (
    <div className="space-y-5">
      <Card className="shadow-card">
        <CardContent className="flex items-center justify-between py-3">
          <p className="text-sm text-muted-foreground">
            {rows.length} locale{rows.length === 1 ? "" : "s"} registered
          </p>
          <PermissionGuard anyOf={[PERMISSIONS.TRANSLATION_MANAGE_GLOSSARY]}>
            <Button size="sm" className="gap-1.5" onClick={() => { setEditing(null); setDialogOpen(true); }}>
              <Plus className="h-4 w-4" /> Register locale
            </Button>
          </PermissionGuard>
        </CardContent>
      </Card>

      {q.isLoading ? (
        <SkeletonBlock rows={6} />
      ) : q.isError ? (
        <ErrorState
          title="Could not load locales"
          description={(q.error as Error).message}
          onRetry={() => q.refetch()}
        />
      ) : rows.length === 0 ? (
        <EmptyState
          icon={Globe}
          title="No locales registered"
          description="Register the locales you plan to translate content into."
        />
      ) : (
        <DataTable<TranslationLocale> rows={rows} columns={columns} rowKey={(l) => l.locale} />
      )}

      <LocaleFormDialog
        open={dialogOpen}
        onOpenChange={(o) => {
          setDialogOpen(o);
          if (!o) setEditing(null);
        }}
        existing={editing}
        submitting={upsertMutation.isPending}
        onSubmit={(payload, mode) => upsertMutation.mutateAsync({ payload, mode }).then(() => undefined)}
      />
    </div>
  );
}
