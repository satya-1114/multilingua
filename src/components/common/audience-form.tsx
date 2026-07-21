import { useMemo } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useQuery } from "@tanstack/react-query";
import { toast } from "sonner";
import { useNavigate } from "@tanstack/react-router";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Checkbox } from "@/components/ui/checkbox";
import { Button } from "@/components/ui/button";
import { TagPicker } from "@/components/common/tag-picker";
import { COMMUNICATION_CHANNELS, GENDERS, INDIAN_STATES, LANGUAGES, OCCUPATIONS, districtsFor } from "@/constants/india";
import type { AudienceContact, AudienceInput, AudienceStatus } from "@/types/audience";
import { tagService } from "@/services/tag.service";
import { audienceService } from "@/services/audience.service";
import { organizationService } from "@/services/organization.service";

const phoneRegex = /^[+\d][\d\s\-()]{6,20}$/;

const schema = z.object({
  firstName: z.string().trim().min(1, "First name is required").max(60),
  lastName: z.string().trim().min(1, "Last name is required").max(60),
  email: z.string().trim().email("Invalid email").max(200),
  phone: z.string().trim().regex(phoneRegex, "Invalid phone number"),
  alternatePhone: z.string().trim().regex(phoneRegex, "Invalid phone number").optional().or(z.literal("")),
  dateOfBirth: z.string().optional().or(z.literal("")),
  gender: z.enum(GENDERS).optional(),
  occupation: z.string().optional(),
  organizationId: z.string().optional(),
  department: z.string().max(80).optional(),
  state: z.string().min(1, "State is required"),
  district: z.string().min(1, "District is required"),
  city: z.string().min(1, "City is required").max(80),
  address: z.string().max(200).optional(),
  pincode: z.string().regex(/^\d{6}$/, "6-digit PIN").optional().or(z.literal("")),
  preferredLanguage: z.string().min(1, "Language is required"),
  preferredChannel: z.enum(COMMUNICATION_CHANNELS.map((c) => c.key) as [string, ...string[]]),
  status: z.enum(["active", "inactive", "pending", "opted_out"] as const),
  notes: z.string().max(500).optional(),
  tagIds: z.array(z.string()),
  consentGiven: z.boolean().refine((v) => v === true, "Consent is required"),
});

type FormValues = z.infer<typeof schema>;

interface AudienceFormProps {
  initial?: AudienceContact;
  mode: "create" | "edit";
}

