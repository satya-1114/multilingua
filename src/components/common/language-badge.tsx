import { LANGUAGES } from "@/constants/india";
import { cn } from "@/lib/utils";

interface LanguageBadgeProps {
  code: string;
  className?: string;
  showScript?: boolean;
}

export function LanguageBadge({ code, className, showScript }: LanguageBadgeProps) {
  const lang = LANGUAGES.find((l) => l.code === code);
  const label = lang?.label ?? code.toUpperCase();
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-md border border-border/70 bg-muted/40 px-2 py-0.5 text-[11px] font-medium text-foreground",
        className,
      )}
    >
      <span className="font-semibold uppercase tracking-wide text-muted-foreground">
        {code}
      </span>
      <span>{label}</span>
      {showScript && lang?.script && (
        <span className="text-muted-foreground">· {lang.script}</span>
      )}
    </span>
  );
}
