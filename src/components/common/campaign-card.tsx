import { Link } from "@tanstack/react-router";
import { Calendar, Languages, Users } from "lucide-react";
import { motion } from "framer-motion";
import type { Campaign } from "@/types/campaign";
import { CampaignStatusBadge } from "@/components/common/campaign-status-badge";
import { CAMPAIGN_STATUS_META } from "@/constants/campaign";
import { cn } from "@/lib/utils";

interface Props {
  campaign: Campaign;
  index?: number;
}

export function CampaignCard({ campaign, index = 0 }: Props) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: Math.min(index, 8) * 0.03 }}
      className="group relative overflow-hidden rounded-xl border bg-card p-4 shadow-card transition-shadow hover:shadow-md"
    >
      <span
        className="absolute inset-x-0 top-0 h-1"
        style={{ background: campaign.color }}
        aria-hidden
      />
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="truncate text-xs font-medium uppercase tracking-wide text-muted-foreground">
            {campaign.code}
          </p>
          <Link
            to="/campaigns/$id"
            params={{ id: campaign.id }}
            className="mt-0.5 block truncate text-base font-semibold text-foreground hover:text-primary"
          >
            {campaign.name}
          </Link>
          <p className="mt-1 line-clamp-2 text-sm text-muted-foreground">{campaign.description}</p>
        </div>
        <CampaignStatusBadge status={campaign.status} />
      </div>

      <div className="mt-4 grid grid-cols-3 gap-2 text-xs">
        <Metric icon={Users} label="Reach" value={campaign.estimatedReach.toLocaleString()} />
        <Metric icon={Languages} label="Languages" value={String(campaign.languages.length)} />
        <Metric
          icon={Calendar}
          label="Start"
          value={
            campaign.schedule.startAt
              ? new Date(campaign.schedule.startAt).toLocaleDateString()
              : "—"
          }
        />
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-1.5 text-[11px] text-muted-foreground">
        <span className={cn("rounded-full bg-muted px-2 py-0.5 font-medium capitalize")}>
          {campaign.type.replace(/_/g, " ")}
        </span>
        <span className="rounded-full bg-muted px-2 py-0.5 font-medium capitalize">
          {campaign.priority} priority
        </span>
        <span className="ml-auto italic">
          {CAMPAIGN_STATUS_META[campaign.status].description}
        </span>
      </div>
    </motion.div>
  );
}

function Metric({
  icon: Icon,
  label,
  value,
}: {
  icon: typeof Users;
  label: string;
  value: string;
}) {
  return (
    <div className="rounded-lg border bg-background/60 p-2">
      <div className="flex items-center gap-1.5 text-muted-foreground">
        <Icon className="h-3 w-3" />
        <span className="text-[10px] uppercase tracking-wide">{label}</span>
      </div>
      <p className="mt-1 text-sm font-semibold text-foreground">{value}</p>
    </div>
  );
}
