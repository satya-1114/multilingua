import { useMemo, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Plus, Pencil, Languages } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { EmptyState } from "@/components/common/empty-state";
import { ErrorState } from "@/components/common/error-state";
import { SkeletonBlock } from "@/components/common/skeleton-block";
import { PermissionGuard } from "@/components/common/permission-guard";
import { PERMISSIONS } from "@/constants/rbac";
import {
  LocaleBadge,
  TranslationStatusBadge,
} from "@/components/translations/translation-badges";
import { TranslationEditorDialog } from "@/components/translations/translation-editor-dialog";
import { translationService } from "@/services/translation.service";
import { queryKeys } from "@/lib/queryKeys";
import type {
  EntityTranslation,
  EntityTranslationInput,
  EntityTranslationUpdate,
} from "@/types/translation";

interface Props {
  entityType: string;
  entityId: string;
  /** Optional field-level filter, e.g. only show translations for `title`. */
  fieldName?: string;
}

/**
 * Reusable panel that renders translations for a single entity — used from
 * Disaster, Public Resource, Organization and Campaign detail views to give
 * a consistent multilingual surface.
 */
export function EntityTranslationsPanel({ entityType, entityId, fieldName }: Props) {
  const qc = useQueryClient();
  const [locale, setLocale] = useState<string>("all");
  const [editing, setEditing] = useState<EntityTranslation | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);

  const localesQ = useQuery({
    queryKey: queryKeys.translationLocales.list(true),
    queryFn: () => translationService.listLocales(true),
  });

  const listQ = useQuery({
    queryKey: queryKeys.translations.entity(
      entityType,
      entityId,
      locale === "all" ? undefined : locale,
    ),
    queryFn: () =>
      translationService.getEntityTranslations(
        entityType,
        entityId,
        locale === "all" ? undefined : locale,
      ),
    enabled: Boolean(entityType && entityId),
  });

  const items = useMemo(() => {
    const rows = listQ.data ?? [];
    return fieldName ? rows.filter((r) => r.fieldName === fieldName) : rows;
  }, [listQ.data, fieldName]);

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ["translations", "entity", entityType, entityId] });
    qc.invalidateQueries({ queryKey: queryKeys.translations.all });
  };

  const saveMutation = useMutation({
    mutationFn: async (args: {
      payload: EntityTranslationInput | EntityTranslationUpdate;
      mode: "create" | "update";
    }) => {
      if (args.mode === "create") {
        return translationService.createTranslation(args.payload as EntityTranslationInput);
      }
      if (!editing) throw new Error("Missing translation");
      return translationService.updateTranslation(editing.id, args.payload as EntityTranslationUpdate);
    },
    onSuccess: () => {
      toast.success(editing ? "Translation updated" : "Translation created");
      invalidate();
      setDialogOpen(false);
      setEditing(null);
    },
    onError: (err: Error) => toast.error(err.message || "Failed to save"),
  });

  const openCreate = () => {
    setEditing(null);
    setDialogOpen(true);
  };
  const openEdit = (t: EntityTranslation) => {
    setEditing(t);
    setDialogOpen(true);
  };

  return (
    <Card className="shadow-card">
      <CardHeader className="flex flex-row items-center justify-between space-y-0">
        <CardTitle className="flex items-center gap-2 text-base">
          <Languages className="h-4 w-4" /> Translations
        </CardTitle>
        <div className="flex items-center gap-2">
          <Select value={locale} onValueChange={setLocale}>
            <SelectTrigger className="h-8 w-[160px]"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All locales</SelectItem>
              {(localesQ.data ?? []).map((l) => (
                <SelectItem key={l.locale} value={l.locale}>
                  {l.locale} — {l.displayName}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <PermissionGuard anyOf={[PERMISSIONS.TRANSLATION_USE]}>
            <Button size="sm" onClick={openCreate} className="gap-1.5">
              <Plus className="h-4 w-4" /> Add
            </Button>
          </PermissionGuard>
        </div>
      </CardHeader>
      <CardContent>
        {listQ.isLoading ? (
          <SkeletonBlock rows={3} />
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
            description="Add a translation to make this entity available in another locale."
          />
        ) : (
          <ul className="space-y-2">
            {items.map((t) => (
              <li
                key={t.id}
                className="flex flex-col gap-1 rounded-md border border-border/60 p-3 md:flex-row md:items-start md:justify-between"
              >
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <LocaleBadge locale={t.locale} />
                    <span className="text-xs font-medium text-muted-foreground">
                      {t.fieldName}
                    </span>
                    <TranslationStatusBadge status={t.status} />
                  </div>
                  <p className="mt-1 whitespace-pre-wrap text-sm text-foreground">
                    {t.translatedValue || (
                      <span className="italic text-muted-foreground">(empty)</span>
                    )}
                  </p>
                </div>
                <PermissionGuard anyOf={[PERMISSIONS.TRANSLATION_USE]}>
                  <Button
                    size="sm"
                    variant="ghost"
                    className="gap-1.5"
                    onClick={() => openEdit(t)}
                  >
                    <Pencil className="h-3.5 w-3.5" /> Edit
                  </Button>
                </PermissionGuard>
              </li>
            ))}
          </ul>
        )}
      </CardContent>

      <TranslationEditorDialog
        open={dialogOpen}
        onOpenChange={(o) => {
          setDialogOpen(o);
          if (!o) setEditing(null);
        }}
        locales={localesQ.data ?? []}
        existing={editing}
        submitting={saveMutation.isPending}
        onSubmit={(payload, mode) => saveMutation.mutateAsync({ payload, mode }).then(() => undefined)}
        preset={{ entityType, entityId, fieldName }}
      />
    </Card>
  );
}
