import { Link, useNavigate, useRouterState } from "@tanstack/react-router";
import { formatDistanceToNow } from "date-fns";
import {
  Bell,
  ChevronRight,
  Menu,
  Search,
  LogOut,
  User,
  Settings as SettingsIcon,
  Monitor,
  Moon,
  Sun,
  Check,
} from "lucide-react";
import { Button } from "@/components/ui/button";

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useAuth } from "@/contexts/auth-context";
import { useTheme } from "@/contexts/theme-context";
import { useNotifications } from "@/contexts/notification-context";
import { useCommandPalette } from "@/components/common/command-palette";
import { RoleBadge } from "@/components/common/role-badge";
import { WorkspaceSwitcher } from "@/components/common/workspace-switcher";
import { cn } from "@/lib/utils";

interface TopBarProps {
  onMenuClick: () => void;
}

function toBreadcrumbs(pathname: string) {
  if (pathname === "/") return [{ label: "Home", to: "/" }];
  const parts = pathname.split("/").filter(Boolean);
  const crumbs = [{ label: "Home", to: "/" }];
  let acc = "";
  for (const part of parts) {
    acc += `/${part}`;
    crumbs.push({
      label: part.charAt(0).toUpperCase() + part.slice(1).replace(/-/g, " "),
      to: acc,
    });
  }
  return crumbs;
}

