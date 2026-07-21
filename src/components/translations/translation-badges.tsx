import { Badge } from "@/components/ui/badge";
import type {
  TranslationJobStatus,
  TranslationStatus,
} from "@/types/translation";

const STATUS_TONE: Record<TranslationStatus, string> = {
  draft: "bg-muted text-muted-foreground",
  translated: "bg-blue-500/15 text-blue-700 dark:text-blue-300",
  reviewed: "bg-amber-500/15 text-amber-700 dark:text-amber-300",
  published: "bg-emerald-500/15 text-emerald-700 dark:text-emerald-300",
};

export function TranslationStatusBadge({ status }: { status: TranslationStatus }) {
  return (
    <Badge variant="secondary" className={STATUS_TONE[status] ?? ""}>
      {status}
    </Badge>
  );
}

const JOB_TONE: Record<TranslationJobStatus, string> = {
  pending: "bg-muted text-muted-foreground",
  processing: "bg-blue-500/15 text-blue-700 dark:text-blue-300",
  completed: "bg-emerald-500/15 text-emerald-700 dark:text-emerald-300",
  failed: "bg-destructive/15 text-destructive",
  cancelled: "bg-muted text-muted-foreground line-through",
};

export function TranslationJobStatusBadge({
  status,
}: {
  status: TranslationJobStatus;
}) {
  return (
    <Badge variant="secondary" className={JOB_TONE[status] ?? ""}>
      {status}
    </Badge>
  );
}

export function LocaleBadge({
  locale,
  isDefault,
}: {
  locale: string;
  isDefault?: boolean;
}) {
  return (
    <Badge
      variant="outline"
      className={
        isDefault
          ? "border-primary/50 text-primary uppercase tracking-wide"
          : "uppercase tracking-wide"
      }
    >
      {locale}
      {isDefault ? " · default" : ""}
    </Badge>
  );
}
