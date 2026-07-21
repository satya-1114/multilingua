import { useMemo, useState } from "react";
import type { RetryPolicy, RetryPolicyInput, BackoffStrategy } from "@/types/retry-policy";
import type { ChannelKind } from "@/types/channel";
import type { FailureCategory } from "@/types/delivery";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { retryPolicyService } from "@/services/retry-policy.service";
import { channelLabel } from "./channel-badge";

const CHANNELS: ChannelKind[] = ["email", "sms", "whatsapp", "push", "web_broadcast", "social_broadcast", "voice"];
const CATEGORIES: FailureCategory[] = ["provider_error", "invalid_address", "bounced", "rate_limited", "unsubscribed", "blocked", "timeout", "unknown"];
const BACKOFFS: BackoffStrategy[] = ["fixed", "linear", "exponential"];

interface Props {
  initial?: RetryPolicy;
  onSubmit: (v: RetryPolicyInput) => void;
  onCancel?: () => void;
}

export function RetryPolicyEditor({ initial, onSubmit, onCancel }: Props) {
  const [v, setV] = useState<RetryPolicyInput>({
    name: initial?.name ?? "",
    description: initial?.description ?? "",
    maxAttempts: initial?.maxAttempts ?? 3,
    intervalSeconds: initial?.intervalSeconds ?? 60,
    backoff: initial?.backoff ?? "exponential",
    backoffMultiplier: initial?.backoffMultiplier ?? 2,
    maxIntervalSeconds: initial?.maxIntervalSeconds ?? 3600,
    channels: initial?.channels ?? ["email"],
    retryOn: initial?.retryOn ?? ["provider_error", "timeout"],
  });

  const preview = useMemo(
    () => retryPolicyService.simulateNextAttempts({ ...(initial ?? ({} as RetryPolicy)), ...v } as RetryPolicy),
    [v, initial],
  );

  const toggle = <T,>(list: T[], value: T): T[] =>
    list.includes(value) ? list.filter((x) => x !== value) : [...list, value];

  return (
    <div className="grid gap-5 lg:grid-cols-3">
      <div className="space-y-4 lg:col-span-2">
        <div className="grid gap-2">
          <Label>Name</Label>
          <Input value={v.name} onChange={(e) => setV({ ...v, name: e.target.value })} placeholder="Policy name" />
        </div>
        <div className="grid gap-2">
          <Label>Description</Label>
          <Input value={v.description ?? ""} onChange={(e) => setV({ ...v, description: e.target.value })} />
        </div>
        <div className="grid gap-3 sm:grid-cols-3">
          <div className="grid gap-2">
            <Label>Max attempts</Label>
            <Input type="number" min={1} max={10} value={v.maxAttempts} onChange={(e) => setV({ ...v, maxAttempts: Number(e.target.value) || 1 })} />
          </div>
          <div className="grid gap-2">
            <Label>Interval (s)</Label>
            <Input type="number" min={5} value={v.intervalSeconds} onChange={(e) => setV({ ...v, intervalSeconds: Number(e.target.value) || 5 })} />
          </div>
          <div className="grid gap-2">
            <Label>Backoff</Label>
            <Select value={v.backoff} onValueChange={(val) => setV({ ...v, backoff: val as BackoffStrategy })}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                {BACKOFFS.map((b) => <SelectItem key={b} value={b}>{b}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          <div className="grid gap-2">
            <Label>Multiplier</Label>
            <Input type="number" step={0.1} value={v.backoffMultiplier} onChange={(e) => setV({ ...v, backoffMultiplier: Number(e.target.value) || 1 })} />
          </div>
          <div className="grid gap-2">
            <Label>Max interval (s)</Label>
            <Input type="number" value={v.maxIntervalSeconds} onChange={(e) => setV({ ...v, maxIntervalSeconds: Number(e.target.value) || 60 })} />
          </div>
        </div>

        <div>
          <Label>Channels</Label>
          <div className="mt-2 flex flex-wrap gap-2">
            {CHANNELS.map((c) => {
              const active = v.channels.includes(c);
              return (
                <button
                  key={c}
                  type="button"
                  onClick={() => setV({ ...v, channels: toggle(v.channels, c) })}
                  className={`rounded-full px-3 py-1 text-xs font-medium ring-1 ring-inset transition-colors ${active ? "bg-primary text-primary-foreground ring-primary" : "bg-muted text-muted-foreground ring-border hover:bg-accent"}`}
                >
                  {channelLabel(c)}
                </button>
              );
            })}
          </div>
        </div>

        <div>
          <Label>Retry on failures</Label>
          <div className="mt-2 flex flex-wrap gap-2">
            {CATEGORIES.map((c) => {
              const active = v.retryOn.includes(c);
              return (
                <button
                  key={c}
                  type="button"
                  onClick={() => setV({ ...v, retryOn: toggle(v.retryOn, c) })}
                  className={`rounded-full px-3 py-1 text-xs font-medium ring-1 ring-inset transition-colors ${active ? "bg-primary text-primary-foreground ring-primary" : "bg-muted text-muted-foreground ring-border hover:bg-accent"}`}
                >
                  {c.replace(/_/g, " ")}
                </button>
              );
            })}
          </div>
        </div>

        <div className="flex justify-end gap-2 pt-2">
          {onCancel && <Button variant="outline" onClick={onCancel}>Cancel</Button>}
          <Button onClick={() => onSubmit(v)} disabled={!v.name.trim() || v.channels.length === 0}>Save policy</Button>
        </div>
      </div>

      <Card className="h-fit">
        <CardHeader className="pb-2"><CardTitle className="text-sm">Retry schedule preview</CardTitle></CardHeader>
        <CardContent>
          <ol className="space-y-2 text-sm">
            {preview.map((p) => (
              <li key={p.attempt} className="flex items-center justify-between rounded-lg bg-muted/40 px-3 py-2">
                <span className="font-medium">Attempt {p.attempt}</span>
                <span className="text-muted-foreground">wait {p.delaySec}s</span>
              </li>
            ))}
          </ol>
        </CardContent>
      </Card>
    </div>
  );
}
