import { useMemo, useRef, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import QRCode from "qrcode";
import {
  QrCode,
  RefreshCw,
  Download,
  Link2,
  Printer,
  Power,
  Globe,
  Smartphone,
  Monitor,
  Tablet,
  Scan,
} from "lucide-react";
import { toast } from "sonner";
import { formatDistanceToNow } from "date-fns";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { SkeletonBlock } from "@/components/common/skeleton-block";
import { EmptyState } from "@/components/common/empty-state";
import { AnalyticsCard } from "@/components/common/analytics-card";
import { ConfirmDialog } from "@/components/common/confirm-dialog";
import { PermissionGuard } from "@/components/common/permission-guard";
import { PERMISSIONS } from "@/constants/rbac";
import { qrService } from "@/services/qr.service";
import type { QrDeviceType } from "@/types/qr";
import { cn } from "@/lib/utils";

interface CampaignQrPanelProps {
  campaignId: string;
  campaignName: string;
}

const DEVICE_ICON: Record<QrDeviceType, typeof Smartphone> = {
  mobile: Smartphone,
  tablet: Tablet,
  desktop: Monitor,
  unknown: Globe,
};

/**
 * Campaign QR management panel — embedded inside the Campaign Details page.
 * Reuses existing card, button, badge, analytics-card, empty-state and
 * confirm-dialog primitives to preserve the platform's look and feel.
 */
export function CampaignQrPanel({ campaignId, campaignName }: CampaignQrPanelProps) {
  const qc = useQueryClient();
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [confirmRegen, setConfirmRegen] = useState(false);
  const [confirmDisable, setConfirmDisable] = useState<null | "disable" | "enable">(null);

  const qrQ = useQuery({
    queryKey: ["campaign-qr", campaignId],
    queryFn: () => qrService.get(campaignId),
  });
  const analyticsQ = useQuery({
    queryKey: ["campaign-qr-analytics", campaignId],
    queryFn: () => qrService.analytics(campaignId),
    enabled: !!qrQ.data,
  });

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ["campaign-qr", campaignId] });
    qc.invalidateQueries({ queryKey: ["campaign-qr-analytics", campaignId] });
  };

  const generateM = useMutation({
    mutationFn: () => qrService.generate(campaignId),
    onSuccess: () => { toast.success("QR code generated"); invalidate(); },
    onError: (e: Error) => toast.error(e.message || "Could not generate QR code"),
  });
  const regenM = useMutation({
    mutationFn: () => qrService.regenerate(campaignId),
    onSuccess: () => { toast.success("QR code regenerated"); invalidate(); },
    onError: (e: Error) => toast.error(e.message || "Could not regenerate QR code"),
  });
  const statusM = useMutation({
    mutationFn: (status: "active" | "disabled") => qrService.setStatus(campaignId, status),
    onSuccess: (data) => { toast.success(`QR ${data.status === "active" ? "enabled" : "disabled"}`); invalidate(); },
    onError: (e: Error) => toast.error(e.message || "Could not update QR status"),
  });

  const qr = qrQ.data ?? null;

  // Render preview client-side from the backend-supplied target URL.
  useMemo(() => {
    if (!qr || !canvasRef.current) return;
    QRCode.toCanvas(canvasRef.current, qr.targetUrl, { width: 240, margin: 2, errorCorrectionLevel: "M" }).catch(() => {
      /* rendering failure is non-fatal — download actions surface errors */
    });
  }, [qr]);

  async function download(kind: "png" | "svg") {
    if (!qr) return;
    try {
      const filename = `${campaignName.replace(/[^a-z0-9-]+/gi, "-").toLowerCase()}-qr.${kind}`;
      const data =
        kind === "png"
          ? await QRCode.toDataURL(qr.targetUrl, { width: 1024, margin: 2, errorCorrectionLevel: "M" })
          : "data:image/svg+xml;utf8," + encodeURIComponent(await QRCode.toString(qr.targetUrl, { type: "svg", margin: 2, errorCorrectionLevel: "M" }));
      const a = document.createElement("a");
      a.href = data;
      a.download = filename;
      a.click();
    } catch {
      toast.error("Download failed");
    }
  }

  async function copyLink() {
    if (!qr) return;
    try {
      await navigator.clipboard.writeText(qr.targetUrl);
      toast.success("Campaign link copied");
    } catch {
      toast.error("Copy failed");
    }
  }

  async function printQr() {
    if (!qr) return;
    const dataUrl = await QRCode.toDataURL(qr.targetUrl, { width: 512, margin: 2, errorCorrectionLevel: "M" });
    const w = window.open("", "_blank", "width=520,height=640");
    if (!w) return;
    w.document.write(`<!doctype html><title>${campaignName} — QR</title>
      <body style="font-family:system-ui;text-align:center;padding:32px;">
        <h1 style="font-size:20px;margin:0 0 16px;">${campaignName}</h1>
        <img src="${dataUrl}" alt="Campaign QR" style="width:320px;height:320px;" />
        <p style="font-size:12px;color:#555;margin-top:16px;word-break:break-all;">${qr.targetUrl}</p>
        <script>window.onload=()=>window.print();</script>
      </body>`);
    w.document.close();
  }

  if (qrQ.isLoading) return <SkeletonBlock rows={6} />;

  return (
    <div className="space-y-4">
      <Card className="shadow-card">
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="flex items-center gap-2 text-base">
            <QrCode className="h-4 w-4" /> Campaign QR code
            {qr && (
              <Badge variant={qr.status === "active" ? "default" : "secondary"} className="ml-2 capitalize">
                {qr.status}
              </Badge>
            )}
          </CardTitle>
          <PermissionGuard anyOf={[PERMISSIONS.CAMPAIGN_QR_MANAGE]}>
            {!qr ? (
              <Button size="sm" className="gap-1.5" onClick={() => generateM.mutate()} disabled={generateM.isPending}>
                <QrCode className="h-4 w-4" /> Generate QR
              </Button>
            ) : (
              <div className="flex flex-wrap gap-2">
                <Button size="sm" variant="outline" className="gap-1.5" onClick={() => setConfirmRegen(true)}>
                  <RefreshCw className="h-4 w-4" /> Regenerate
                </Button>
                <Button
                  size="sm"
                  variant={qr.status === "active" ? "outline" : "default"}
                  className="gap-1.5"
                  onClick={() => setConfirmDisable(qr.status === "active" ? "disable" : "enable")}
                >
                  <Power className="h-4 w-4" /> {qr.status === "active" ? "Disable" : "Enable"}
                </Button>
              </div>
            )}
          </PermissionGuard>
        </CardHeader>
        <CardContent>
          {!qr ? (
            <EmptyState
              icon={QrCode}
              title="No QR code yet"
              description="Generate a QR code so audiences can scan and open this campaign's public page."
            />
          ) : (
            <div className="grid gap-6 md:grid-cols-[240px_1fr]">
              <div className="flex flex-col items-center gap-3">
                <div className={cn("rounded-lg border bg-white p-3", qr.status === "disabled" && "opacity-50")}>
                  <canvas ref={canvasRef} aria-label="Campaign QR preview" />
                </div>
                <p className="text-xs text-muted-foreground">v{qr.version} · Updated {formatDistanceToNow(new Date(qr.updatedAt), { addSuffix: true })}</p>
              </div>
              <div className="space-y-3">
                <div className="rounded-md border bg-muted/40 p-3 text-xs">
                  <p className="uppercase tracking-wide text-muted-foreground">Public link</p>
                  <p className="mt-1 break-all font-mono text-foreground">{qr.targetUrl}</p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <Button size="sm" variant="outline" className="gap-1.5" onClick={() => download("png")}>
                    <Download className="h-4 w-4" /> PNG
                  </Button>
                  <Button size="sm" variant="outline" className="gap-1.5" onClick={() => download("svg")}>
                    <Download className="h-4 w-4" /> SVG
                  </Button>
                  <Button size="sm" variant="outline" className="gap-1.5" onClick={copyLink}>
                    <Link2 className="h-4 w-4" /> Copy link
                  </Button>
                  <Button size="sm" variant="outline" className="gap-1.5" onClick={printQr}>
                    <Printer className="h-4 w-4" /> Print
                  </Button>
                </div>
                <p className="text-xs text-muted-foreground">
                  Regenerating rotates the token — previously-printed codes will stop working.
                </p>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {qr && (
        <>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <AnalyticsCard label="Total scans" value={analyticsQ.data?.totalScans ?? qr.totalScans} icon={Scan} />
            <AnalyticsCard label="Unique scans" value={analyticsQ.data?.uniqueScans ?? qr.uniqueScans} icon={Globe} />
            <AnalyticsCard
              label="Last scan"
              value={
                (analyticsQ.data?.lastScanAt ?? qr.lastScanAt)
                  ? formatDistanceToNow(new Date((analyticsQ.data?.lastScanAt ?? qr.lastScanAt) as string), { addSuffix: true })
                  : "—"
              }
              icon={RefreshCw}
            />
            <AnalyticsCard
              label="Top device"
              value={analyticsQ.data?.byDevice?.[0]?.device ?? "—"}
              helper={analyticsQ.data?.byDevice?.[0] ? `${analyticsQ.data.byDevice[0].count} scans` : undefined}
              icon={Smartphone}
            />
          </div>

          <Card className="shadow-card">
            <CardHeader className="pb-2"><CardTitle className="text-base">Scan breakdown</CardTitle></CardHeader>
            <CardContent className="grid gap-6 md:grid-cols-3">
              <BreakdownList
                title="By country"
                empty="No country data yet"
                rows={(analyticsQ.data?.byCountry ?? []).map((r) => ({ label: r.country, value: r.count }))}
              />
              <BreakdownList
                title="By device"
                empty="No device data yet"
                rows={(analyticsQ.data?.byDevice ?? []).map((r) => ({
                  label: r.device,
                  value: r.count,
                  icon: DEVICE_ICON[r.device],
                }))}
              />
              <BreakdownList
                title="By language selected"
                empty="No language data yet"
                rows={(analyticsQ.data?.byLanguage ?? []).map((r) => ({ label: r.language.toUpperCase(), value: r.count }))}
              />
            </CardContent>
          </Card>
        </>
      )}

      <ConfirmDialog
        open={confirmRegen}
        onOpenChange={setConfirmRegen}
        title="Regenerate QR code?"
        description="This rotates the token. Any previously printed or shared code will stop working immediately."
        destructive
        confirmLabel="Regenerate"
        onConfirm={async () => { await regenM.mutateAsync(); setConfirmRegen(false); }}
      />
      <ConfirmDialog
        open={!!confirmDisable}
        onOpenChange={(o) => !o && setConfirmDisable(null)}
        title={confirmDisable === "disable" ? "Disable QR code?" : "Enable QR code?"}
        description={
          confirmDisable === "disable"
            ? "Scans will be blocked until the code is enabled again."
            : "Scans will resume immediately."
        }
        confirmLabel={confirmDisable === "disable" ? "Disable" : "Enable"}
        onConfirm={async () => {
          await statusM.mutateAsync(confirmDisable === "disable" ? "disabled" : "active");
          setConfirmDisable(null);
        }}
      />
    </div>
  );
}

function BreakdownList({
  title,
  rows,
  empty,
}: {
  title: string;
  empty: string;
  rows: { label: string; value: number; icon?: typeof Smartphone }[];
}) {
  const total = rows.reduce((s, r) => s + r.value, 0);
  return (
    <div>
      <p className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">{title}</p>
      {rows.length === 0 ? (
        <p className="text-sm text-muted-foreground">{empty}</p>
      ) : (
        <ul className="space-y-2">
          {rows.slice(0, 6).map((r) => {
            const pct = total ? Math.round((r.value / total) * 100) : 0;
            const Icon = r.icon;
            return (
              <li key={r.label} className="space-y-1">
                <div className="flex items-center justify-between text-sm">
                  <span className="flex items-center gap-1.5 capitalize">
                    {Icon && <Icon className="h-3.5 w-3.5 text-muted-foreground" />}
                    {r.label}
                  </span>
                  <span className="text-xs text-muted-foreground">{r.value} · {pct}%</span>
                </div>
                <div className="h-1.5 rounded-full bg-muted">
                  <div className="h-full rounded-full bg-primary" style={{ width: `${pct}%` }} />
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
