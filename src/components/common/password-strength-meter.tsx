import { motion } from "framer-motion";
import { Check, X } from "lucide-react";
import { evaluatePasswordStrength } from "@/lib/password-strength";
import { cn } from "@/lib/utils";

interface PasswordStrengthMeterProps {
  password: string;
  showChecklist?: boolean;
}

const barColors = [
  "bg-destructive",
  "bg-destructive",
  "bg-warning",
  "bg-primary",
  "bg-success",
];

export function PasswordStrengthMeter({
  password,
  showChecklist = true,
}: PasswordStrengthMeterProps) {
  const { score, label, checks } = evaluatePasswordStrength(password);
  const segments = 4;
  const filled = score === 0 ? 0 : score;

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-1.5">
        {Array.from({ length: segments }).map((_, i) => (
          <motion.div
            key={i}
            initial={false}
            animate={{ opacity: 1 }}
            className={cn(
              "h-1.5 flex-1 rounded-full transition-colors",
              i < filled ? barColors[score] : "bg-border",
            )}
          />
        ))}
        <span className="ml-2 min-w-[60px] text-right text-xs font-medium text-muted-foreground">
          {password ? label : ""}
        </span>
      </div>
      {showChecklist && (
        <ul className="grid grid-cols-1 gap-1 sm:grid-cols-2">
          {checks.map((c) => (
            <li
              key={c.rule}
              className={cn(
                "flex items-center gap-1.5 text-xs",
                c.passed ? "text-success" : "text-muted-foreground",
              )}
            >
              {c.passed ? <Check className="h-3 w-3" /> : <X className="h-3 w-3" />}
              {c.rule}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
