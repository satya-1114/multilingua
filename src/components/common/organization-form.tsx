import { useMemo } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useNavigate } from "@tanstack/react-router";
import { toast } from "sonner";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { INDIAN_STATES, LANGUAGES, TIMEZONES } from "@/constants/india";
import { ORGANIZATION_TYPES, type OrganizationType } from "@/constants/rbac";
import { organizationService } from "@/services/organization.service";
import type { Organization, OrganizationInput, OrganizationStatus } from "@/types/organization";
import { cn } from "@/lib/utils";

const schema = z.object({
  name: z.string().trim().min(2, "Name is required").max(120),
  type: z.enum(ORGANIZATION_TYPES),
  website: z.string().trim().url("Enter a valid URL").optional().or(z.literal("")),
  email: z.string().trim().email(),
  phone: z.string().trim().min(6).max(24),
  address: z.string().trim().min(3).max(200),
  city: z.string().trim().min(1).max(80),
  state: z.string().min(1, "State is required"),
  country: z.string().min(1),
  pincode: z.string().regex(/^\d{4,10}$/).optional().or(z.literal("")),
  timezone: z.string().min(1),
  languages: z.array(z.string()).min(1, "Select at least one language"),
  status: z.enum(["active", "inactive", "suspended"] as const),
  brandColor: z.string().optional(),
});

type FormValues = z.infer<typeof schema>;

interface OrganizationFormProps {
  initial?: Organization;
  mode: "create" | "edit";
}

export function OrganizationForm({ initial, mode }: OrganizationFormProps) {
  const navigate = useNavigate();
  const defaults: FormValues = useMemo(
    () => ({
      name: initial?.name ?? "",
      type: (initial?.type ?? ORGANIZATION_TYPES[0]) as OrganizationType,
      website: initial?.website ?? "",
      email: initial?.email ?? "",
      phone: initial?.phone ?? "",
      address: initial?.address ?? "",
      city: initial?.city ?? "",
      state: initial?.state ?? "",
      country: initial?.country ?? "India",
      pincode: initial?.pincode ?? "",
      timezone: initial?.timezone ?? "Asia/Kolkata",
      languages: initial?.languages ?? ["en"],
      status: (initial?.status ?? "active") as OrganizationStatus,
      brandColor: initial?.brandColor ?? "#2563EB",
    }),
    [initial],
  );

  const form = useForm<FormValues>({ resolver: zodResolver(schema), defaultValues: defaults });

  const onSubmit = async (values: FormValues) => {
    const payload: OrganizationInput = { ...values, website: values.website || undefined, pincode: values.pincode || undefined };
    try {
      if (mode === "create") {
        const org = await organizationService.create(payload);
        toast.success("Organization created");
        navigate({ to: "/organizations/$id", params: { id: org.id } });
      } else if (initial) {
        await organizationService.update(initial.id, payload);
        toast.success("Organization updated");
        navigate({ to: "/organizations/$id", params: { id: initial.id } });
      }
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Save failed");
    }
  };

  const languages = form.watch("languages");
  const toggleLang = (code: string) =>
    form.setValue("languages", languages.includes(code) ? languages.filter((c) => c !== code) : [...languages, code]);

  return (
    <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
      <Card className="shadow-card">
        <CardHeader><CardTitle className="text-base">Organization details</CardTitle></CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-2">
          <Field label="Name" error={form.formState.errors.name?.message}>
            <Input {...form.register("name")} />
          </Field>
          <Field label="Type" error={form.formState.errors.type?.message}>
            <Select value={form.watch("type")} onValueChange={(v) => form.setValue("type", v as OrganizationType)}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>{ORGANIZATION_TYPES.map((t) => <SelectItem key={t} value={t}>{t}</SelectItem>)}</SelectContent>
            </Select>
          </Field>
          <Field label="Website" error={form.formState.errors.website?.message}>
            <Input placeholder="https://…" {...form.register("website")} />
          </Field>
          <Field label="Contact email" error={form.formState.errors.email?.message}>
            <Input type="email" {...form.register("email")} />
          </Field>
          <Field label="Phone" error={form.formState.errors.phone?.message}>
            <Input {...form.register("phone")} />
          </Field>
          <Field label="Status">
            <Select value={form.watch("status")} onValueChange={(v) => form.setValue("status", v as OrganizationStatus)}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="active">Active</SelectItem>
                <SelectItem value="inactive">Inactive</SelectItem>
                <SelectItem value="suspended">Suspended</SelectItem>
              </SelectContent>
            </Select>
          </Field>
        </CardContent>
      </Card>

      <Card className="shadow-card">
        <CardHeader><CardTitle className="text-base">Address</CardTitle></CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-2">
          <Field label="Address" className="md:col-span-2" error={form.formState.errors.address?.message}>
            <Textarea rows={2} {...form.register("address")} />
          </Field>
          <Field label="City" error={form.formState.errors.city?.message}>
            <Input {...form.register("city")} />
          </Field>
          <Field label="State" error={form.formState.errors.state?.message}>
            <Select value={form.watch("state")} onValueChange={(v) => form.setValue("state", v)}>
              <SelectTrigger><SelectValue placeholder="Select" /></SelectTrigger>
              <SelectContent>{INDIAN_STATES.map((s) => <SelectItem key={s} value={s}>{s}</SelectItem>)}</SelectContent>
            </Select>
          </Field>
          <Field label="Country">
            <Input {...form.register("country")} />
          </Field>
          <Field label="Pincode" error={form.formState.errors.pincode?.message}>
            <Input {...form.register("pincode")} />
          </Field>
        </CardContent>
      </Card>

      <Card className="shadow-card">
        <CardHeader><CardTitle className="text-base">Brand & localization</CardTitle></CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-2">
          <Field label="Timezone">
            <Select value={form.watch("timezone")} onValueChange={(v) => form.setValue("timezone", v)}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>{TIMEZONES.map((t) => <SelectItem key={t} value={t}>{t}</SelectItem>)}</SelectContent>
            </Select>
          </Field>
          <Field label="Brand color">
            <Input type="color" {...form.register("brandColor")} className="h-10 w-24 p-1" />
          </Field>
          <Field label="Languages" className="md:col-span-2" error={form.formState.errors.languages?.message}>
            <div className="flex flex-wrap gap-1.5">
              {LANGUAGES.map((l) => {
                const active = languages.includes(l.code);
                return (
                  <button
                    key={l.code}
                    type="button"
                    onClick={() => toggleLang(l.code)}
                    className={cn(
                      "rounded-full border px-2.5 py-1 text-xs transition-colors",
                      active ? "border-primary bg-primary/10 text-primary" : "border-border text-muted-foreground hover:border-foreground",
                    )}
                  >
                    {l.label}
                  </button>
                );
              })}
            </div>
          </Field>
        </CardContent>
      </Card>

      <div className="flex justify-end gap-2">
        <Button type="button" variant="outline" onClick={() => navigate({ to: "/organizations" })}>Cancel</Button>
        <Button type="submit" disabled={form.formState.isSubmitting}>{mode === "create" ? "Create organization" : "Save changes"}</Button>
      </div>
    </form>
  );
}

function Field({ label, children, error, className }: { label: string; children: React.ReactNode; error?: string; className?: string }) {
  return (
    <div className={className}>
      <Label className="text-xs uppercase tracking-wide text-muted-foreground">{label}</Label>
      <div className="mt-1.5">{children}</div>
      {error && <p className="mt-1 text-xs text-destructive">{error}</p>}
    </div>
  );
}
