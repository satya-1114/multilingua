import { useEffect } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { SkeletonBlock } from "@/components/common/skeleton-block";
import { ErrorState } from "@/components/common/error-state";
import { publicAccessService } from "@/services/public-access.service";
import { PublicShell, ResourceView, detectDevice } from "./p.$slug";

export const Route = createFileRoute("/q/$token")({
  head: () => ({
    meta: [
      { title: "Public information — Multilingua" },
      { name: "description", content: "Public information page accessed via QR code." },
      { name: "robots", content: "index,follow" },
    ],
  }),
  component: PublicQrPage,
});

function PublicQrPage() {
  const { token } = Route.useParams();
  const q = useQuery({
    queryKey: ["public-qr", token],
    queryFn: () => publicAccessService.resolveByToken(token),
    retry: false,
  });

  useEffect(() => {
    if (!q.data) return;
    publicAccessService
      .registerViewByToken(token, { deviceType: detectDevice() })
      .catch(() => { /* non-fatal */ });
  }, [q.data, token]);

  if (q.isLoading) return <PublicShell><SkeletonBlock rows={8} /></PublicShell>;
  if (q.isError || !q.data)
    return (
      <PublicShell>
        <ErrorState
          title="Not available"
          description="This QR code is inactive or the resource has been unpublished."
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
