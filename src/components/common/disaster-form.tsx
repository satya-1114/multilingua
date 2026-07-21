import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  DISASTER_TYPES,
  DISASTER_SEVERITIES,
  DISASTER_STATUSES,
  type Disaster,
  type DisasterInput,
} from "@/types/disaster";

const schema = z.object({
  title: z.string().min(3, "Title is required"),
  description: z.string().optional(),
  disasterType: z.enum(DISASTER_TYPES),
  severity: z.enum(DISASTER_SEVERITIES),
  status: z.enum(DISASTER_STATUSES),
  startedAt: z.string().optional(),
  address: z.string().optional(),
  city: z.string().optional(),
  district: z.string().optional(),
  state: z.string().optional(),
  country: z.string().optional(),
  postalCode: z.string().optional(),
  latitude: z.string().optional(),
  longitude: z.string().optional(),
});

type FormValues = z.infer<typeof schema>;

interface DisasterFormProps {
  initial?: Disaster;
  submitLabel?: string;
  onSubmit: (input: DisasterInput) => Promise<void> | void;
  onCancel?: () => void;
}

/**
 * Reusable disaster create/edit form. Aligned to the backend contract
 * (`backend/app/schemas/disaster.py`) — no client-only fields.
 */
export function DisasterForm({
  initial,
  submitLabel = "Save disaster",
  onSubmit,
  onCancel,
}: DisasterFormProps) {
  const form = useForm<FormValues>({
    resolver: zodResolver(schema) as never,
    defaultValues: {
      title: initial?.title ?? "",
      description: initial?.description ?? "",
      disasterType: initial?.disasterType ?? "flood",
      severity: initial?.severity ?? "medium",
      status: initial?.status ?? "reported",
      startedAt: initial?.startedAt ? initial.startedAt.slice(0, 16) : "",
      address: initial?.address ?? "",
      city: initial?.city ?? "",
      district: initial?.district ?? "",
      state: initial?.state ?? "",
      country: initial?.country ?? "India",
      postalCode: initial?.postalCode ?? "",
      latitude: initial?.latitude != null ? String(initial.latitude) : "",
      longitude: initial?.longitude != null ? String(initial.longitude) : "",
    },
  });

  async function submit(v: FormValues) {
    const lat = v.latitude ? Number(v.latitude) : undefined;
    const lng = v.longitude ? Number(v.longitude) : undefined;
    const input: DisasterInput = {
      title: v.title,
      description: v.description || undefined,
      disasterType: v.disasterType,
      severity: v.severity,
      status: v.status,
      startedAt: v.startedAt ? new Date(v.startedAt).toISOString() : undefined,
      address: v.address || undefined,
      city: v.city || undefined,
      district: v.district || undefined,
      state: v.state || undefined,
      country: v.country || undefined,
      postalCode: v.postalCode || undefined,
      latitude: Number.isFinite(lat) ? lat : undefined,
      longitude: Number.isFinite(lng) ? lng : undefined,
      organizationId: initial?.organizationId ?? undefined,
    };
    await onSubmit(input);
  }

  return (
    <form onSubmit={form.handleSubmit(submit)} className="space-y-6">
      <Card className="shadow-card">
        <CardHeader><CardTitle className="text-base">Basics</CardTitle></CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-2">
          <div className="md:col-span-2">
            <Label htmlFor="title">Title</Label>
            <Input id="title" {...form.register("title")} />
            {form.formState.errors.title && (
              <p className="mt-1 text-xs text-destructive">{form.formState.errors.title.message}</p>
            )}
          </div>
          <div className="md:col-span-2">
            <Label htmlFor="description">Description</Label>
            <Textarea id="description" rows={3} {...form.register("description")} />
          </div>

          <div>
            <Label>Type</Label>
            <Select
              value={form.watch("disasterType")}
              onValueChange={(v) => form.setValue("disasterType", v as FormValues["disasterType"])}
            >
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                {DISASTER_TYPES.map((c) => (
                  <SelectItem key={c} value={c} className="capitalize">
                    {c.replace(/_/g, " ")}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div>
            <Label>Severity</Label>
            <Select
              value={form.watch("severity")}
              onValueChange={(v) => form.setValue("severity", v as FormValues["severity"])}
            >
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                {DISASTER_SEVERITIES.map((s) => (
                  <SelectItem key={s} value={s} className="capitalize">{s}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div>
            <Label>Status</Label>
            <Select
              value={form.watch("status")}
              onValueChange={(v) => form.setValue("status", v as FormValues["status"])}
            >
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                {DISASTER_STATUSES.map((s) => (
                  <SelectItem key={s} value={s} className="capitalize">{s}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div>
            <Label htmlFor="startedAt">Started at</Label>
            <Input id="startedAt" type="datetime-local" {...form.register("startedAt")} />
          </div>
        </CardContent>
      </Card>

      <Card className="shadow-card">
        <CardHeader><CardTitle className="text-base">Location</CardTitle></CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-2">
          <div className="md:col-span-2">
            <Label htmlFor="address">Address</Label>
            <Input id="address" {...form.register("address")} />
          </div>
          <div>
            <Label htmlFor="city">City</Label>
            <Input id="city" {...form.register("city")} />
          </div>
          <div>
            <Label htmlFor="district">District</Label>
            <Input id="district" {...form.register("district")} />
          </div>
          <div>
            <Label htmlFor="state">State</Label>
            <Input id="state" {...form.register("state")} />
          </div>
          <div>
            <Label htmlFor="country">Country</Label>
            <Input id="country" {...form.register("country")} />
          </div>
          <div>
            <Label htmlFor="postalCode">Postal code</Label>
            <Input id="postalCode" {...form.register("postalCode")} />
          </div>
          <div>
            <Label htmlFor="latitude">Latitude</Label>
            <Input id="latitude" placeholder="13.0827" {...form.register("latitude")} />
          </div>
          <div>
            <Label htmlFor="longitude">Longitude</Label>
            <Input id="longitude" placeholder="80.2707" {...form.register("longitude")} />
          </div>
          <p className="md:col-span-2 text-xs text-muted-foreground">
            Coordinates are stored for future map support. No map provider is required today.
          </p>
        </CardContent>
      </Card>

      <div className="flex justify-end gap-2">
        {onCancel && (
          <Button type="button" variant="outline" onClick={onCancel}>Cancel</Button>
        )}
        <Button type="submit" disabled={form.formState.isSubmitting}>
          {submitLabel}
        </Button>
      </div>
    </form>
  );
}
