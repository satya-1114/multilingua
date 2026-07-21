import { createFileRoute } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { format } from "date-fns";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { SchedulerPanel } from "@/components/common/scheduler-panel";
import { schedulerService } from "@/services/scheduler.service";
import { toast } from "sonner";
import { CalendarClock, Trash2 } from "lucide-react";

export const Route = createFileRoute("/_authenticated/communication/scheduling")({
  component: SchedulingPage,
});

function SchedulingPage() {
  const q = useQuery({ queryKey: ["schedules"], queryFn: () => schedulerService.list() });
  const schedules = q.data ?? [];

  return (
    <div className="grid gap-5 lg:grid-cols-[1fr_1.5fr]">
      <Card className="h-fit">
        <CardHeader className="pb-2"><CardTitle className="text-sm">Scheduled campaigns</CardTitle></CardHeader>
        <CardContent className="space-y-3">
          {schedules.length === 0 && <p className="text-sm text-muted-foreground">No schedules yet.</p>}
          {schedules.map((s) => (
            <div key={s.id} className="rounded-lg border p-3">
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <p className="truncate text-sm font-semibold">{s.campaignName}</p>
                  <p className="mt-0.5 text-xs text-muted-foreground">
                    <CalendarClock className="mr-1 inline h-3 w-3" />
                    {s.mode.toUpperCase()} · {s.timezone}
                  </p>
                  {s.startAt && <p className="text-xs text-muted-foreground">Next · {format(new Date(s.startAt), "PPp")}</p>}
                  {s.recurrence && <p className="text-xs text-muted-foreground">Repeats {s.recurrence.pattern} every {s.recurrence.interval}</p>}
                </div>
                <Button size="icon" variant="ghost" onClick={async () => { await schedulerService.remove(s.id); toast.success("Schedule removed"); q.refetch(); }}>
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            </div>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2"><CardTitle className="text-sm">New / edit schedule</CardTitle></CardHeader>
        <CardContent>
          <SchedulerPanel
            initial={{ campaignId: "cmp-adhoc", campaignName: "Ad hoc broadcast" }}
            onSubmit={async (cfg) => {
              await schedulerService.upsert(cfg);
              toast.success("Schedule saved");
              q.refetch();
            }}
          />
        </CardContent>
      </Card>
    </div>
  );
}
