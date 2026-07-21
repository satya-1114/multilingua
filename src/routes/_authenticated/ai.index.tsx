import { createFileRoute, Link } from "@tanstack/react-router";
import { motion } from "framer-motion";
import { useQuery } from "@tanstack/react-query";
import {
  Sparkles,
  History,
  FileText,
  Languages,
  Wand2,
  BookOpen,
  Activity,
} from "lucide-react";
import { SectionHeader } from "@/components/common/section-header";
import { StatCard } from "@/components/common/stat-card";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { historyService } from "@/services/history.service";
import { draftService } from "@/services/draft.service";
import { promptService } from "@/services/prompt.service";
import { jobsService } from "@/services/jobs.service";
import { LanguageBadge } from "@/components/common/language-badge";
import { formatDistanceToNow } from "date-fns";

export const Route = createFileRoute("/_authenticated/ai/")({
  component: AiDashboardPage,
});

function AiDashboardPage() {
  const history = useQuery({
    queryKey: ["ai-history", { pageSize: 5 }],
    queryFn: () => historyService.list({ pageSize: 5 }),
  });
  const drafts = useQuery({
    queryKey: ["ai-drafts", { pageSize: 5 }],
    queryFn: () => draftService.list({ pageSize: 5 }),
  });
  const prompts = useQuery({
    queryKey: ["ai-prompts", { pageSize: 6 }],
    queryFn: () => promptService.list({ pageSize: 6 }),
  });
  const jobs = useQuery({
    queryKey: ["ai-jobs", { pageSize: 3 }],
    queryFn: () => jobsService.list({ pageSize: 3 }),
  });

  const totalGenerations = history.data?.pagination.total ?? 0;
  const activeDrafts = drafts.data?.pagination.total ?? 0;
  const promptLibrary = prompts.data?.pagination.total ?? 0;
  const runningJobs =
    jobs.data?.data.filter((j) => j.status === "running").length ?? 0;

  return (
    <div className="space-y-6">
        <SectionHeader
          title="AI Content Studio"
          description="Draft, translate and review multilingual public communication with your organisation's guardrails."
          actions={
            <div className="flex gap-2">
              <Button variant="outline" asChild>
                <Link to="/ai/prompts">
                  <BookOpen className="mr-1.5 h-4 w-4" /> Prompt library
                </Link>
              </Button>
              <Button asChild>
                <Link to="/ai/workspace">
                  <Wand2 className="mr-1.5 h-4 w-4" /> Open workspace
                </Link>
              </Button>
            </div>
          }
        />

        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <StatCard
            label="Generations this month"
            value={totalGenerations.toString()}
            trend="up"
            delta="+12.4%"
            helper="vs last month"
            icon={Sparkles}
            index={0}
          />
          <StatCard
            label="Active drafts"
            value={activeDrafts.toString()}
            trend="flat"
            helper="auto-saved"
            icon={FileText}
            index={1}
          />
          <StatCard
            label="Prompt templates"
            value={promptLibrary.toString()}
            trend="up"
            delta="+3"
            helper="new this week"
            icon={BookOpen}
            index={2}
          />
          <StatCard
            label="Jobs in progress"
            value={runningJobs.toString()}
            trend="flat"
            helper="translation & delivery"
            icon={Activity}
            index={3}
          />
        </div>

        <div className="grid gap-4 lg:grid-cols-3">
          <Card className="lg:col-span-2">
            <CardContent className="p-5">
              <div className="mb-4 flex items-center justify-between">
                <div>
                  <p className="text-sm font-semibold text-foreground">Recent generations</p>
                  <p className="text-xs text-muted-foreground">
                    Latest AI drafts across languages and channels.
                  </p>
                </div>
                <Button variant="ghost" size="sm" asChild>
                  <Link to="/ai/history">
                    <History className="mr-1.5 h-3.5 w-3.5" /> View all
                  </Link>
                </Button>
              </div>
              <ul className="divide-y divide-border/60">
                {(history.data?.data ?? []).map((entry, i) => (
                  <motion.li
                    key={entry.id}
                    initial={{ opacity: 0, y: 4 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: i * 0.03 }}
                    className="flex items-start justify-between gap-3 py-3"
                  >
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium text-foreground">
                        {entry.title}
                      </p>
                      <p className="mt-0.5 text-xs text-muted-foreground">
                        {entry.createdBy} · {formatDistanceToNow(new Date(entry.createdAt))} ago
                      </p>
                    </div>
                    <LanguageBadge code={entry.language} />
                  </motion.li>
                ))}
              </ul>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-5">
              <div className="mb-4 flex items-center justify-between">
                <div>
                  <p className="text-sm font-semibold text-foreground">Pinned drafts</p>
                  <p className="text-xs text-muted-foreground">Continue where you left off.</p>
                </div>
                <Button variant="ghost" size="sm" asChild>
                  <Link to="/ai/drafts">All drafts</Link>
                </Button>
              </div>
              <ul className="space-y-3">
                {(drafts.data?.data ?? []).slice(0, 4).map((d) => (
                  <li key={d.id} className="rounded-lg border border-border/70 bg-muted/20 p-3">
                    <p className="line-clamp-1 text-sm font-medium text-foreground">
                      {d.title}
                    </p>
                    <p className="mt-0.5 line-clamp-2 text-xs text-muted-foreground">
                      {d.content}
                    </p>
                    <div className="mt-2 flex items-center justify-between text-[11px] text-muted-foreground">
                      <LanguageBadge code={d.language} />
                      <span>updated {formatDistanceToNow(new Date(d.updatedAt))} ago</span>
                    </div>
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>
        </div>

        <Card>
          <CardContent className="p-5">
            <div className="mb-3 flex items-center justify-between">
              <div>
                <p className="text-sm font-semibold text-foreground">Featured prompts</p>
                <p className="text-xs text-muted-foreground">
                  Curated starters for common public communication scenarios.
                </p>
              </div>
              <Button variant="ghost" size="sm" asChild>
                <Link to="/translation">
                  <Languages className="mr-1.5 h-3.5 w-3.5" /> Open translation
                </Link>
              </Button>
            </div>
            <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
              {(prompts.data?.data ?? []).slice(0, 6).map((p) => (
                <div
                  key={p.id}
                  className="rounded-lg border border-border/70 bg-card p-3 transition-shadow hover:shadow-elevated"
                >
                  <p className="text-sm font-semibold text-foreground">{p.title}</p>
                  <p className="mt-1 line-clamp-2 text-xs text-muted-foreground">
                    {p.description}
                  </p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
  );
}
