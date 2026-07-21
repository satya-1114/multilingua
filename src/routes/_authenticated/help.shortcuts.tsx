import { createFileRoute } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { SectionHeader } from "@/components/common/section-header";
import { Card, CardContent } from "@/components/ui/card";
import { helpService } from "@/services/help.service";

export const Route = createFileRoute("/_authenticated/help/shortcuts")({
  head: () => ({ meta: [{ title: "Keyboard shortcuts" }, { name: "robots", content: "noindex" }] }),
  component: ShortcutsPage,
});

function ShortcutsPage() {
  const q = useQuery({ queryKey: ["help", "shortcuts"], queryFn: () => helpService.shortcuts() });
  const grouped = (q.data ?? []).reduce<Record<string, typeof q.data>>((acc, s) => {
    (acc[s.category] ||= []).push(s);
    return acc;
  }, {} as Record<string, typeof q.data>);
  return (
    <div className="space-y-5">
        <SectionHeader title="Keyboard shortcuts" description="Move faster with these system-wide shortcuts." />
        <div className="grid gap-4 md:grid-cols-2">
          {Object.entries(grouped).map(([cat, items]) => (
            <Card key={cat}>
              <CardContent className="p-4">
                <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">{cat}</p>
                <ul className="divide-y divide-border">
                  {items?.map((s, i) => (
                    <li key={i} className="flex items-center justify-between py-2 text-sm">
                      <span>{s.description}</span>
                      <span className="flex gap-1">
                        {s.keys.filter(Boolean).map((k) => (
                          <kbd key={k} className="rounded bg-muted px-1.5 py-0.5 font-mono text-[11px]">{k}</kbd>
                        ))}
                      </span>
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
  );
}
