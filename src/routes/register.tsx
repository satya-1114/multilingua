import { useMemo } from "react";
import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { toast } from "sonner";
import { motion } from "framer-motion";
import { AuthLayout } from "@/components/layouts/auth-layout";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { FormField, PasswordField } from "@/components/common/form-field";
import { PasswordStrengthMeter } from "@/components/common/password-strength-meter";
import { useAuth } from "@/contexts/auth-context";
import {
  ORGANIZATION_TYPES,
  REGISTRATION_ROLES,
  ROLES,
  ROLE_METADATA,
  VOLUNTEER_AVAILABILITY,
  type Role,
} from "@/constants/rbac";

export const Route = createFileRoute("/register")({
  head: () => ({
    meta: [
      { title: "Create account — Multilingua" },
      { name: "description", content: "Create your Multilingua account." },
      { name: "robots", content: "noindex" },
    ],
  }),
  component: RegisterPage,
});

// Registration-selectable roles only — Super Admin is never listed.
const SELECTABLE_ROLES = REGISTRATION_ROLES.filter(
  (r) => r !== ROLES.SUPER_ADMIN,
) as Exclude<Role, typeof ROLES.SUPER_ADMIN>[];

const baseSchema = {
  fullName: z.string().trim().min(2, "Enter your full name").max(120),
  email: z.string().trim().email("Enter a valid email").max(255),
  phone: z
    .string()
    .trim()
    .min(6, "Enter a valid phone number")
    .max(24)
    .regex(/^[+()\-\s\d]+$/, "Only digits, spaces, +, -, ( and ) are allowed"),
  password: z
    .string()
    .min(8, "Minimum 8 characters")
    .max(128)
    .regex(/[A-Z]/, "Include an uppercase letter")
    .regex(/[a-z]/, "Include a lowercase letter")
    .regex(/\d/, "Include a number"),
  confirmPassword: z.string(),
  acceptTerms: z.literal(true, { errorMap: () => ({ message: "Required" }) }),
  acceptPrivacy: z.literal(true, { errorMap: () => ({ message: "Required" }) }),
};

const schema = z.discriminatedUnion("role", [
  z.object({
    role: z.literal(ROLES.VIEWER),
    ...baseSchema,
  }),
  z.object({
    role: z.literal(ROLES.VOLUNTEER),
    ...baseSchema,
    languagesKnown: z.string().trim().min(2, "List at least one language").max(200),
    skills: z.string().trim().min(2, "List at least one skill").max(300),
    currentLocation: z.string().trim().min(2, "Enter your current location").max(120),
    availability: z.string().min(1, "Select your availability"),
  }),
  z.object({
    role: z.literal(ROLES.CAMPAIGN_MANAGER),
    ...baseSchema,
    organizationName: z.string().trim().min(2, "Enter your organization").max(120),
    organizationType: z.string().min(1, "Select an organization type"),
    officeAddress: z.string().trim().min(4, "Enter your office address").max(240),
    designation: z.string().trim().min(2, "Enter your designation").max(120),
  }),
]).refine((v) => v.password === v.confirmPassword, {
  path: ["confirmPassword"],
  message: "Passwords don't match",
});

type FormValues = z.infer<typeof schema>;

