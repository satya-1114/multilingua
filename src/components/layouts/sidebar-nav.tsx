import { Link, useRouterState } from "@tanstack/react-router";
import { useState, useMemo } from "react";
import { motion } from "framer-motion";
import type { LucideIcon } from "lucide-react";
import {
  LayoutDashboard,
  Megaphone,
  Users,
  Languages,
  BarChart3,
  Sparkles,
  Settings,
  UserCircle,
  ChevronDown,
  ShieldCheck,
  Bell,
  Building2,
  LifeBuoy,
  Tag,
  UsersRound,
  ScrollText,
  CalendarDays,
  FileText,
  Image as ImageIcon,
  Activity,
  Wand2,
  BookOpen,
  History as HistoryIcon,
  BarChart2,
  Workflow as WorkflowIcon,
  Plug,
  Gauge,
  Lock,
  Sliders,
  Building,
  Star,
  ClipboardList,
  HeartHandshake,
  Siren,
  Globe,



} from "lucide-react";
import { BrandMark } from "@/components/common/brand-mark";
import { PERMISSIONS, ROLES, type Permission, type Role } from "@/constants/rbac";
import { usePermissions } from "@/hooks/use-permissions";
import { isRouteAllowed } from "@/lib/route-access";
import { cn } from "@/lib/utils";

interface NavItem {
  title: string;
  to: string;
  icon: LucideIcon;
  badge?: string;
  anyOf?: Permission[];
  roles?: Role[];
}

interface NavSection {
  label: string;
  items: NavItem[];
}

