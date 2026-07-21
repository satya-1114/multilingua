import { Fragment } from "react";
import { Check, X } from "lucide-react";
import { PERMISSIONS, ROLES, ROLE_METADATA, ROLE_PERMISSIONS, type Permission, type Role } from "@/constants/rbac";
import { cn } from "@/lib/utils";

const CATEGORIES: { label: string; keys: Permission[] }[] = [
  { label: "Campaigns", keys: [PERMISSIONS.CAMPAIGN_VIEW, PERMISSIONS.CAMPAIGN_CREATE, PERMISSIONS.CAMPAIGN_EDIT, PERMISSIONS.CAMPAIGN_LAUNCH] },
  { label: "Content", keys: [PERMISSIONS.CONTENT_VIEW, PERMISSIONS.CONTENT_CREATE, PERMISSIONS.CONTENT_APPROVE] },
  { label: "Audience", keys: [PERMISSIONS.AUDIENCE_VIEW, PERMISSIONS.AUDIENCE_MANAGE, PERMISSIONS.AUDIENCE_IMPORT] },
  { label: "Analytics", keys: [PERMISSIONS.ANALYTICS_VIEW, PERMISSIONS.ANALYTICS_EXPORT] },
  { label: "Administration", keys: [PERMISSIONS.USER_MANAGE, PERMISSIONS.SETTINGS_MANAGE, PERMISSIONS.AUDIT_VIEW] },
  { label: "Platform", keys: [PERMISSIONS.WORKSPACE_MANAGE, PERMISSIONS.SYSTEM_VIEW, PERMISSIONS.FEATURE_FLAG_MANAGE] },
  { label: "Automation & integrations", keys: [PERMISSIONS.AUTOMATION_MANAGE, PERMISSIONS.INTEGRATION_MANAGE, PERMISSIONS.WEBHOOK_MANAGE] },
  { label: "Monitoring & security", keys: [PERMISSIONS.MONITORING_VIEW, PERMISSIONS.SECURITY_VIEW, PERMISSIONS.SECURITY_MANAGE] },
];

const ORDER: Role[] = [
  ROLES.SUPER_ADMIN,
  ROLES.CAMPAIGN_MANAGER,
  ROLES.VOLUNTEER,
  ROLES.VIEWER,
];

export function PermissionMatrix() {
  return (
    <div className="overflow-x-auto rounded-xl border">
      <table className="w-full text-sm">
        <thead className="bg-muted/40 text-xs uppercase text-muted-foreground">
          <tr>
            <th className="sticky left-0 z-10 bg-muted/40 px-3 py-2 text-left font-medium">Permission</th>
            {ORDER.map((r) => (
              <th key={r} className="px-3 py-2 text-center font-medium">{ROLE_METADATA[r].label}</th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-border">
          {CATEGORIES.map((cat) => (
            <Fragment key={cat.label}>
              <tr key={cat.label} className="bg-muted/20">
                <td colSpan={ORDER.length + 1} className="px-3 py-1.5 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
                  {cat.label}
                </td>
              </tr>
              {cat.keys.map((p) => (
                <tr key={p}>
                  <td className="sticky left-0 z-10 bg-background px-3 py-2 font-mono text-xs">{p}</td>
                  {ORDER.map((r) => {
                    const has = ROLE_PERMISSIONS[r].includes(p);
                    return (
                      <td key={r} className="px-3 py-2 text-center">
                        {has ? (
                          <Check className="mx-auto h-4 w-4 text-success" />
                        ) : (
                          <X className={cn("mx-auto h-4 w-4 text-muted-foreground/50")} />
                        )}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </Fragment>
          ))}
        </tbody>
      </table>
    </div>
  );
}
