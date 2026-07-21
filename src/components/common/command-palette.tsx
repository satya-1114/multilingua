import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { useNavigate } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
} from "@/components/ui/command";
import {
  LayoutDashboard,
  Megaphone,
  Users,
  Building2,
  ScrollText,
  Bell,
  Settings as SettingsIcon,
  UserCircle,
  UsersRound,
  Tag,
  CalendarDays,
  FileText,
  Image as ImageIcon,
  Plus,
  ShieldCheck,
} from "lucide-react";
import { campaignService } from "@/services/campaign.service";
import { audienceService } from "@/services/audience.service";
import { organizationService } from "@/services/organization.service";
import { templateService } from "@/services/template.service";
import { useDebouncedValue } from "@/hooks/use-debounced-value";

interface CommandPaletteContextValue {
  open: () => void;
}

const Ctx = createContext<CommandPaletteContextValue | null>(null);

export function useCommandPalette() {
  const v = useContext(Ctx);
  if (!v) throw new Error("useCommandPalette must be used inside CommandPaletteProvider");
  return v;
}

export function CommandPaletteProvider({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const navigate = useNavigate();
  const debounced = useDebouncedValue(query, 200);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setOpen((v) => !v);
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  useEffect(() => {
    if (!open) setQuery("");
  }, [open]);

  const trimmed = debounced.trim();
  const searching = trimmed.length >= 2;

  const campaignsQ = useQuery({
    queryKey: ["cmdk", "campaigns", trimmed],
    queryFn: () => campaignService.list({ search: trimmed, pageSize: 6 }),
    enabled: open && searching,
  });
  const audienceQ = useQuery({
    queryKey: ["cmdk", "audience", trimmed],
    queryFn: () => audienceService.list({ search: trimmed, pageSize: 5 }),
    enabled: open && searching,
  });
  const orgQ = useQuery({
    queryKey: ["cmdk", "orgs", trimmed],
    queryFn: () => organizationService.list({ search: trimmed, pageSize: 5 }),
    enabled: open && searching,
  });
  const templatesQ = useQuery({
    queryKey: ["cmdk", "templates", trimmed],
    queryFn: () => templateService.list({ search: trimmed, pageSize: 5 }),
    enabled: open && searching,
  });

  const openPalette = useCallback(() => setOpen(true), []);

  const value = useMemo(() => ({ open: openPalette }), [openPalette]);

  const go = (fn: () => void) => {
    setOpen(false);
    fn();
  };

  return (
    <Ctx.Provider value={value}>
      {children}
      <CommandDialog open={open} onOpenChange={setOpen}>
        <CommandInput
          placeholder="Search campaigns, contacts, organizations, templates…"
          value={query}
          onValueChange={setQuery}
        />
        <CommandList>
          <CommandEmpty>
            {searching ? "No results found." : "Type to search across your workspace."}
          </CommandEmpty>

          <CommandGroup heading="Navigate">
            <CommandItem onSelect={() => go(() => navigate({ to: "/dashboard" }))}>
              <LayoutDashboard className="mr-2 h-4 w-4" /> Dashboard
            </CommandItem>
            <CommandItem onSelect={() => go(() => navigate({ to: "/campaigns" }))}>
              <Megaphone className="mr-2 h-4 w-4" /> Campaigns
            </CommandItem>
            <CommandItem onSelect={() => go(() => navigate({ to: "/campaigns/calendar" }))}>
              <CalendarDays className="mr-2 h-4 w-4" /> Campaign calendar
            </CommandItem>
            <CommandItem onSelect={() => go(() => navigate({ to: "/campaigns/approvals" }))}>
              <ShieldCheck className="mr-2 h-4 w-4" /> Approval queue
            </CommandItem>
            <CommandItem onSelect={() => go(() => navigate({ to: "/templates" }))}>
              <FileText className="mr-2 h-4 w-4" /> Templates
            </CommandItem>
            <CommandItem onSelect={() => go(() => navigate({ to: "/media" }))}>
              <ImageIcon className="mr-2 h-4 w-4" /> Media library
            </CommandItem>
            <CommandItem onSelect={() => go(() => navigate({ to: "/audience" }))}>
              <Users className="mr-2 h-4 w-4" /> Audience
            </CommandItem>
            <CommandItem onSelect={() => go(() => navigate({ to: "/audience-groups" }))}>
              <UsersRound className="mr-2 h-4 w-4" /> Audience groups
            </CommandItem>
            <CommandItem onSelect={() => go(() => navigate({ to: "/tags" }))}>
              <Tag className="mr-2 h-4 w-4" /> Tags
            </CommandItem>
            <CommandItem onSelect={() => go(() => navigate({ to: "/organizations" }))}>
              <Building2 className="mr-2 h-4 w-4" /> Organizations
            </CommandItem>
            <CommandItem onSelect={() => go(() => navigate({ to: "/audit-logs" }))}>
              <ScrollText className="mr-2 h-4 w-4" /> Audit logs
            </CommandItem>
            <CommandItem onSelect={() => go(() => navigate({ to: "/notifications" }))}>
              <Bell className="mr-2 h-4 w-4" /> Notifications
            </CommandItem>
            <CommandItem onSelect={() => go(() => navigate({ to: "/profile" }))}>
              <UserCircle className="mr-2 h-4 w-4" /> Profile
            </CommandItem>
            <CommandItem onSelect={() => go(() => navigate({ to: "/settings" }))}>
              <SettingsIcon className="mr-2 h-4 w-4" /> Settings
            </CommandItem>
          </CommandGroup>

          <CommandSeparator />

          <CommandGroup heading="Create">
            <CommandItem onSelect={() => go(() => navigate({ to: "/campaigns/new" }))}>
              <Plus className="mr-2 h-4 w-4" /> New campaign
            </CommandItem>
            <CommandItem onSelect={() => go(() => navigate({ to: "/templates/new" }))}>
              <Plus className="mr-2 h-4 w-4" /> New template
            </CommandItem>
            <CommandItem onSelect={() => go(() => navigate({ to: "/audience/new" }))}>
              <Plus className="mr-2 h-4 w-4" /> New contact
            </CommandItem>
            <CommandItem onSelect={() => go(() => navigate({ to: "/organizations/new" }))}>
              <Plus className="mr-2 h-4 w-4" /> New organization
            </CommandItem>
          </CommandGroup>

          {searching && (campaignsQ.data?.items.length ?? 0) > 0 && (
            <>
              <CommandSeparator />
              <CommandGroup heading="Campaigns">
                {campaignsQ.data!.items.map((c) => (
                  <CommandItem
                    key={c.id}
                    value={`campaign-${c.id}-${c.name}`}
                    onSelect={() => go(() => navigate({ to: "/campaigns/$id", params: { id: c.id } }))}
                  >
                    <Megaphone className="mr-2 h-4 w-4" />
                    <span className="truncate">{c.name}</span>
                    <span className="ml-auto text-xs text-muted-foreground">{c.code}</span>
                  </CommandItem>
                ))}
              </CommandGroup>
            </>
          )}

          {searching && (templatesQ.data?.items.length ?? 0) > 0 && (
            <>
              <CommandSeparator />
              <CommandGroup heading="Templates">
                {templatesQ.data!.items.map((t) => (
                  <CommandItem
                    key={t.id}
                    value={`template-${t.id}-${t.name}`}
                    onSelect={() => go(() => navigate({ to: "/templates/$id", params: { id: t.id } }))}
                  >
                    <FileText className="mr-2 h-4 w-4" />
                    <span className="truncate">{t.name}</span>
                    <span className="ml-auto text-xs uppercase text-muted-foreground">{t.category}</span>
                  </CommandItem>
                ))}
              </CommandGroup>
            </>
          )}

          {searching && (audienceQ.data?.items.length ?? 0) > 0 && (
            <>
              <CommandSeparator />
              <CommandGroup heading="Audience">
                {audienceQ.data!.items.map((a) => (
                  <CommandItem
                    key={a.id}
                    value={`audience-${a.id}-${a.fullName}`}
                    onSelect={() => go(() => navigate({ to: "/audience/$id", params: { id: a.id } }))}
                  >
                    <Users className="mr-2 h-4 w-4" />
                    <span className="truncate">{a.fullName}</span>
                    <span className="ml-auto text-xs text-muted-foreground">{a.city}</span>
                  </CommandItem>
                ))}
              </CommandGroup>
            </>
          )}

          {searching && (orgQ.data?.items.length ?? 0) > 0 && (
            <>
              <CommandSeparator />
              <CommandGroup heading="Organizations">
                {orgQ.data!.items.map((o) => (
                  <CommandItem
                    key={o.id}
                    value={`org-${o.id}-${o.name}`}
                    onSelect={() => go(() => navigate({ to: "/organizations/$id", params: { id: o.id } }))}
                  >
                    <Building2 className="mr-2 h-4 w-4" />
                    <span className="truncate">{o.name}</span>
                    <span className="ml-auto text-xs text-muted-foreground">{o.type}</span>
                  </CommandItem>
                ))}
              </CommandGroup>
            </>
          )}
        </CommandList>
      </CommandDialog>
    </Ctx.Provider>
  );
}
