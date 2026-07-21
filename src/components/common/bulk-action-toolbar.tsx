import type { ReactNode } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { cn } from "@/lib/utils";

interface BulkActionToolbarProps {
  count: number;
  onClear: () => void;
  children: ReactNode;
  className?: string;
}

export function BulkActionToolbar({ count, onClear, children, className }: BulkActionToolbarProps) {
  return (
    <AnimatePresence>
      {count > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: 8 }}
          transition={{ duration: 0.18 }}
          className={cn(
            "sticky bottom-4 z-10 mx-auto flex max-w-3xl items-center justify-between gap-3 rounded-xl border border-border bg-card px-4 py-2.5 shadow-lg",
            className,
          )}
        >
          <div className="flex items-center gap-3 text-sm">
            <span className="rounded-full bg-primary px-2 py-0.5 text-xs font-semibold text-primary-foreground">
              {count}
            </span>
            <span className="text-muted-foreground">selected</span>
            <button
              type="button"
              onClick={onClear}
              className="text-xs text-muted-foreground hover:text-foreground"
            >
              Clear
            </button>
          </div>
          <div className="flex items-center gap-2">{children}</div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
