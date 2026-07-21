import { Building2, Users } from "lucide-react";
import { Link } from "@tanstack/react-router";
import type { Organization } from "@/types/organization";
import { Card } from "@/components/ui/card";
import { StatusBadge } from "@/components/common/status-badge";

interface OrganizationCardProps {
  organization: Organization;
}

export function OrganizationCard({ organization }: OrganizationCardProps) {
  return (
    <Link
      to="/organizations/$id"
      params={{ id: organization.id }}
      className="block focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary rounded-xl"
    >
      <Card className="shadow-card hover:shadow-lg transition-shadow p-5">
        <div className="flex items-start gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-primary/10 text-primary">
            {organization.logoUrl ? (
              <img src={organization.logoUrl} alt="" className="h-full w-full rounded-xl object-cover" />
            ) : (
              <Building2 className="h-5 w-5" />
            )}
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex items-center justify-between gap-2">
              <p className="truncate text-sm font-semibold text-foreground">{organization.name}</p>
              <StatusBadge status={organization.status} />
            </div>
            <p className="mt-0.5 text-xs text-muted-foreground">{organization.type}</p>
          </div>
        </div>
        <div className="mt-4 grid grid-cols-3 gap-3 text-xs">
          <div>
            <p className="text-muted-foreground">Users</p>
            <p className="mt-0.5 font-semibold text-foreground">{organization.userCount}</p>
          </div>
          <div>
            <p className="text-muted-foreground">Audience</p>
            <p className="mt-0.5 font-semibold text-foreground">{organization.audienceCount.toLocaleString()}</p>
          </div>
          <div>
            <p className="text-muted-foreground">Campaigns</p>
            <p className="mt-0.5 font-semibold text-foreground">{organization.campaignCount}</p>
          </div>
        </div>
        <div className="mt-3 flex items-center gap-2 text-xs text-muted-foreground">
          <Users className="h-3.5 w-3.5" />
          {organization.city}, {organization.state}
        </div>
      </Card>
    </Link>
  );
}
