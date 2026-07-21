import { useState } from "react";
import { createFileRoute, Link, useRouter } from "@tanstack/react-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { ArrowLeft, Check, Pencil, Send, Trash2, X } from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { SkeletonBlock } from "@/components/common/skeleton-block";
import { ErrorState } from "@/components/common/error-state";
import { PermissionGuard } from "@/components/common/permission-guard";
import { ConfirmDialog } from "@/components/common/confirm-dialog";
import {
  LocaleBadge,
  TranslationStatusBadge,
} from "@/components/translations/translation-badges";
import { TranslationEditorDialog } from "@/components/translations/translation-editor-dialog";
import { PERMISSIONS } from "@/constants/rbac";
import { translationService } from "@/services/translation.service";
import { queryKeys } from "@/lib/queryKeys";
import type { EntityTranslationUpdate } from "@/types/translation";

export const Route = createFileRoute("/_authenticated/translations/$id")({
  head: () => ({
    meta: [
      { title: "Translation — Multilingua" },
      { name: "robots", content: "noindex" },
    ],
  }),
  component: TranslationDetailPage,
});

function TranslationDetailPage() {
  const { id } = Route.useParams();
  const router = useRouter();
  const qc = useQueryClient();
  const [editOpen, setEditOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);

  const q = useQuery({
    queryKey: queryKeys.translations.detail(id),
    queryFn: () => translationService.getTranslation(id),
  });

  const localesQ = useQuery({
    queryKey: queryKeys.translationLocales.list(true),
    queryFn: () => translationService.listLocales(true),
  });

  const invalidateAll = () => {
    qc.invalidateQueries({ queryKey: queryKeys.translations.detail(id) });
    qc.invalidateQueries({ queryKey: queryKeys.translations.all });
  };

  const updateMutation = useMutation({
    mutationFn: (patch: EntityTranslationUpdate) =>
      translationService.updateTranslation(id, patch),
    onSuccess: () => {
      toast.success("Translation updated");
      invalidateAll();
      setEditOpen(false);
    },
    onError: (err: Error) => toast.error(err.message || "Failed to update"),
  });

  const reviewMutation = useMutation({
    mutationFn: () => translationService.reviewTranslation(id),
    onSuccess: () => {
      toast.success("Translation reviewed");
      invalidateAll();
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const rejectMutation = useMutation({
    mutationFn: () => translationService.rejectTranslation(id),
    onSuccess: () => {
      toast.success("Translation rejected");
      invalidateAll();
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const publishMutation = useMutation({
    mutationFn: () => translationService.publishTranslation(id),
    onSuccess: () => {
      toast.success("Translation published");
      invalidateAll();
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const deleteMutation = useMutation({
    mutationFn: () => translationService.deleteTranslation(id),
    onSuccess: () => {
      toast.success("Translation deleted");
      qc.invalidateQueries({ queryKey: queryKeys.translations.all });
      router.navigate({ to: "/translations" });
    },
    onError: (err: Error) => toast.error(err.message),
  });

  if (q.isLoading) return <SkeletonBlock rows={8} />;
  if (q.isError) {
    return (
      <ErrorState
        title="Could not load translation"
        description={(q.error as Error).message}
        onRetry={() => q.refetch()}
      />
    );
  }
  const t = q.data!;
  const canReview = t.status === "translated";
  const canPublish = t.status === "reviewed";

  return (
    <div className="space-y-5">
      <Button asChild size="sm" variant="ghost" className="gap-1.5">
        <Link to="/translations"><ArrowLeft className="h-4 w-4" /> Back to translations</Link>
      </Button>

      <Card className="shadow-card">
        <CardHeader className="flex flex-row items-start justify-between space-y-0">
          <div>
            <CardTitle className="flex flex-wrap items-center gap-2 text-lg">
              <span className="capitalize">{t.entityType.replace(/_/g, " ")}</span>
              <span className="text-muted-foreground">/</span>
              <span className="font-mono text-sm">{t.fieldName}</span>
              <LocaleBadge locale={t.locale} />
              <TranslationStatusBadge status={t.status} />
            </CardTitle>
            <p className="mt-1 text-xs text-muted-foreground font-mono">{t.entityId}</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <PermissionGuard anyOf={[PERMISSIONS.TRANSLATION_USE]}>
              <Button size="sm" variant="outline" className="gap-1.5" onClick={() => setEditOpen(true)}>
                <Pencil className="h-3.5 w-3.5" /> Edit
              </Button>
            </PermissionGuard>
            <PermissionGuard anyOf={[PERMISSIONS.TRANSLATION_MANAGE_GLOSSARY, PERMISSIONS.CONTENT_APPROVE]}>
              <Button
                size="sm"
                variant="outline"
                className="gap-1.5"
                disabled={!canReview || reviewMutation.isPending}
                onClick={() => reviewMutation.mutate()}
              >
                <Check className="h-3.5 w-3.5" /> Review
              </Button>
              <Button
                size="sm"
                variant="outline"
                className="gap-1.5"
                disabled={!canReview || rejectMutation.isPending}
                onClick={() => rejectMutation.mutate()}
              >
                <X className="h-3.5 w-3.5" /> Reject
              </Button>
              <Button
                size="sm"
                className="gap-1.5"
                disabled={!canPublish || publishMutation.isPending}
                onClick={() => publishMutation.mutate()}
              >
                <Send className="h-3.5 w-3.5" /> Publish
              </Button>
            </PermissionGuard>
            <PermissionGuard anyOf={[PERMISSIONS.TRANSLATION_MANAGE_GLOSSARY]}>
              <Button
                size="sm"
                variant="destructive"
                className="gap-1.5"
                onClick={() => setDeleteOpen(true)}
              >
                <Trash2 className="h-3.5 w-3.5" /> Delete
              </Button>
            </PermissionGuard>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <p className="mb-1 text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Translated value
            </p>
            <p className="whitespace-pre-wrap rounded-md border border-border/60 bg-muted/30 p-3 text-sm text-foreground">
              {t.translatedValue || (
                <span className="italic text-muted-foreground">(empty)</span>
              )}
            </p>
          </div>
          <dl className="grid grid-cols-1 gap-3 text-sm md:grid-cols-2">
            <div>
              <dt className="text-xs uppercase tracking-wide text-muted-foreground">Source hash</dt>
              <dd className="font-mono text-xs">{t.sourceHash ?? "—"}</dd>
            </div>
            <div>
              <dt className="text-xs uppercase tracking-wide text-muted-foreground">Updated</dt>
              <dd>
                {t.updatedAt
                  ? formatDistanceToNow(new Date(t.updatedAt), { addSuffix: true })
                  : "—"}
              </dd>
            </div>
            <div>
              <dt className="text-xs uppercase tracking-wide text-muted-foreground">Translator</dt>
              <dd className="font-mono text-xs">{t.translatedByUserId ?? "—"}</dd>
            </div>
            <div>
              <dt className="text-xs uppercase tracking-wide text-muted-foreground">Reviewer</dt>
              <dd className="font-mono text-xs">{t.reviewedByUserId ?? "—"}</dd>
            </div>
          </dl>
        </CardContent>
      </Card>

      <TranslationEditorDialog
        open={editOpen}
        onOpenChange={setEditOpen}
        locales={localesQ.data ?? []}
        existing={t}
        submitting={updateMutation.isPending}
        onSubmit={(payload) => updateMutation.mutateAsync(payload as EntityTranslationUpdate).then(() => undefined)}
      />

      <ConfirmDialog
        open={deleteOpen}
        onOpenChange={setDeleteOpen}
        title="Delete this translation?"
        description="This cannot be undone. The published translated value will be removed."
        destructive
        confirmLabel="Delete"
        onConfirm={() => deleteMutation.mutateAsync().then(() => undefined)}
      />
    </div>
  );
}
