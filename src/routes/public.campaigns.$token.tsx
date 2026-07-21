import { useState } from "react";
import { createFileRoute, useSearch } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { z } from "zod";
import { Download, Share2, Globe, ExternalLink } from "lucide-react";
import { toast } from "sonner";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { SkeletonBlock } from "@/components/common/skeleton-block";
import { ErrorState } from "@/components/common/error-state";
import { qrService } from "@/services/qr.service";
import { LANGUAGES } from "@/constants/india";

const searchSchema = z.object({ lang: z.string().optional() });

/**
 * Public, unauthenticated campaign landing page — the destination of a
 * campaign QR scan. Located outside the `_authenticated` layout so no
 * session is required. Backend records the scan when this loads.
 */
export const Route = createFileRoute("/public/campaigns/$token")({
  validateSearch: (s) => searchSchema.parse(s),
  head: ({ loaderData }: { loaderData?: { title?: string } }) => ({
    meta: [
      { title: loaderData?.title ? `${loaderData.title} — Multilingua` : "Campaign — Multilingua" },
      { name: "description", content: "Public campaign page — scan and view campaign details." },
      { name: "robots", content: "index,follow" },
    ],
  }),
  component: PublicCampaignPage,
});

function PublicCampaignPage() {
  const { token } = Route.useParams();
  const { lang } = useSearch({ from: Route.id });
  const storageKey = `multilingua:public-lang:${token}`;
  const [language, setLanguageState] = useState<string>(() => {
    if (lang) return lang;
    if (typeof window !== "undefined") {
      const saved = window.localStorage.getItem(storageKey);
      if (saved) return saved;
    }
    return "en";
  });
  const setLanguage = (next: string) => {
    setLanguageState(next);
    if (typeof window !== "undefined") window.localStorage.setItem(storageKey, next);
  };

  const q = useQuery({
    queryKey: ["public-campaign", token, language],
    queryFn: () => qrService.public(token, { language }),
  });

  if (q.isLoading) return <PublicShell><SkeletonBlock rows={10} /></PublicShell>;
  if (q.isError || !q.data)
    return (
      <PublicShell>
        <ErrorState
          title="Campaign unavailable"
          description="This QR code may have been disabled or the campaign is no longer public."
          onRetry={() => q.refetch()}
        />
      </PublicShell>
    );

  const c = q.data;
  const shareUrl = typeof window !== "undefined" ? window.location.href : "";

  async function share() {
    try {
      if (navigator.share) {
        await navigator.share({ title: c.title, text: c.description ?? "", url: shareUrl });
      } else {
        await navigator.clipboard.writeText(shareUrl);
        toast.success("Link copied");
      }
    } catch {
      /* user cancelled */
    }
  }

  return (
    <PublicShell>
      <div className="mx-auto max-w-4xl space-y-6 px-4 py-8">
        <header className="flex flex-wrap items-start justify-between gap-4">
          <div className="space-y-2">
            {c.organizationName && (
              <Badge variant="secondary" className="uppercase tracking-wide">{c.organizationName}</Badge>
            )}
            <h1 className="text-3xl font-semibold tracking-tight text-foreground">{c.title}</h1>
            {c.description && <p className="max-w-2xl text-sm text-muted-foreground">{c.description}</p>}
          </div>
          <div className="flex items-center gap-2">
            {c.languages.length > 0 && (
              <div className="flex items-center gap-2">
                <Globe className="h-4 w-4 text-muted-foreground" />
                <Select value={language} onValueChange={setLanguage}>
                  <SelectTrigger className="w-[160px]">
                    <SelectValue placeholder="Language" />
                  </SelectTrigger>
                  <SelectContent>
                    {c.languages.map((code) => {
                      const opt = LANGUAGES.find((l) => l.code === code);
                      return (
                        <SelectItem key={code} value={code}>
                          {opt?.label ?? code.toUpperCase()}
                        </SelectItem>
                      );
                    })}
                  </SelectContent>
                </Select>
              </div>
            )}
            <Button size="sm" variant="outline" className="gap-1.5" onClick={share}>
              <Share2 className="h-4 w-4" /> Share
            </Button>
          </div>
        </header>

        {c.audioUrl && (
          <Card className="shadow-card">
            <CardHeader className="pb-2"><CardTitle className="text-base">Listen</CardTitle></CardHeader>
            <CardContent>
              {/* eslint-disable-next-line jsx-a11y/media-has-caption */}
              <audio src={c.audioUrl} controls className="w-full" />
            </CardContent>
          </Card>
        )}

        {c.images.length > 0 && (
          <div className="grid gap-3 sm:grid-cols-2">
            {c.images.map((img, i) => (
              <img
                key={i}
                src={img.url}
                alt={img.alt ?? c.title}
                className="w-full rounded-lg border object-cover"
                loading="lazy"
              />
            ))}
          </div>
        )}

        {c.videos.length > 0 && (
          <div className="grid gap-3">
            {c.videos.map((v, i) => (
              // eslint-disable-next-line jsx-a11y/media-has-caption
              <video key={i} src={v.url} poster={v.poster} controls className="w-full rounded-lg border" />
            ))}
          </div>
        )}

        {c.resources.length > 0 && (
          <Card className="shadow-card">
            <CardHeader className="pb-2"><CardTitle className="text-base">Resources</CardTitle></CardHeader>
            <CardContent>
              <ul className="divide-y">
                {c.resources.map((r) => (
                  <li key={r.url} className="flex items-center justify-between py-2 text-sm">
                    <span className="truncate">{r.name}</span>
                    <Button asChild size="sm" variant="ghost" className="gap-1.5">
                      <a href={r.url} target="_blank" rel="noopener noreferrer" download>
                        <Download className="h-4 w-4" /> Download
                      </a>
                    </Button>
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>
        )}

        <footer className="pt-6 text-center text-xs text-muted-foreground">
          <a href="/" className="inline-flex items-center gap-1 hover:text-foreground">
            Powered by Multilingua <ExternalLink className="h-3 w-3" />
          </a>
        </footer>
      </div>
    </PublicShell>
  );
}

function PublicShell({ children }: { children: React.ReactNode }) {
  return <div className="min-h-screen bg-background">{children}</div>;
}
