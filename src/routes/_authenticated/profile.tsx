import { useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useQuery } from "@tanstack/react-query";
import { format } from "date-fns";
import { toast } from "sonner";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Switch } from "@/components/ui/switch";
import { SectionHeader } from "@/components/common/section-header";
import { FormField, PasswordField } from "@/components/common/form-field";
import { PasswordStrengthMeter } from "@/components/common/password-strength-meter";
import { RoleBadge } from "@/components/common/role-badge";
import { StatusChip } from "@/components/common/status-chip";
import { DataTable } from "@/components/common/data-table";
import { EmptyState } from "@/components/common/empty-state";
import { useAuth } from "@/contexts/auth-context";
import { authService } from "@/services/auth.service";
import { userService } from "@/services/user.service";

export const Route = createFileRoute("/_authenticated/profile")({
  head: () => ({
    meta: [
      { title: "Profile — Multilingua" },
      { name: "robots", content: "noindex" },
    ],
  }),
  component: ProfilePage,
});

const profileSchema = z.object({
  firstName: z.string().trim().min(2, "Required").max(60),
  lastName: z.string().trim().min(2, "Required").max(60),
  email: z.string().trim().email("Enter a valid email").max(255),
  phone: z.string().trim().max(24),
  timezone: z.string().min(1),
  locale: z.string().min(1),
});

type ProfileFormValues = z.infer<typeof profileSchema>;

const passwordSchema = z
  .object({
    current: z.string().min(6, "Enter your current password"),
    next: z
      .string()
      .min(8, "Minimum 8 characters")
      .regex(/[A-Z]/, "Include an uppercase letter")
      .regex(/[a-z]/, "Include a lowercase letter")
      .regex(/\d/, "Include a number"),
    confirm: z.string(),
  })
  .refine((v) => v.next === v.confirm, {
    path: ["confirm"],
    message: "Passwords don't match",
  });

type PasswordFormValues = z.infer<typeof passwordSchema>;

