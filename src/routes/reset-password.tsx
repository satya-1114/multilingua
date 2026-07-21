import { useState } from "react";
import { createFileRoute, useNavigate, useSearch, Link } from "@tanstack/react-router";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { motion } from "framer-motion";
import { CheckCircle2 } from "lucide-react";
import { AuthLayout } from "@/components/layouts/auth-layout";
import { Button } from "@/components/ui/button";
import { PasswordField } from "@/components/common/form-field";
import { PasswordStrengthMeter } from "@/components/common/password-strength-meter";
import { authService } from "@/services/auth.service";

const searchSchema = z.object({
  token: z.string().min(1),
});

export const Route = createFileRoute("/reset-password")({
  validateSearch: (search) => searchSchema.parse(search),
  head: () => ({
    meta: [
      { title: "Set a new password — Multilingua" },
      { name: "robots", content: "noindex" },
    ],
  }),
  component: ResetPasswordPage,
});

const schema = z
  .object({
    password: z
      .string()
      .min(8, "Minimum 8 characters")
      .regex(/[A-Z]/, "Include an uppercase letter")
      .regex(/[a-z]/, "Include a lowercase letter")
      .regex(/\d/, "Include a number"),
    confirmPassword: z.string(),
  })
  .refine((v) => v.password === v.confirmPassword, {
    path: ["confirmPassword"],
    message: "Passwords don't match",
  });

type FormValues = z.infer<typeof schema>;

function ResetPasswordPage() {
  const navigate = useNavigate();
  const { token } = useSearch({ from: "/reset-password" });
  const [done, setDone] = useState(false);

  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { password: "", confirmPassword: "" },
    mode: "onBlur",
  });

  const password = form.watch("password");

  const onSubmit = form.handleSubmit(async (values) => {
    await authService.resetPassword({ token, password: values.password });
    setDone(true);
  });

  if (done) {
    return (
      <AuthLayout title="Password updated" subtitle="You can now sign in with your new password.">
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="space-y-4">
          <div className="flex items-start gap-3 rounded-lg border border-border bg-muted/40 p-4">
            <div className="flex h-9 w-9 items-center justify-center rounded-full bg-success/15 text-success">
              <CheckCircle2 className="h-4 w-4" />
            </div>
            <p className="text-sm text-muted-foreground">
              Your password has been updated. For security, all other sessions have been signed out.
            </p>
          </div>
          <Button className="w-full" onClick={() => navigate({ to: "/login" })}>
            Continue to sign in
          </Button>
        </motion.div>
      </AuthLayout>
    );
  }

  return (
    <AuthLayout
      title="Set a new password"
      subtitle="Pick a strong password you don't use elsewhere."
      footer={
        <Link to="/login" className="font-medium text-primary hover:underline">
          Back to sign in
        </Link>
      }
    >
      <form onSubmit={onSubmit} className="space-y-4" noValidate>
        <div className="space-y-2">
          <PasswordField
            id="password"
            label="New password"
            autoComplete="new-password"
            error={form.formState.errors.password?.message}
            {...form.register("password")}
          />
          <PasswordStrengthMeter password={password} />
        </div>
        <PasswordField
          id="confirmPassword"
          label="Confirm password"
          autoComplete="new-password"
          error={form.formState.errors.confirmPassword?.message}
          {...form.register("confirmPassword")}
        />
        <Button type="submit" className="w-full" disabled={form.formState.isSubmitting}>
          {form.formState.isSubmitting ? "Updating…" : "Update password"}
        </Button>
      </form>
    </AuthLayout>
  );
}