const navSections: NavSection[] = [
  {
    label: "Overview",
    items: [
      { title: "Dashboard", to: "/dashboard", icon: LayoutDashboard },
      { title: "My Tasks", to: "/my-tasks", icon: ClipboardList, anyOf: [PERMISSIONS.TASK_ACT] },
      { title: "Favorites", to: "/favorites", icon: Star },
    ],
  },
  {
    label: "Campaigns",
    items: [
      { title: "All campaigns", to: "/campaigns", icon: Megaphone, anyOf: [PERMISSIONS.CAMPAIGN_VIEW] },
      { title: "Calendar", to: "/campaigns/calendar", icon: CalendarDays, anyOf: [PERMISSIONS.CAMPAIGN_VIEW] },
      { title: "Approvals", to: "/campaigns/approvals", icon: ShieldCheck, anyOf: [PERMISSIONS.APPROVAL_ACT, PERMISSIONS.CAMPAIGN_VIEW] },
    ],
  },
  {
    label: "Communication",
    items: [
      { title: "Overview", to: "/communication", icon: Activity, anyOf: [PERMISSIONS.COMMUNICATION_VIEW] },
      { title: "Channels", to: "/communication/channels", icon: Plug, anyOf: [PERMISSIONS.CHANNEL_VIEW] },
      { title: "Delivery queues", to: "/communication/delivery", icon: Gauge, anyOf: [PERMISSIONS.DELIVERY_VIEW] },
      { title: "Scheduling", to: "/communication/scheduling", icon: CalendarDays, anyOf: [PERMISSIONS.SCHEDULER_MANAGE, PERMISSIONS.COMMUNICATION_VIEW] },
      { title: "Retry policies", to: "/communication/retry-policies", icon: WorkflowIcon, anyOf: [PERMISSIONS.RETRY_POLICY_MANAGE] },
      { title: "Engagement", to: "/communication/engagement", icon: BarChart2, anyOf: [PERMISSIONS.ENGAGEMENT_VIEW, PERMISSIONS.ANALYTICS_VIEW] },
    ],
  },
  {
    label: "Content",
    items: [
      { title: "Templates", to: "/templates", icon: FileText, anyOf: [PERMISSIONS.TEMPLATE_VIEW] },
      { title: "Media library", to: "/media", icon: ImageIcon, anyOf: [PERMISSIONS.MEDIA_VIEW] },
    ],
  },
  {
    label: "AI Studio",
    items: [
      { title: "Overview", to: "/ai", icon: Sparkles, anyOf: [PERMISSIONS.AI_USE] },
      { title: "Workspace", to: "/ai/workspace", icon: Wand2, anyOf: [PERMISSIONS.AI_GENERATE] },
      { title: "Prompt library", to: "/ai/prompts", icon: BookOpen, anyOf: [PERMISSIONS.AI_USE] },
      { title: "History", to: "/ai/history", icon: HistoryIcon, anyOf: [PERMISSIONS.AI_HISTORY_VIEW] },
      { title: "Drafts", to: "/ai/drafts", icon: FileText, anyOf: [PERMISSIONS.AI_USE] },
      { title: "Translation", to: "/translation", icon: Languages, anyOf: [PERMISSIONS.TRANSLATION_USE] },
    ],
  },
  {
    label: "Audience",
    items: [
      { title: "Contacts", to: "/audience", icon: Users, anyOf: [PERMISSIONS.AUDIENCE_VIEW] },
      { title: "Groups", to: "/audience-groups", icon: UsersRound, anyOf: [PERMISSIONS.AUDIENCE_VIEW] },
      { title: "Tags", to: "/tags", icon: Tag, anyOf: [PERMISSIONS.AUDIENCE_VIEW] },
      { title: "Volunteers", to: "/volunteers", icon: HeartHandshake, anyOf: [PERMISSIONS.VOLUNTEER_VIEW] },
    ],
  },
  {
    label: "Response",
    items: [
      { title: "Disasters", to: "/disasters", icon: Siren, anyOf: [PERMISSIONS.DISASTER_VIEW] },
      { title: "Public information", to: "/public-resources", icon: Globe, anyOf: [PERMISSIONS.PUBLIC_VIEW] },
      { title: "Translations", to: "/translations", icon: Languages, anyOf: [PERMISSIONS.TRANSLATION_USE] },
    ],
  },


  {
    label: "Analytics",
    items: [
      { title: "Overview", to: "/analytics", icon: BarChart2, anyOf: [PERMISSIONS.ANALYTICS_VIEW] },
      { title: "Platform", to: "/analytics/platform", icon: BarChart2, anyOf: [PERMISSIONS.ANALYTICS_VIEW] },
      { title: "Reports", to: "/analytics/reports", icon: FileText, anyOf: [PERMISSIONS.ANALYTICS_VIEW] },
      { title: "Report builder", to: "/analytics/builder", icon: Wand2, anyOf: [PERMISSIONS.ANALYTICS_EXPORT] },
    ],
  },
  {
    label: "Automation & integrations",
    items: [
      { title: "Workflows", to: "/automation", icon: WorkflowIcon, anyOf: [PERMISSIONS.AUTOMATION_VIEW, PERMISSIONS.WORKFLOW_MANAGE] },
      { title: "Integrations", to: "/integrations", icon: Plug, anyOf: [PERMISSIONS.INTEGRATION_VIEW, PERMISSIONS.INTEGRATION_MANAGE] },
      { title: "Webhooks", to: "/integrations/webhooks", icon: Plug, anyOf: [PERMISSIONS.WEBHOOK_MANAGE] },
    ],
  },
  {
    label: "Operations",
    items: [
      { title: "Monitoring", to: "/monitoring", icon: Gauge, anyOf: [PERMISSIONS.MONITORING_VIEW] },
      { title: "Background jobs", to: "/jobs", icon: Activity, anyOf: [PERMISSIONS.JOB_VIEW] },
      { title: "Security", to: "/security", icon: Lock, anyOf: [PERMISSIONS.SECURITY_VIEW] },
    ],
  },
  {
    label: "Administration",
    items: [
      { title: "Workspaces", to: "/workspaces", icon: Building, anyOf: [PERMISSIONS.WORKSPACE_VIEW, PERMISSIONS.WORKSPACE_MANAGE] },
      { title: "Organizations", to: "/organizations", icon: Building2, anyOf: [PERMISSIONS.ORG_VIEW] },
      { title: "Users", to: "/admin/users", icon: UsersRound, roles: [ROLES.SUPER_ADMIN] },
      { title: "System", to: "/admin", icon: Sliders, anyOf: [PERMISSIONS.SYSTEM_VIEW, PERMISSIONS.SYSTEM_MANAGE] },
      { title: "Audit logs", to: "/audit-logs", icon: ScrollText, anyOf: [PERMISSIONS.AUDIT_VIEW] },
    ],
  },
  {
    label: "Account",
    items: [
      { title: "Notifications", to: "/notifications", icon: Bell },
      { title: "Profile", to: "/profile", icon: UserCircle },
      { title: "Settings", to: "/settings", icon: Settings },
      { title: "Help center", to: "/help", icon: LifeBuoy },
    ],
  },
];


