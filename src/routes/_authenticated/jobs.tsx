import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { SectionHeader } from "@/components/common/section-header";
import { JobStatusCard } from "@/components/common/job-status-card";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { jobsService } from "@/services/jobs.service";
import type { JobStatus } from "@/types/jobs";

export const Route = createFileRoute("/_authenticated/jobs")({
  component: JobsPage,
});

function JobsPage() {
  const qc = useQueryClient();
  const [status, setStatus] = useState<JobStatus | "all">("all");
  const jobs = useQuery({
    queryKey: ["jobs", status],
    queryFn: () => jobsService.list({ status, pageSize: 50 }),
  });
  const invalidate = () => qc.invalidateQueries({ queryKey: ["jobs"] });
  const retry = useMutation({ mutationFn: (id: string) => jobsService.retry(id), onSuccess: invalidate });
  const cancel = useMutation({ mutationFn: (id: string) => jobsService.cancel(id), onSuccess: invalidate });

  return (
    <div className="space-y-5">
        <SectionHeader
          title="Background jobs"
          description="Track AI generation, translation, delivery and import workloads."
        />
        <Tabs value={status} onValueChange={(v) => setStatus(v as typeof status)}>
          <TabsList>
            <TabsTrigger value="all">All</TabsTrigger>
            <TabsTrigger value="queued">Queued</TabsTrigger>
            <TabsTrigger value="running">Running</TabsTrigger>
            <TabsTrigger value="completed">Completed</TabsTrigger>
            <TabsTrigger value="failed">Failed</TabsTrigger>
          </TabsList>
        </Tabs>
        <div className="grid gap-3">
          {(jobs.data?.data ?? []).map((job) => (
            <JobStatusCard
              key={job.id}
              job={job}
              onRetry={(j) => retry.mutate(j.id)}
              onCancel={(j) => cancel.mutate(j.id)}
            />
          ))}
        </div>
      </div>
  );
}
