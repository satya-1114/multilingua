import { createFileRoute, Link } from "@tanstack/react-router";
import { ShieldAlert } from "lucide-react";
import { Button } from "@/components/ui/button";

export const Route = createFileRoute("/forbidden")({
  head: () => ({
    meta: [
      { title: "Access denied — Multilingua" },
      { name: "robots", content: "noindex" },
    ],
  }),
  component: ForbiddenPage,
});

function ForbiddenPage() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <div className="max-w-md text-center">
        <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-destructive/10">
          <ShieldAlert className="h-6 w-6 text-destructive" />
        </div>
        <p className="mt-4 text-sm font-semibold text-primary">403</p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight text-foreground">
          Access denied
        </h1>
        <p className="mt-2 text-sm text-muted-foreground">
          You don't have permission to view this resource. Contact your workspace admin if
          you believe this is an error.
        </p>
        <div className="mt-6 flex justify-center gap-2">
          <Button asChild variant="outline">
            <Link to="/dashboard">Go to dashboard</Link>
          </Button>
          <Button asChild>
            <Link to="/">Home</Link>
          </Button>
        </div>
      </div>
    </div>
  );
}