export function AudienceForm({ initial, mode }: AudienceFormProps) {
  const navigate = useNavigate();
  const tagsQuery = useQuery({ queryKey: ["audience", "tags"], queryFn: () => tagService.list() });
  const orgsQuery = useQuery({ queryKey: ["organizations", "all"], queryFn: () => organizationService.listAll() });

  const defaultValues: FormValues = useMemo(
    () => ({
      firstName: initial?.firstName ?? "",
      lastName: initial?.lastName ?? "",
      email: initial?.email ?? "",
      phone: initial?.phone ?? "",
      alternatePhone: initial?.alternatePhone ?? "",
      dateOfBirth: initial?.dateOfBirth ?? "",
      gender: initial?.gender,
      occupation: initial?.occupation ?? "",
      organizationId: initial?.organizationId ?? "",
      department: initial?.department ?? "",
      state: initial?.state ?? "",
      district: initial?.district ?? "",
      city: initial?.city ?? "",
      address: initial?.address ?? "",
      pincode: initial?.pincode ?? "",
      preferredLanguage: initial?.preferredLanguage ?? "en",
      preferredChannel: initial?.preferredChannel ?? "sms",
      status: (initial?.status ?? "active") as AudienceStatus,
      notes: initial?.notes ?? "",
      tagIds: initial?.tags.map((t) => t.id) ?? [],
      consentGiven: initial?.consentGiven ?? false,
    }),
    [initial],
  );

  const form = useForm<FormValues>({ resolver: zodResolver(schema), defaultValues });
  const state = form.watch("state");
  const districts = useMemo(() => districtsFor(state), [state]);

  const onSubmit = async (values: FormValues) => {
    const payload: AudienceInput = { ...values, alternatePhone: values.alternatePhone || undefined, preferredChannel: values.preferredChannel as AudienceInput["preferredChannel"] };
    try {
      if (mode === "create") {
        const created = await audienceService.create(payload);
        toast.success("Contact created");
        navigate({ to: "/audience/$id", params: { id: created.id } });
      } else if (initial) {
        await audienceService.update(initial.id, payload);
        toast.success("Contact updated");
        navigate({ to: "/audience/$id", params: { id: initial.id } });
      }
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Save failed");
    }
  };

  return (
    <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
      <Card className="shadow-card">
        <CardHeader><CardTitle className="text-base">Personal information</CardTitle></CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-2">
          <Field label="First name" error={form.formState.errors.firstName?.message}>
            <Input {...form.register("firstName")} />
          </Field>
          <Field label="Last name" error={form.formState.errors.lastName?.message}>
            <Input {...form.register("lastName")} />
          </Field>
          <Field label="Email" error={form.formState.errors.email?.message}>
            <Input type="email" {...form.register("email")} />
          </Field>
          <Field label="Phone" error={form.formState.errors.phone?.message}>
            <Input {...form.register("phone")} />
          </Field>
          <Field label="Alternate phone" error={form.formState.errors.alternatePhone?.message}>
            <Input {...form.register("alternatePhone")} />
          </Field>
          <Field label="Date of birth">
            <Input type="date" {...form.register("dateOfBirth")} />
          </Field>
          <Field label="Gender">
            <Select value={form.watch("gender") ?? ""} onValueChange={(v) => form.setValue("gender", v as FormValues["gender"])}>
              <SelectTrigger><SelectValue placeholder="Select" /></SelectTrigger>
              <SelectContent>{GENDERS.map((g) => <SelectItem key={g} value={g}>{g}</SelectItem>)}</SelectContent>
            </Select>
          </Field>
          <Field label="Occupation">
            <Select value={form.watch("occupation") ?? ""} onValueChange={(v) => form.setValue("occupation", v)}>
              <SelectTrigger><SelectValue placeholder="Select" /></SelectTrigger>
              <SelectContent>{OCCUPATIONS.map((o) => <SelectItem key={o} value={o}>{o}</SelectItem>)}</SelectContent>
            </Select>
          </Field>
        </CardContent>
      </Card>

      <Card className="shadow-card">
        <CardHeader><CardTitle className="text-base">Organization</CardTitle></CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-2">
          <Field label="Organization">
            <Select value={form.watch("organizationId") ?? ""} onValueChange={(v) => form.setValue("organizationId", v)}>
              <SelectTrigger><SelectValue placeholder="Select organization" /></SelectTrigger>
              <SelectContent>{(orgsQuery.data ?? []).map((o) => <SelectItem key={o.id} value={o.id}>{o.name}</SelectItem>)}</SelectContent>
            </Select>
          </Field>
          <Field label="Department">
            <Input {...form.register("department")} />
          </Field>
        </CardContent>
      </Card>

      <Card className="shadow-card">
        <CardHeader><CardTitle className="text-base">Location</CardTitle></CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-2">
          <Field label="State" error={form.formState.errors.state?.message}>
            <Select
              value={form.watch("state")}
              onValueChange={(v) => { form.setValue("state", v); form.setValue("district", ""); }}
            >
              <SelectTrigger><SelectValue placeholder="Select state" /></SelectTrigger>
              <SelectContent>{INDIAN_STATES.map((s) => <SelectItem key={s} value={s}>{s}</SelectItem>)}</SelectContent>
            </Select>
          </Field>
          <Field label="District" error={form.formState.errors.district?.message}>
            <Select value={form.watch("district")} onValueChange={(v) => form.setValue("district", v)} disabled={!state}>
              <SelectTrigger><SelectValue placeholder={state ? "Select district" : "Select state first"} /></SelectTrigger>
              <SelectContent>
                {(districts.length ? districts : [state]).filter(Boolean).map((d) => (
                  <SelectItem key={d} value={d}>{d}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </Field>
          <Field label="City" error={form.formState.errors.city?.message}>
            <Input {...form.register("city")} />
          </Field>
          <Field label="Pincode" error={form.formState.errors.pincode?.message}>
            <Input {...form.register("pincode")} maxLength={6} />
          </Field>
          <Field label="Address" className="md:col-span-2">
            <Textarea rows={2} {...form.register("address")} />
          </Field>
        </CardContent>
      </Card>

      <Card className="shadow-card">
        <CardHeader><CardTitle className="text-base">Communication</CardTitle></CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-2">
          <Field label="Preferred language" error={form.formState.errors.preferredLanguage?.message}>
            <Select value={form.watch("preferredLanguage")} onValueChange={(v) => form.setValue("preferredLanguage", v)}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>{LANGUAGES.map((l) => <SelectItem key={l.code} value={l.code}>{l.label}</SelectItem>)}</SelectContent>
            </Select>
          </Field>
          <Field label="Preferred channel">
            <Select value={form.watch("preferredChannel")} onValueChange={(v) => form.setValue("preferredChannel", v)}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>{COMMUNICATION_CHANNELS.map((c) => <SelectItem key={c.key} value={c.key}>{c.label}</SelectItem>)}</SelectContent>
            </Select>
          </Field>
          <Field label="Status">
            <Select value={form.watch("status")} onValueChange={(v) => form.setValue("status", v as AudienceStatus)}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="active">Active</SelectItem>
                <SelectItem value="inactive">Inactive</SelectItem>
                <SelectItem value="pending">Pending</SelectItem>
                <SelectItem value="opted_out">Opted out</SelectItem>
              </SelectContent>
            </Select>
          </Field>
          <Field label="Tags" className="md:col-span-2">
            <TagPicker
              tags={tagsQuery.data ?? []}
              value={form.watch("tagIds")}
              onChange={(v) => form.setValue("tagIds", v)}
              onCreate={async (name) => tagService.create({ name, color: "#2563EB" })}
            />
          </Field>
          <Field label="Notes" className="md:col-span-2">
            <Textarea rows={3} {...form.register("notes")} />
          </Field>
        </CardContent>
      </Card>

      <Card className="shadow-card">
        <CardContent className="flex items-start gap-3 p-5">
          <Checkbox
            id="consent"
            checked={form.watch("consentGiven")}
            onCheckedChange={(v) => form.setValue("consentGiven", v === true, { shouldValidate: true })}
          />
          <div className="space-y-1">
            <Label htmlFor="consent" className="text-sm font-medium">
              I confirm this contact has consented to receive communications.
            </Label>
            {form.formState.errors.consentGiven && (
              <p className="text-xs text-destructive">{form.formState.errors.consentGiven.message}</p>
            )}
          </div>
        </CardContent>
      </Card>

      <div className="flex justify-end gap-2">
        <Button type="button" variant="outline" onClick={() => navigate({ to: "/audience" })}>Cancel</Button>
        <Button type="submit" disabled={form.formState.isSubmitting}>
          {mode === "create" ? "Create contact" : "Save changes"}
        </Button>
      </div>
    </form>
  );
}

function Field({
  label, children, error, className,
}: { label: string; children: React.ReactNode; error?: string; className?: string }) {
  return (
    <div className={className}>
      <Label className="text-xs uppercase tracking-wide text-muted-foreground">{label}</Label>
      <div className="mt-1.5">{children}</div>
      {error && <p className="mt-1 text-xs text-destructive">{error}</p>}
    </div>
  );
}
