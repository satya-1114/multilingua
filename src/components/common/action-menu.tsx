import type { ReactNode } from "react";
import type { LucideIcon } from "lucide-react";
import { MoreHorizontal } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

export interface ActionMenuItem {
  key: string;
  label: string;
  icon?: LucideIcon;
  onSelect: () => void;
  destructive?: boolean;
  separatorBefore?: boolean;
}

interface ActionMenuProps {
  items: ActionMenuItem[];
  trigger?: ReactNode;
}

export function ActionMenu({ items, trigger }: ActionMenuProps) {
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        {trigger ?? (
          <Button variant="ghost" size="icon" className="h-8 w-8" aria-label="Open actions">
            <MoreHorizontal className="h-4 w-4" />
          </Button>
        )}
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-44">
        {items.map((item) => (
          <div key={item.key}>
            {item.separatorBefore && <DropdownMenuSeparator />}
            <DropdownMenuItem
              onSelect={item.onSelect}
              className={item.destructive ? "text-destructive focus:text-destructive" : ""}
            >
              {item.icon && <item.icon className="mr-2 h-3.5 w-3.5" />}
              {item.label}
            </DropdownMenuItem>
          </div>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