function RegisterPage() {
  const navigate = useNavigate();
  const { register: registerUser } = useAuth();
  const organizationTypes = useMemo(() => ORGANIZATION_TYPES, []);

  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    mode: "onBlur",
    defaultValues: {
      role: ROLES.VIEWER,
      fullName: "",
      email: "",
      phone: "",
      password: "",
      confirmPassword: "",
      acceptTerms: false as unknown as true,
      acceptPrivacy: false as unknown as true,
    } as Partial<FormValues> as FormValues,
  });

  const role = form.watch("role");
  const password = form.watch("password");

  const onSubmit = form.handleSubmit(async (values) => {
    try {
      await registerUser({
        role: values.role,
        fullName: values.fullName,
        email: values.email,
        phone: values.phone,
        password: values.password,
        acceptTerms: values.acceptTerms,
        acceptPrivacy: values.acceptPrivacy,
        ...(values.role === ROLES.CAMPAIGN_MANAGER
          ? {
              organizationName: values.organizationName,
              organizationType: values.organizationType,
              officeAddress: values.officeAddress,
              designation: values.designation,
            }
          : {}),
        ...(values.role === ROLES.VOLUNTEER
          ? {
              languagesKnown: values.languagesKnown
                .split(",")
                .map((s) => s.trim())
                .filter(Boolean),
              skills: values.skills
                .split(",")
                .map((s) => s.trim())
                .filter(Boolean),
              currentLocation: values.currentLocation,
              availability: values.availability,
            }
          : {}),
      });
      toast.success("Account created — verify your email to continue");
      navigate({ to: "/verify-email", search: { email: values.email } });
    } catch (err) {
      const message = err instanceof Error ? err.message : "Sign-up failed";
      toast.error(message);
    }
  });

  const errors = form.formState.errors as Record<string, { message?: string } | undefined>;

  return (
    <AuthLayout
      title="Create your account"
      subtitle="Join Multilingua and start reaching every community in their language."
      footer={
        <>
          Already have an account?{" "}
          <Link to="/login" className="font-medium text-primary hover:underline">
            Sign in
          </Link>
        </>
      }
    >
      <motion.form
        onSubmit={onSubmit}
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.25 }}
        className="space-y-4"
        noValidate
      >
        <div className="space-y-1.5">
          <Label>I'm signing up as</Label>
          <Controller
            control={form.control}
            name="role"
            render={({ field }) => (
              <div className="grid gap-2 sm:grid-cols-3">
                {SELECTABLE_ROLES.map((r) => {
                  const meta = ROLE_METADATA[r];
                  const active = field.value === r;
                  return (
                    <button
                      key={r}
                      type="button"
                      onClick={() => field.onChange(r)}
                      className={
                        "rounded-lg border p-3 text-left transition-colors " +
                        (active
                          ? "border-primary bg-primary/5 ring-1 ring-primary"
                          : "border-border hover:bg-muted/40")
                      }
                      aria-pressed={active}
                    >
                      <div className="text-sm font-semibold text-foreground">{meta.label}</div>
                      <div className="mt-0.5 text-xs text-muted-foreground">
                        {meta.description}
                      </div>
                    </button>
                  );
                })}
              </div>
            )}
          />
        </div>

        <FormField
          id="fullName"
          label="Full name"
          autoComplete="name"
          error={errors.fullName?.message}
          {...form.register("fullName")}
        />

        <FormField
          id="email"
          label="Email"
          type="email"
          autoComplete="email"
          error={errors.email?.message}
          {...form.register("email")}
        />

        <FormField
          id="phone"
          label="Phone number"
          type="tel"
          autoComplete="tel"
          placeholder="+1 555 010 1234"
          error={errors.phone?.message}
          {...form.register("phone")}
        />

        {role === ROLES.CAMPAIGN_MANAGER && (
          <>
            <div className="grid gap-4 sm:grid-cols-2">
              <FormField
                id="organizationName"
                label="Organization name"
                error={errors.organizationName?.message}
                {...form.register("organizationName" as const)}
              />
              <div className="space-y-1.5">
                <Label htmlFor="organizationType">Organization type</Label>
                <Controller
                  control={form.control}
                  name={"organizationType" as never}
                  render={({ field }) => (
                    <Select
                      value={(field.value as string) ?? ""}
                      onValueChange={field.onChange}
                    >
                      <SelectTrigger id="organizationType">
                        <SelectValue placeholder="Select type" />
                      </SelectTrigger>
                      <SelectContent>
                        {organizationTypes.map((t) => (
                          <SelectItem key={t} value={t}>
                            {t}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  )}
                />
                {errors.organizationType && (
                  <p className="text-xs text-destructive">
                    {errors.organizationType.message}
                  </p>
                )}
              </div>
            </div>

            <FormField
              id="officeAddress"
              label="Office address"
              error={errors.officeAddress?.message}
              {...form.register("officeAddress" as const)}
            />

            <FormField
              id="designation"
              label="Designation"
              placeholder="e.g. Program Director"
              error={errors.designation?.message}
              {...form.register("designation" as const)}
            />
          </>
        )}

        {role === ROLES.VOLUNTEER && (
          <>
            <FormField
              id="languagesKnown"
              label="Languages known"
              placeholder="e.g. English, Hindi, Tamil"
              error={errors.languagesKnown?.message}
              {...form.register("languagesKnown" as const)}
            />
            <FormField
              id="skills"
              label="Skills"
              placeholder="e.g. Content writing, Translation, Field outreach"
              error={errors.skills?.message}
              {...form.register("skills" as const)}
            />
            <FormField
              id="currentLocation"
              label="Current location"
              placeholder="City, State"
              error={errors.currentLocation?.message}
              {...form.register("currentLocation" as const)}
            />
            <div className="space-y-1.5">
              <Label htmlFor="availability">Availability</Label>
              <Controller
                control={form.control}
                name={"availability" as never}
                render={({ field }) => (
                  <Select
                    value={(field.value as string) ?? ""}
                    onValueChange={field.onChange}
                  >
                    <SelectTrigger id="availability">
                      <SelectValue placeholder="Select availability" />
                    </SelectTrigger>
                    <SelectContent>
                      {VOLUNTEER_AVAILABILITY.map((a) => (
                        <SelectItem key={a} value={a}>
                          {a}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
              />
              {errors.availability && (
                <p className="text-xs text-destructive">{errors.availability.message}</p>
              )}
            </div>
          </>
        )}

        <div className="space-y-2">
          <PasswordField
            id="password"
            label="Password"
            autoComplete="new-password"
            error={errors.password?.message}
            {...form.register("password")}
          />
          <PasswordStrengthMeter password={password} />
        </div>

        <PasswordField
          id="confirmPassword"
          label="Confirm password"
          autoComplete="new-password"
          error={errors.confirmPassword?.message}
          {...form.register("confirmPassword")}
        />

        <div className="space-y-2 rounded-lg border border-border bg-muted/40 p-3">
          <label htmlFor="acceptTerms" className="flex items-start gap-2 text-xs">
            <Controller
              control={form.control}
              name="acceptTerms"
              render={({ field }) => (
                <Checkbox
                  id="acceptTerms"
                  checked={field.value === true}
                  onCheckedChange={(v) => field.onChange(v === true)}
                  className="mt-0.5"
                />
              )}
            />
            <span className="leading-relaxed text-muted-foreground">
              I agree to the{" "}
              <a href="#" className="font-medium text-primary hover:underline">
                Terms of Service
              </a>
              .
            </span>
          </label>
          <label htmlFor="acceptPrivacy" className="flex items-start gap-2 text-xs">
            <Controller
              control={form.control}
              name="acceptPrivacy"
              render={({ field }) => (
                <Checkbox
                  id="acceptPrivacy"
                  checked={field.value === true}
                  onCheckedChange={(v) => field.onChange(v === true)}
                  className="mt-0.5"
                />
              )}
            />
            <span className="leading-relaxed text-muted-foreground">
              I acknowledge the{" "}
              <a href="#" className="font-medium text-primary hover:underline">
                Privacy Policy
              </a>{" "}
              and consent to processing of my data.
            </span>
          </label>
          {(errors.acceptTerms || errors.acceptPrivacy) && (
            <p className="text-xs text-destructive">
              Please accept the terms and privacy policy to continue.
            </p>
          )}
        </div>

        <Button type="submit" className="w-full" disabled={form.formState.isSubmitting}>
          {form.formState.isSubmitting ? "Creating account…" : "Create account"}
        </Button>
      </motion.form>
    </AuthLayout>
  );
}