function initialsOf(name: string) {
  return name
    .split(" ")
    .map((n) => n[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();
}

export function TopBar({ onMenuClick }: TopBarProps) {
  const navigate = useNavigate();
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  const { user, logout } = useAuth();
  const { theme, setTheme } = useTheme();
  const { notifications, unreadCount, markRead, markAllRead } = useNotifications();
  const { open: openPalette } = useCommandPalette();
  const crumbs = toBreadcrumbs(pathname);

  const recentNotifications = notifications.filter((n) => !n.archived).slice(0, 5);
  const initials = user ? initialsOf(user.fullName) : "AD";

  async function handleSignOut() {
    await logout();
    navigate({ to: "/login" });
  }

  return (
    <header className="sticky top-0 z-30 flex h-16 items-center gap-3 border-b border-border bg-card/80 px-4 backdrop-blur md:px-6">
      <Button
        variant="ghost"
        size="icon"
        className="lg:hidden"
        onClick={onMenuClick}
        aria-label="Open navigation"
      >
        <Menu className="h-5 w-5" />
      </Button>

      <WorkspaceSwitcher />



      <nav aria-label="Breadcrumb" className="hidden min-w-0 flex-1 md:block">
        <ol className="flex items-center gap-1.5 text-sm text-muted-foreground">
          {crumbs.map((c, i) => {
            const last = i === crumbs.length - 1;
            return (
              <li key={c.to} className="flex items-center gap-1.5">
                {i > 0 && (
                  <ChevronRight className="h-3.5 w-3.5 text-muted-foreground/60" />
                )}
                {last ? (
                  <span className="font-medium text-foreground">{c.label}</span>
                ) : (
                  <Link to={c.to} className="hover:text-foreground">
                    {c.label}
                  </Link>
                )}
              </li>
            );
          })}
        </ol>
      </nav>

      <div className="flex flex-1 items-center justify-end gap-2 md:flex-none">
        <button
          type="button"
          onClick={openPalette}
          className="relative hidden h-9 w-72 items-center gap-2 rounded-md border border-input bg-background pl-3 pr-2 text-left text-sm text-muted-foreground shadow-sm transition hover:border-primary/40 md:flex"
          aria-label="Open command palette"
        >
          <Search className="h-4 w-4" />
          <span className="flex-1 truncate">Search campaigns, contacts, templates…</span>
          <kbd className="ml-auto rounded border bg-muted px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
            ⌘K
          </kbd>
        </button>
        <Button
          variant="ghost"
          size="icon"
          className="md:hidden"
          aria-label="Search"
          onClick={openPalette}
        >
          <Search className="h-4 w-4" />
        </Button>

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon" aria-label="Change theme">
              {theme === "dark" ? (
                <Moon className="h-4 w-4" />
              ) : theme === "light" ? (
                <Sun className="h-4 w-4" />
              ) : (
                <Monitor className="h-4 w-4" />
              )}
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-40">
            <DropdownMenuItem onSelect={() => setTheme("light")}>
              <Sun className="mr-2 h-4 w-4" /> Light
              {theme === "light" && <Check className="ml-auto h-3.5 w-3.5" />}
            </DropdownMenuItem>
            <DropdownMenuItem onSelect={() => setTheme("dark")}>
              <Moon className="mr-2 h-4 w-4" /> Dark
              {theme === "dark" && <Check className="ml-auto h-3.5 w-3.5" />}
            </DropdownMenuItem>
            <DropdownMenuItem onSelect={() => setTheme("system")}>
              <Monitor className="mr-2 h-4 w-4" /> System
              {theme === "system" && <Check className="ml-auto h-3.5 w-3.5" />}
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>

        {/* Notifications */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon" aria-label="Notifications" className="relative">
              <Bell className="h-4 w-4" />
              {unreadCount > 0 && (
                <span
                  className="absolute right-1.5 top-1.5 inline-flex h-4 min-w-[16px] items-center justify-center rounded-full bg-accent px-1 text-[10px] font-semibold text-accent-foreground"
                  aria-label={`${unreadCount} unread notifications`}
                >
                  {unreadCount > 9 ? "9+" : unreadCount}
                </span>
              )}
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-80 p-0">
            <div className="flex items-center justify-between px-3 py-2.5">
              <p className="text-sm font-semibold">Notifications</p>
              <button
                type="button"
                onClick={markAllRead}
                className="text-xs font-medium text-primary hover:underline disabled:text-muted-foreground disabled:no-underline"
                disabled={unreadCount === 0}
              >
                Mark all read
              </button>
            </div>
            <DropdownMenuSeparator className="my-0" />
            <ScrollArea className="max-h-80">
              {recentNotifications.length === 0 ? (
                <p className="px-3 py-6 text-center text-xs text-muted-foreground">
                  You're all caught up.
                </p>
              ) : (
                <ul className="divide-y divide-border">
                  {recentNotifications.map((n) => (
                    <li key={n.id}>
                      <button
                        type="button"
                        onClick={() => markRead(n.id)}
                        className={cn(
                          "flex w-full items-start gap-2 px-3 py-2.5 text-left text-sm transition-colors hover:bg-muted/60",
                          !n.read && "bg-primary/5",
                        )}
                      >
                        <span
                          className={cn(
                            "mt-1.5 h-2 w-2 shrink-0 rounded-full",
                            n.read ? "bg-transparent" : "bg-primary",
                          )}
                        />
                        <span className="min-w-0 flex-1">
                          <span className="block truncate font-medium text-foreground">
                            {n.title}
                          </span>
                          <span className="mt-0.5 block truncate text-xs text-muted-foreground">
                            {n.message}
                          </span>
                          <span className="mt-1 block text-[10px] text-muted-foreground">
                            {formatDistanceToNow(new Date(n.timestamp), { addSuffix: true })}
                          </span>
                        </span>
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </ScrollArea>
            <DropdownMenuSeparator className="my-0" />
            <DropdownMenuItem asChild className="justify-center text-xs font-medium">
              <Link to="/notifications">View all notifications</Link>
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>

        {/* Profile */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" className="h-9 gap-2 px-2">
              <Avatar className="h-7 w-7">
                {user?.avatarUrl && <AvatarImage src={user.avatarUrl} alt={user.fullName} />}
                <AvatarFallback className="bg-primary text-xs text-primary-foreground">
                  {initials}
                </AvatarFallback>
              </Avatar>
              <span className="hidden text-sm font-medium sm:inline">
                {user?.fullName ?? "Signed in"}
              </span>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-64">
            <DropdownMenuLabel>
              <div className="flex flex-col gap-1">
                <span className="text-sm font-medium">{user?.fullName ?? ""}</span>
                <span className="text-xs text-muted-foreground">{user?.email ?? ""}</span>
                {user && (
                  <div className="mt-1">
                    <RoleBadge role={user.role} />
                  </div>
                )}
              </div>
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem asChild>
              <Link to="/profile">
                <User className="mr-2 h-4 w-4" /> Profile
              </Link>
            </DropdownMenuItem>
            <DropdownMenuItem asChild>
              <Link to="/settings">
                <SettingsIcon className="mr-2 h-4 w-4" /> Settings
              </Link>
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem onSelect={handleSignOut}>
              <LogOut className="mr-2 h-4 w-4" /> Sign out
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
}
