import { useState } from "react";
import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Save } from "lucide-react";
import { toast } from "sonner";
import { SectionHeader } from "@/components/common/section-header";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { publicAccessService } from "@/services/public-access.service";
import {
  RESOURCE_TYPES,
  VISIBILITIES,
  type PublicResourceCreateInput,
  type ResourceType,
  type Visibility,
} from "@/types/public-access";

export const Route = createFileRoute("/_authenticated/public-resources/new")({
  head: () => ({
    meta: [
      { title: "New public resource — Multilingua" },
      { name: "robots", content: "noindex" },
    ],
  }),
  component: NewResourcePage,
});

function NewResourcePage() {
  const navigate = useNavigate();
  const qc = useQueryClient();

  const [form, setForm] = useState<PublicResourceCreateInput>({
    resourceType: "emergency_info",
    slug: "",
    title: "",
    description: "",
    visibility: "public",
  });

  const createMut = useMutation({
    mutationFn: (payload: PublicResourceCreateInput) =>
      publicAccessService.create(payload),
    onSuccess: (r) => {
      qc.invalidateQueries({ queryKey: ["public-resources"] });
      toast.success("Public resource created");
      navigate({ to: "/public-resources/$id", params: { id: r.id } });
    },
    onError: (e: Error) => toast.error(e.message || "Failed to create"),
  });

  function submit(e: React.FormEvent) {
    e.preventDefault();
    const payload: PublicResourceCreateInput = {
      resourceType: form.resourceType,
      slug: form.slug.trim(),
      title: form.title.trim(),
      description: form.description?.trim() || null,
      visibility: form.visibility,
    };
    createMut.mutate(payload);
  }

  return (
    <div className="space-y-6">
      <SectionHeader
        title="New public resource"
        description="Publish a shareable page addressable by slug and QR token."
        actions={
          <Button variant="outline" size="sm" onClick={() => navigate({ to: "/public-resources" })}>
            <ArrowLeft className="mr-1.5 h-4 w-4" /> Back
          </Button>
        }
      />
      <Card className="shadow-card max-w-3xl">
        <CardContent className="p-6">
          <form className="grid gap-4" onSubmit={submit}>
            <div className="grid gap-2">
              <Label htmlFor="title">Title</Label>
              <Input
                id="title"
                required
                value={form.title}
                onChange={(e) => setForm({ ...form, title: e.target.value })}
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="slug">Slug</Label>
              <Input
                id="slug"
                required
                placeholder="e.g. flood-response-2026"
                pattern="^[a-z0-9][a-z0-9\-]{0,118}[a-z0-9]$|^[a-z0-9]$"
                value={form.slug}
                onChange={(e) => setForm({ ...form, slug: e.target.value })}
              />
              <p className="text-xs text-muted-foreground">
                Lowercase letters, digits, and hyphens only.
              </p>
            </div>
            <div className="grid gap-2 md:grid-cols-2 md:gap-4">
              <div className="grid gap-2">
                <Label>Resource type</Label>
                <Select
                  value={form.resourceType}
                  onValueChange={(v) => setForm({ ...form, resourceType: v as ResourceType })}
                >
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {RESOURCE_TYPES.map((t) => (
                      <SelectItem key={t} value={t} className="capitalize">
                        {t.replace(/_/g, " ")}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="grid gap-2">
                <Label>Visibility</Label>
                <Select
                  value={form.visibility ?? "public"}
                  onValueChange={(v) => setForm({ ...form, visibility: v as Visibility })}
                >
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {VISIBILITIES.filter((v) => v !== "expired").map((v) => (
                      <SelectItem key={v} value={v} className="capitalize">{v}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="grid gap-2">
              <Label htmlFor="description">Description</Label>
              <Textarea
                id="description"
                rows={5}
                value={form.description ?? ""}
                onChange={(e) => setForm({ ...form, description: e.target.value })}
              />
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <Button type="button" variant="outline" onClick={() => navigate({ to: "/public-resources" })}>
                Cancel
              </Button>
              <Button type="submit" disabled={createMut.isPending} className="gap-1.5">
                <Save className="h-4 w-4" />
                {createMut.isPending ? "Creating…" : "Create resource"}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
