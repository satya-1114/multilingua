import { useState } from "react";
import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { motion } from "framer-motion";
import { CheckCircle2, Mail } from "lucide-react";
import { AuthLayout } from "@/components/layouts/auth-layout";
import { Button } from "@/components/ui/button";
import { FormField } from "@/components/common/form-field";
import { authService } from "@/services/auth.service";

export const Route = createFileRoute("/forgot-password")({
  head: () => ({
    meta: [
      { title: "Reset password — Multilingua" },
      { name: "description", content: "Reset your Multilingua password." },
      { name: "robots", content: "noindex" },
    ],
  }),
  component: ForgotPasswordPage,
});

const schema = z.object({ email: z.string().trim().email("Enter a valid email").max(255) });
type FormValues = z.infer<typeof schema>;

function ForgotPasswordPage() {
  const navigate = useNavigate();
  const [sent, setSent] = useState<string | null>(null);
  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { email: "" },
    mode: "onBlur",
  });

  const onSubmit = form.handleSubmit(async (values) => {
    await authService.requestPasswordReset(values.email);
    setSent(values.email);
  });

  return (
    <AuthLayout
      title={sent ? "Check your email" : "Reset your password"}
      subtitle={
        sent
          ? "We've sent a 6-digit code to continue the reset."
          : "Enter your email and we'll send a verification code."
      }
      footer={
        <>
          Remembered it?{" "}
          <Link to="/login" className="font-medium text-primary hover:underline">
            Back to sign in
          </Link>
        </>
      }
    >
      {sent ? (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          className="space-y-4"
        >
          <div className="flex items-start gap-3 rounded-lg border border-border bg-muted/40 p-4">
            <div className="flex h-9 w-9 items-center justify-center rounded-full bg-success/15 text-success">
              <CheckCircle2 className="h-4 w-4" />
            </div>
            <div className="text-sm">
              <p className="font-medium text-foreground">Code sent</p>
              <p className="mt-0.5 text-muted-foreground">
                We sent a code to <span className="font-medium text-foreground">{sent}</span>.
                It expires in 10 minutes.
              </p>
            </div>
          </div>
          <Button
            className="w-full"
            onClick={() => navigate({ to: "/verify-otp", search: { email: sent } })}
          >
            Enter verification code
          </Button>
        </motion.div>
      ) : (
        <form onSubmit={onSubmit} className="space-y-4" noValidate>
          <FormField
            id="email"
            label="Email"
            type="email"
            autoComplete="email"
            error={form.formState.errors.email?.message}
            {...form.register("email")}
          />
          <Button type="submit" className="w-full" disabled={form.formState.isSubmitting}>
            <Mail className="mr-2 h-4 w-4" />
            {form.formState.isSubmitting ? "Sending…" : "Send verification code"}
          </Button>
        </form>
      )}
    </AuthLayout>
  );
}
