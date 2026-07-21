import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ChannelBadge } from "./channel-badge";
import type { ChannelKind } from "@/types/channel";

interface MessagePreviewProps {
  channel: ChannelKind;
  subject?: string;
  body: string;
  sender?: string;
  device?: "mobile" | "desktop";
}

export function MessagePreview({ channel, subject, body, sender, device = "mobile" }: MessagePreviewProps) {
  return (
    <Card className="shadow-card">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm">Preview</CardTitle>
        <ChannelBadge channel={channel} />
      </CardHeader>
      <CardContent>
        <div className={device === "mobile" ? "mx-auto w-[280px] rounded-2xl border-4 border-foreground/80 bg-background p-3" : "rounded-xl border bg-background p-4"}>
          {sender && <p className="text-xs font-semibold text-foreground">{sender}</p>}
          {subject && <p className="mt-1 text-sm font-semibold">{subject}</p>}
          <p className="mt-2 whitespace-pre-wrap text-sm text-muted-foreground">{body}</p>
        </div>
      </CardContent>
    </Card>
  );
}