function initialsOf(name: string) {
  return name
    .split(" ")
    .map((n) => n[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();
}

function ProfilePage() {
  const { user } = useAuth();
  const [twoFactor, setTwoFactor] = useState(user?.twoFactorEnabled ?? false);

  const profileForm = useForm<ProfileFormValues>({
    resolver: zodResolver(profileSchema),
    defaultValues: {
      firstName: user?.firstName ?? "",
      lastName: user?.lastName ?? "",
      email: user?.email ?? "",
      phone: user?.phone ?? "",
      timezone: user?.timezone ?? "UTC",
      locale: user?.locale ?? "en",
    },
  });

  const passwordForm = useForm<PasswordFormValues>({
    resolver: zodResolver(passwordSchema),
    defaultValues: { current: "", next: "", confirm: "" },
  });

  const nextPassword = passwordForm.watch("next");

  const historyQuery = useQuery({
    queryKey: ["login-history"],
    queryFn: () => userService.getLoginHistory(),
  });

const onSaveProfile = profileForm.handleSubmit(
  async (values) => {
    console.log("SUCCESS");
    console.log(values);
  },
  (errors) => {
    console.log("FORM ERRORS");
    console.log(errors);
  }
);

  const onChangePassword = passwordForm.handleSubmit(async (values) => {
    await authService.changePassword(values.current, values.next);
    passwordForm.reset();
    toast.success("Password changed");
  });

  async function toggleTwoFactor(next: boolean) {
    setTwoFactor(next);
    if (next) {
      await userService.enableTwoFactor();
      toast.success("Two-factor authentication enabled");
    } else {
      await userService.disableTwoFactor();
      toast.success("Two-factor authentication disabled");
    }
  }

  if (!user) return null;

  return (
    <div className="space-y-6">
      <SectionHeader title="Profile" description="Manage your account, credentials, and security." />

      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="shadow-card lg:col-span-1">
          <CardContent className="flex flex-col items-center gap-3 p-6 text-center">
            <Avatar className="h-20 w-20">
              {user.avatarUrl && <AvatarImage src={user.avatarUrl} alt={user.fullName} />}
              <AvatarFallback className="bg-primary text-lg text-primary-foreground">
                {initialsOf(user.fullName)}
              </AvatarFallback>
            </Avatar>
            <div>
              <p className="text-base font-semibold text-foreground">{user.fullName}</p>
              <p className="text-sm text-muted-foreground">{user.email}</p>
              <div className="mt-2 flex flex-wrap items-center justify-center gap-1.5">
                <RoleBadge role={user.role} />
                <StatusChip
                  label={user.emailVerified ? "Verified" : "Unverified"}
                  tone={user.emailVerified ? "success" : "warning"}
                />
              </div>
            </div>
            <Button size="sm" variant="outline">
              Upload photo
            </Button>
            <div className="w-full space-y-1 border-t border-border pt-3 text-left text-xs text-muted-foreground">
              <p><span className="font-medium text-foreground">Organization:</span> {user.organization.name}</p>
              <p><span className="font-medium text-foreground">Type:</span> {user.organization.type}</p>
              <p><span className="font-medium text-foreground">Member since:</span> {format(new Date(user.createdAt), "MMM d, yyyy")}</p>
            </div>
          </CardContent>
        </Card>

        <Card className="shadow-card lg:col-span-2">
          <CardHeader>
            <CardTitle className="text-base">Basic information</CardTitle>
            <CardDescription>Update how your name and contact details appear across the workspace.</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={onSaveProfile} className="space-y-4">
              <div className="grid gap-4 sm:grid-cols-2">
                <FormField id="firstName" label="First name" error={profileForm.formState.errors.firstName?.message} {...profileForm.register("firstName")} />
                <FormField id="lastName" label="Last name" error={profileForm.formState.errors.lastName?.message} {...profileForm.register("lastName")} />
              </div>
              <div className="grid gap-4 sm:grid-cols-2">
                <FormField id="email" label="Email" type="email" error={profileForm.formState.errors.email?.message} {...profileForm.register("email")} />
                <FormField id="phone" label="Phone" type="tel" error={profileForm.formState.errors.phone?.message} {...profileForm.register("phone")} />
              </div>
              <div className="grid gap-4 sm:grid-cols-2">
                <FormField id="timezone" label="Timezone" error={profileForm.formState.errors.timezone?.message} {...profileForm.register("timezone")} />
                <FormField id="locale" label="Language" error={profileForm.formState.errors.locale?.message} {...profileForm.register("locale")} />
              </div>
              <div className="flex justify-end">
                <Button type="submit" disabled={profileForm.formState.isSubmitting}>
                  {profileForm.formState.isSubmitting ? "Saving…" : "Save changes"}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card className="shadow-card">
          <CardHeader>
            <CardTitle className="text-base">Change password</CardTitle>
            <CardDescription>Use a strong password unique to this account.</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={onChangePassword} className="space-y-4">
              <PasswordField
                id="current"
                label="Current password"
                autoComplete="current-password"
                error={passwordForm.formState.errors.current?.message}
                {...passwordForm.register("current")}
              />
              <div className="space-y-2">
                <PasswordField
                  id="next"
                  label="New password"
                  autoComplete="new-password"
                  error={passwordForm.formState.errors.next?.message}
                  {...passwordForm.register("next")}
                />
                <PasswordStrengthMeter password={nextPassword} />
              </div>
              <PasswordField
                id="confirm"
                label="Confirm new password"
                autoComplete="new-password"
                error={passwordForm.formState.errors.confirm?.message}
                {...passwordForm.register("confirm")}
              />
              <div className="flex justify-end">
                <Button type="submit" disabled={passwordForm.formState.isSubmitting}>
                  {passwordForm.formState.isSubmitting ? "Updating…" : "Update password"}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>

        <Card className="shadow-card">
          <CardHeader>
            <CardTitle className="text-base">Account security</CardTitle>
            <CardDescription>Extra layers to keep your account safe.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-start justify-between rounded-lg border border-border p-4">
              <div className="min-w-0">
                <p className="text-sm font-semibold text-foreground">Two-factor authentication</p>
                <p className="mt-1 text-xs text-muted-foreground">
                  Require a one-time code at every sign-in. Recommended for all admins.
                </p>
              </div>
              <Switch checked={twoFactor} onCheckedChange={toggleTwoFactor} aria-label="Toggle two-factor authentication" />
            </div>
            <div className="rounded-lg border border-border p-4">
              <p className="text-sm font-semibold text-foreground">Active sessions</p>
              <p className="mt-1 text-xs text-muted-foreground">
                Sign out of all other devices to revoke sessions elsewhere.
              </p>
              <Button variant="outline" size="sm" className="mt-3">
                Sign out other sessions
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card className="shadow-card">
        <CardHeader>
          <CardTitle className="text-base">Recent login activity</CardTitle>
          <CardDescription>Review recent sign-in attempts on your account.</CardDescription>
        </CardHeader>
        <CardContent>
          {historyQuery.isLoading ? (
            <p className="text-sm text-muted-foreground">Loading…</p>
          ) : (historyQuery.data ?? []).length === 0 ? (
            <EmptyState title="No login activity yet" />
          ) : (
            <DataTable
              rowKey={(r) => r.id}
              rows={historyQuery.data ?? []}
              columns={[
                { key: "date", header: "Date", render: (r) => format(new Date(r.timestamp), "MMM d, yyyy HH:mm") },
                { key: "device", header: "Device", render: (r) => `${r.device} · ${r.browser}` },
                { key: "location", header: "Location", render: (r) => r.location },
                { key: "ip", header: "IP address", render: (r) => <span className="font-mono text-xs">{r.ipAddress}</span> },
                {
                  key: "status",
                  header: "Status",
                  align: "right",
                  render: (r) => (
                    <StatusChip
                      label={r.status === "success" ? "Success" : "Failed"}
                      tone={r.status === "success" ? "success" : "danger"}
                    />
                  ),
                },
              ]}
            />
          )}
        </CardContent>
      </Card>
    </div>
  );
}
