import { format } from "date-fns";
import { cn } from "@/lib/utils";
import type { LogEntry } from "@/types/monitoring";

const levelStyles: Record<LogEntry["level"], string> = {
  info: "bg-primary/10 text-primary",
  warning: "bg-warning/10 text-warning",
  error: "bg-destructive/10 text-destructive",
  debug: "bg-muted text-muted-foreground",
};

export function MonitoringTable({ rows }: { rows: LogEntry[] }) {
  return (
    <div className="overflow-hidden rounded-xl border">
      <table className="w-full text-sm">
        <thead className="bg-muted/40 text-xs uppercase text-muted-foreground">
          <tr>
            <th className="px-3 py-2 text-left font-medium">Time</th>
            <th className="px-3 py-2 text-left font-medium">Level</th>
            <th className="px-3 py-2 text-left font-medium">Service</th>
            <th className="px-3 py-2 text-left font-medium">Message</th>
            <th className="px-3 py-2 text-left font-medium">Actor</th>
            <th className="px-3 py-2 text-left font-medium">Request</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border">
          {rows.map((r) => (
            <tr key={r.id} className="hover:bg-muted/30">
              <td className="whitespace-nowrap px-3 py-2 text-xs font-mono text-muted-foreground">
                {format(new Date(r.at), "MMM d HH:mm:ss")}
              </td>
              <td className="px-3 py-2">
                <span className={cn("inline-flex rounded-md px-2 py-0.5 text-[11px] font-semibold uppercase", levelStyles[r.level])}>
                  {r.level}
                </span>
              </td>
              <td className="px-3 py-2 text-xs">{r.service}</td>
              <td className="px-3 py-2">{r.message}</td>
              <td className="px-3 py-2 text-xs text-muted-foreground">{r.actor ?? "—"}</td>
              <td className="px-3 py-2 font-mono text-[11px] text-muted-foreground">{r.requestId}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
