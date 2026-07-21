import type { ReactNode } from "react";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription, SheetFooter } from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";

interface FilterDrawerProps {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  title?: string;
  description?: string;
  onApply?: () => void;
  onReset?: () => void;
  children: ReactNode;
}

export function FilterDrawer({
  open,
  onOpenChange,
  title = "Filters",
  description = "Refine the list below.",
  onApply,
  onReset,
  children,
}: FilterDrawerProps) {
  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="w-full max-w-md overflow-y-auto">
        <SheetHeader>
          <SheetTitle>{title}</SheetTitle>
          <SheetDescription>{description}</SheetDescription>
        </SheetHeader>
        <div className="mt-6 space-y-5">{children}</div>
        <SheetFooter className="mt-6 flex-row justify-between gap-2">
          <Button variant="ghost" onClick={onReset}>Reset</Button>
          <Button onClick={() => { onApply?.(); onOpenChange(false); }}>Apply filters</Button>
        </SheetFooter>
      </SheetContent>
    </Sheet>
  );
}
