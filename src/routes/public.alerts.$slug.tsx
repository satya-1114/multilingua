import { createFileRoute } from "@tanstack/react-router";
import { AlertTriangle } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

/**
 * Public disaster alert page.
 *
 * The backend does not yet expose a public alerts endpoint (see
 * `backend/app/api/v1/disasters.py` — all routes require authenticated
 * `disaster:view`). This page is kept as a stable slug so shared URLs
 * remain resolvable, but shows a friendly notice until the public API
 * lands in a later milestone.
 */
export const Route = createFileRoute("/public/alerts/$slug")({
  head: () => ({
    meta: [
      { title: "Public disaster alert — Multilingua" },
      {
        name: "description",
        content: "Public disaster alerts will be available soon.",
      },
      { name: "robots", content: "noindex" },
    ],
  }),
  component: PublicAlertPage,
});

function PublicAlertPage() {
  return (
    <div className="min-h-screen bg-background">
      <div className="mx-auto max-w-2xl px-4 py-12">
        <Card className="shadow-card">
          <CardHeader className="flex flex-row items-center gap-3 space-y-0 pb-2">
            <AlertTriangle className="h-5 w-5 text-amber-600" />
            <CardTitle className="text-base">Public alerts coming soon</CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground">
            <p>
              Public disaster alert pages are being prepared. Please check
              back once the public information channel is live.
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
