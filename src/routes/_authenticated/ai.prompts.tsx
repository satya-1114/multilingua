import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Search, Star } from "lucide-react";
import { toast } from "sonner";
import { SectionHeader } from "@/components/common/section-header";
import { PromptCard } from "@/components/common/prompt-card";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { PROMPT_CATEGORIES } from "@/constants/ai";
import { promptService } from "@/services/prompt.service";
import type { PromptCategory, PromptTemplate } from "@/types/ai";

export const Route = createFileRoute("/_authenticated/ai/prompts")({
  component: PromptLibraryPage,
});

function PromptLibraryPage() {
  const qc = useQueryClient();
  const navigate = useNavigate();
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState<PromptCategory | "all">("all");
  const [favoritesOnly, setFavoritesOnly] = useState(false);

  const prompts = useQuery({
    queryKey: ["prompts", { search, category, favoritesOnly }],
    queryFn: () =>
      promptService.list({
        search,
        category,
        favoritesOnly,
        pageSize: 100,
      }),
  });

  const invalidate = () => qc.invalidateQueries({ queryKey: ["prompts"] });

  const toggleFavorite = useMutation({
    mutationFn: (p: PromptTemplate) => promptService.toggleFavorite(p.id),
    onSuccess: invalidate,
  });
  const duplicate = useMutation({
    mutationFn: (p: PromptTemplate) => promptService.duplicate(p.id),
    onSuccess: () => {
      invalidate();
      toast.success("Prompt duplicated");
    },
  });
  const remove = useMutation({
    mutationFn: (p: PromptTemplate) => promptService.remove(p.id),
    onSuccess: () => {
      invalidate();
      toast.success("Prompt deleted");
    },
  });

  return (
    <div className="space-y-5">
        <SectionHeader
          title="Prompt library"
          description="Reusable prompt templates with variables for common public communication scenarios."
        />

        <Card>
          <CardContent className="flex flex-wrap items-center gap-3 p-4">
            <div className="relative min-w-[240px] flex-1">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search prompts…"
                className="pl-9"
              />
            </div>
            <Select
              value={category}
              onValueChange={(v) => setCategory(v as PromptCategory | "all")}
            >
              <SelectTrigger className="w-[200px]">
                <SelectValue placeholder="Category" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All categories</SelectItem>
                {PROMPT_CATEGORIES.map((c) => (
                  <SelectItem key={c.key} value={c.key}>
                    {c.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Button
              variant={favoritesOnly ? "default" : "outline"}
              onClick={() => setFavoritesOnly((v) => !v)}
            >
              <Star className="mr-1.5 h-4 w-4" />
              Favorites
            </Button>
          </CardContent>
        </Card>

        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {(prompts.data?.data ?? []).map((p) => (
            <PromptCard
              key={p.id}
              prompt={p}
              onToggleFavorite={toggleFavorite.mutate}
              onDuplicate={duplicate.mutate}
              onDelete={remove.mutate}
              onUse={() => {
                promptService.markUsed(p.id).catch(() => {});
                sessionStorage.setItem("ai:prompt", p.body);
                navigate({ to: "/ai/workspace" });
                toast.success("Prompt loaded into AI Workspace");
              }}
            />
          ))}
        </div>
      </div>
  );
}
