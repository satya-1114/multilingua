import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { formatDistanceToNow } from "date-fns";
import { Archive, Pin, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { SectionHeader } from "@/components/common/section-header";
import { LanguageBadge } from "@/components/common/language-badge";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { draftService } from "@/services/draft.service";
import type { AiDraft } from "@/types/ai";

export const Route = createFileRoute("/_authenticated/ai/drafts")({
  component: AiDraftsPage,
});

function AiDraftsPage() {
  const qc = useQueryClient();
  const [tab, setTab] = useState<"active" | "archived" | "pinned">("active");

  const drafts = useQuery({
    queryKey: ["drafts", tab],
    queryFn: () =>
      draftService.list({
        archived: tab === "archived",
        pinnedOnly: tab === "pinned",
        pageSize: 100,
      }),
  });

  const invalidate = () => qc.invalidateQueries({ queryKey: ["drafts"] });

  const pin = useMutation({
    mutationFn: (d: AiDraft) => draftService.pin(d.id, !d.pinned),
    onSuccess: invalidate,
  });
  const archive = useMutation({
    mutationFn: (d: AiDraft) => draftService.archive(d.id),
    onSuccess: () => {
      invalidate();
      toast.success("Draft archived");
    },
  });
  const remove = useMutation({
    mutationFn: (d: AiDraft) => draftService.remove(d.id),
    onSuccess: () => {
      invalidate();
      toast.success("Draft deleted");
    },
  });

  return (
    <div className="space-y-5">
        <SectionHeader
          title="Saved drafts"
          description="Autosaved and pinned drafts across all AI Studio sessions."
        />
        <Tabs value={tab} onValueChange={(v) => setTab(v as typeof tab)}>
          <TabsList>
            <TabsTrigger value="active">Active</TabsTrigger>
            <TabsTrigger value="pinned">Pinned</TabsTrigger>
            <TabsTrigger value="archived">Archived</TabsTrigger>
          </TabsList>
        </Tabs>
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {(drafts.data?.data ?? []).map((d) => (
            <Card key={d.id}>
              <CardContent className="flex h-full flex-col gap-2 p-4">
                <div className="flex items-start justify-between gap-2">
                  <p className="line-clamp-1 text-sm font-semibold text-foreground">
                    {d.title}
                  </p>
                  <LanguageBadge code={d.language} />
                </div>
                <p className="line-clamp-3 text-xs text-muted-foreground">{d.content}</p>
                <div className="mt-auto flex items-center justify-between text-[11px] text-muted-foreground">
                  <span>updated {formatDistanceToNow(new Date(d.updatedAt))} ago</span>
                  <div className="flex items-center gap-1">
                    <Button size="icon" variant="ghost" onClick={() => pin.mutate(d)}>
                      <Pin className={d.pinned ? "h-3.5 w-3.5 fill-current" : "h-3.5 w-3.5"} />
                    </Button>
                    {!d.archived && (
                      <Button size="icon" variant="ghost" onClick={() => archive.mutate(d)}>
                        <Archive className="h-3.5 w-3.5" />
                      </Button>
                    )}
                    <Button size="icon" variant="ghost" onClick={() => remove.mutate(d)}>
                      <Trash2 className="h-3.5 w-3.5" />
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
  );
}
