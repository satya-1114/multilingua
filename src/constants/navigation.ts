import {
  LayoutDashboard,
  Megaphone,
  Users,
  Languages,
  BarChart3,
  MessageSquare,
  Sparkles,
  Settings,
  UserCircle,
  type LucideIcon,
} from "lucide-react";

export interface NavItem {
  title: string;
  to: string;
  icon: LucideIcon;
  badge?: string;
}

export interface NavSection {
  label: string;
  items: NavItem[];
}

export const navSections: NavSection[] = [
  {
    label: "Overview",
    items: [
      { title: "Dashboard", to: "/dashboard", icon: LayoutDashboard },
      { title: "Analytics", to: "/dashboard", icon: BarChart3 },
    ],
  },
  {
    label: "Communication",
    items: [
      { title: "Campaigns", to: "/dashboard", icon: Megaphone },
      { title: "Messages", to: "/dashboard", icon: MessageSquare },
      { title: "AI Studio", to: "/dashboard", icon: Sparkles, badge: "New" },
    ],
  },
  {
    label: "Audience",
    items: [
      { title: "Contacts", to: "/dashboard", icon: Users },
      { title: "Languages", to: "/dashboard", icon: Languages },
    ],
  },
  {
    label: "Account",
    items: [
      { title: "Profile", to: "/profile", icon: UserCircle },
      { title: "Settings", to: "/settings", icon: Settings },
    ],
  },
];

export const APP_NAME = "Multilingua";
export const APP_TAGLINE = "AI Communication Platform";