interface SidebarNavProps {
  onNavigate?: () => void;
}

export function SidebarNav({ onNavigate }: SidebarNavProps) {
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  const { hasAnyPermission, hasAnyRole, role } = usePermissions();
  const [collapsedSections, setCollapsedSections] = useState<Record<string, boolean>>({});

  const visibleSections = useMemo(() => {
    return navSections
      .map((section) => ({
        ...section,
        items: section.items.filter((item) => {
          const roleOk = !item.roles || item.roles.length === 0 || hasAnyRole(item.roles);
          const permOk = !item.anyOf || item.anyOf.length === 0 || hasAnyPermission(item.anyOf);
          const routeOk = isRouteAllowed(item.to, role);
          return roleOk && permOk && routeOk;
        }),
      }))
      .filter((s) => s.items.length > 0);
  }, [hasAnyPermission, hasAnyRole, role]);

  return (
    <aside className="flex h-full w-full flex-col bg-sidebar text-sidebar-foreground">
      <div className="flex h-16 items-center border-b border-sidebar-border px-5">
        <Link to="/" onClick={onNavigate} className="flex items-center">
          <BrandMark />
        </Link>
      </div>

      <nav className="flex-1 overflow-y-auto px-3 py-5" aria-label="Primary">
        <ul className="flex flex-col gap-5">
          {visibleSections.map((section) => {
            const collapsed = collapsedSections[section.label];
            return (
              <li key={section.label}>
                <button
                  type="button"
                  onClick={() =>
                    setCollapsedSections((prev) => ({
                      ...prev,
                      [section.label]: !prev[section.label],
                    }))
                  }
                  className="flex w-full items-center justify-between px-3 pb-2 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground hover:text-foreground"
                  aria-expanded={!collapsed}
                >
                  {section.label}
                  <ChevronDown
                    className={cn("h-3 w-3 transition-transform", collapsed && "-rotate-90")}
                  />
                </button>
                {!collapsed && (
                  <motion.ul
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: "auto" }}
                    transition={{ duration: 0.18 }}
                    className="flex flex-col gap-0.5 overflow-hidden"
                  >
                    {section.items.map((item) => {
                      const active = pathname === item.to;
                      const Icon = item.icon;
                      return (
                        <li key={item.title}>
                          <Link
                            to={item.to}
                            onClick={onNavigate}
                            className={cn(
                              "group flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                              active
                                ? "bg-primary text-primary-foreground shadow-card"
                                : "text-sidebar-foreground/80 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground",
                            )}
                          >
                            <Icon
                              className={cn(
                                "h-4 w-4 shrink-0",
                                active
                                  ? "text-primary-foreground"
                                  : "text-muted-foreground",
                              )}
                            />
                            <span className="flex-1 truncate">{item.title}</span>
                            {item.badge && (
                              <span
                                className={cn(
                                  "rounded-full px-1.5 py-0.5 text-[10px] font-semibold",
                                  active
                                    ? "bg-primary-foreground/15 text-primary-foreground"
                                    : "bg-accent/15 text-accent",
                                )}
                              >
                                {item.badge}
                              </span>
                            )}
                          </Link>
                        </li>
                      );
                    })}
                  </motion.ul>
                )}
              </li>
            );
          })}
        </ul>
      </nav>

      <div className="border-t border-sidebar-border p-4">
        <a
          href="#"
          className="flex items-center gap-3 rounded-xl bg-sidebar-accent p-3 transition-colors hover:bg-sidebar-accent/70"
        >
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10 text-primary">
            <LifeBuoy className="h-4 w-4" />
          </div>
          <div className="min-w-0">
            <p className="text-xs font-semibold text-sidebar-accent-foreground">Support</p>
            <p className="text-xs text-muted-foreground">Docs, guides, and help.</p>
          </div>
        </a>
      </div>
    </aside>
  );
}
