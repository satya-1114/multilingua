import { APP_NAME } from "@/constants/navigation";

export function AppFooter() {
  return (
    <footer className="border-t border-border bg-card px-6 py-4">
      <div className="flex flex-col items-center justify-between gap-2 text-xs text-muted-foreground sm:flex-row">
        <p>
          &copy; {new Date().getFullYear()} {APP_NAME}. All rights reserved.
        </p>
        <div className="flex items-center gap-4">
          <a href="#" className="hover:text-foreground">Privacy</a>
          <a href="#" className="hover:text-foreground">Terms</a>
          <a href="#" className="hover:text-foreground">Support</a>
          <span>v1.0.0</span>
        </div>
      </div>
    </footer>
  );
}
