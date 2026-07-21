import { useMemo, useState } from "react";
import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Plus } from "lucide-react";
import { SectionHeader } from "@/components/common/section-header";
import { DataTableToolbar } from "@/components/common/data-table-toolbar";
import { FilterDrawer } from "@/components/common/filter-drawer";
import { EmptyState } from "@/components/common/empty-state";
import { ErrorState } from "@/components/common/error-state";
import { SkeletonBlock } from "@/components/common/skeleton-block";
import { TemplateCard } from "@/components/common/template-card";
import { PermissionGuard } from "@/components/common/permission-guard";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { templateService } from "@/services/template.service";
import { useDebouncedValue } from "@/hooks/use-debounced-value";
import { TEMPLATE_CATEGORIES } from "@/constants/template";
import { LANGUAGES } from "@/constants/india";
import { PERMISSIONS } from "@/constants/rbac";
import type { TemplateCategory, TemplateStatus } from "@/types/template";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/_authenticated/templates/")({
  head: () => ({
    meta: [
      { title: "Templates — Multilingua" },
      { name: "description", content: "Reusable multilingual communication templates." },
      { name: "robots", content: "noindex" },
    ],
  }),
  component: TemplatesIndexPage,
});

interface Filters {
  category: TemplateCategory[];
  language: string[];
  status: TemplateStatus[];
}

const EMPTY: Filters = { category: [], language: [], status: [] };

function TemplatesIndexPage() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [search, setSearch] = useState("");
  const [filters, setFilters] = useState<Filters>(EMPTY);
  const [pending, setPending] = useState<Filters>(EMPTY);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const debounced = useDebouncedValue(search, 250);

  const query = useMemo(() => ({
    search: debounced || undefined,
    category: filters.category.length ? filters.category : undefined,
    language: filters.language.length ? filters.language : undefined,
    status: filters.status.length ? filters.status : undefined,
    pageSize: 60,
  }), [debounced, filters]);

  const listQ = useQuery({ queryKey: ["templates", query], queryFn: () => templateService.list(query), placeholderData: (p) => p });

  const items = listQ.data?.items ?? [];
  const filterCount = filters.category.length + filters.language.length + filters.status.length;

  return (
    <div className="space-y-6">
      <SectionHeader
        title="Templates"
        description="Reusable, versioned, multilingual communication templates."
        actions={
          <PermissionGuard anyOf={[PERMISSIONS.TEMPLATE_CREATE]}>
            <Button size="sm" className="gap-2" onClick={() => navigate({ to: "/templates/new" })}>
              <Plus className="h-4 w-4" /> New template
            </Button>
          </PermissionGuard>
        }
      />

      <div>
        <DataTableToolbar
          search={search}
          onSearchChange={setSearch}
          placeholder="Search templates by name, subject, or content…"
          onOpenFilters={() => { setPending(filters); setDrawerOpen(true); }}
          filterCount={filterCount}
          onClearFilters={() => setFilters(EMPTY)}
        />
      </div>

      {listQ.isError ? (
        <ErrorState onRetry={() => listQ.refetch()} />
      ) : listQ.isLoading ? (
        <SkeletonBlock rows={6} />
      ) : items.length === 0 ? (
        <EmptyState title="No templates found" description="Try clearing filters or creating a new template." />
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {items.map((t, i) => <TemplateCard key={t.id} template={t} index={i} />)}
        </div>
      )}

      <FilterDrawer
        open={drawerOpen}
        onOpenChange={setDrawerOpen}
        onApply={() => { setFilters(pending); qc.invalidateQueries({ queryKey: ["templates"] }); }}
        onReset={() => setPending(EMPTY)}
      >
        <FilterGroup
          label="Category"
          options={TEMPLATE_CATEGORIES.map((c) => ({ value: c.key, label: c.label }))}
          selected={pending.category}
          onChange={(v) => setPending((f) => ({ ...f, category: v as TemplateCategory[] }))}
        />
        <FilterGroup
          label="Language"
          options={LANGUAGES.map((l) => ({ value: l.code, label: l.label }))}
          selected={pending.language}
          onChange={(v) => setPending((f) => ({ ...f, language: v }))}
        />
        <FilterGroup
          label="Status"
          options={[
            { value: "published", label: "Published" },
            { value: "draft", label: "Draft" },
            { value: "archived", label: "Archived" },
          ]}
          selected={pending.status}
          onChange={(v) => setPending((f) => ({ ...f, status: v as TemplateStatus[] }))}
        />
      </FilterDrawer>
    </div>
  );
}

function FilterGroup({
  label, options, selected, onChange,
}: { label: string; options: { value: string; label: string }[]; selected: string[]; onChange: (v: string[]) => void }) {
  const toggle = (v: string) => onChange(selected.includes(v) ? selected.filter((x) => x !== v) : [...selected, v]);
  return (
    <div>
      <Label className="text-xs uppercase tracking-wide text-muted-foreground">{label}</Label>
      <div className="mt-2 flex flex-wrap gap-1.5 max-h-40 overflow-y-auto">
        {options.map((opt) => {
          const active = selected.includes(opt.value);
          return (
            <button
              key={opt.value}
              type="button"
              onClick={() => toggle(opt.value)}
              className={cn(
                "rounded-full border px-2.5 py-1 text-xs transition-colors",
                active ? "border-primary bg-primary text-primary-foreground" : "border-border text-muted-foreground hover:text-foreground",
              )}
            >
              {opt.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}
