import { useEffect } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { Globe, Share2 } from "lucide-react";
import { toast } from "sonner";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { SkeletonBlock } from "@/components/common/skeleton-block";
import { ErrorState } from "@/components/common/error-state";
import { publicAccessService } from "@/services/public-access.service";
import type { PublicResource } from "@/types/public-access";

export const Route = createFileRoute("/p/$slug")({
  head: () => ({
    meta: [
      { title: "Public information — Multilingua" },
      { name: "description", content: "Public information page." },
      { name: "robots", content: "index,follow" },
    ],
  }),
  component: PublicSlugPage,
});

function PublicSlugPage() {
  const { slug } = Route.useParams();
  const q = useQuery({
    queryKey: ["public-slug", slug],
    queryFn: () => publicAccessService.resolveBySlug(slug),
    retry: false,
  });

  useEffect(() => {
    if (!q.data) return;
    publicAccessService
      .registerViewBySlug(slug, { deviceType: detectDevice() })
      .catch(() => { /* non-fatal */ });
  }, [q.data, slug]);

  if (q.isLoading) return <PublicShell><SkeletonBlock rows={8} /></PublicShell>;
  if (q.isError || !q.data)
    return (
      <PublicShell>
        <ErrorState
          title="Not available"
          description="This resource is unavailable or has been unpublished."
          onRetry={() => q.refetch()}
        />
      </PublicShell>
    );

  return (
    <PublicShell>
      <ResourceView resource={q.data} />
    </PublicShell>
  );
}

export function ResourceView({ resource: r }: { resource: PublicResource }) {
  const shareUrl = typeof window !== "undefined" ? window.location.href : "";
  async function share() {
    try {
      if (navigator.share) {
        await navigator.share({ title: r.title, text: r.description ?? "", url: shareUrl });
      } else {
        await navigator.clipboard.writeText(shareUrl);
        toast.success("Link copied");
      }
    } catch { /* cancelled */ }
  }
  return (
    <div className="mx-auto max-w-3xl space-y-6 px-4 py-10">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div className="space-y-2">
          <Badge variant="secondary" className="uppercase tracking-wide">
            {r.resourceType.replace(/_/g, " ")}
          </Badge>
          <h1 className="text-3xl font-semibold tracking-tight text-foreground">{r.title}</h1>
        </div>
        <Button size="sm" variant="outline" className="gap-1.5" onClick={share}>
          <Share2 className="h-4 w-4" /> Share
        </Button>
      </header>
      {r.description && (
        <Card className="shadow-card">
          <CardHeader className="pb-2">
            <CardTitle className="text-base flex items-center gap-2">
              <Globe className="h-4 w-4" /> About
            </CardTitle>
          </CardHeader>
          <CardContent className="whitespace-pre-line text-sm text-foreground/90">
            {r.description}
          </CardContent>
        </Card>
      )}
      {r.expiresAt && (
        <p className="text-xs text-muted-foreground">
          Available until {new Date(r.expiresAt).toLocaleString()}
        </p>
      )}
      <footer className="pt-8 text-center text-xs text-muted-foreground">
        Powered by Multilingua
      </footer>
    </div>
  );
}

export function PublicShell({ children }: { children: React.ReactNode }) {
  return <div className="min-h-screen bg-background">{children}</div>;
}

export function detectDevice(): "mobile" | "tablet" | "desktop" | "unknown" {
  if (typeof navigator === "undefined") return "unknown";
  const ua = navigator.userAgent;
  if (/Mobi|Android/i.test(ua) && !/iPad|Tablet/i.test(ua)) return "mobile";
  if (/iPad|Tablet/i.test(ua)) return "tablet";
  return "desktop";
}
