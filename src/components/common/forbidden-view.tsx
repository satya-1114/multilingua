import { ShieldAlert } from "lucide-react";
import { Link, useRouter } from "@tanstack/react-router";
import { Button } from "@/components/ui/button";

/**
 * Inline 403 view. Rendered INSIDE the authenticated app shell so the user
 * keeps their sidebar, session, and tokens. Do not navigate to a top-level
 * `/forbidden` route from within `_authenticated` — that swaps out the shell
 * and feels like a forced logout.
 */
export function ForbiddenView() {
  const router = useRouter();
  return (
    <div className="flex min-h-[60vh] items-center justify-center px-4">
      <div className="max-w-md text-center">
        <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-destructive/10">
          <ShieldAlert className="h-6 w-6 text-destructive" aria-hidden="true" />
        </div>
        <p className="mt-4 text-sm font-semibold text-primary">403</p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight text-foreground">
          Access denied
        </h1>
        <p className="mt-2 text-sm text-muted-foreground">
          You don't have permission to view this page. Your session is still active — pick
          another destination below.
        </p>
        <div className="mt-6 flex flex-wrap justify-center gap-2">
          <Button variant="outline" onClick={() => router.history.back()}>
            Go back
          </Button>
          <Button asChild variant="outline">
            <Link to="/dashboard">Dashboard</Link>
          </Button>
          <Button asChild>
            <Link to="/">Home</Link>
          </Button>
        </div>
      </div>
    </div>
  );
}
