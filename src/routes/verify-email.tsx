import { useState } from "react";
import { createFileRoute, useNavigate, useSearch, Link } from "@tanstack/react-router";
import { z } from "zod";
import { motion } from "framer-motion";
import { toast } from "sonner";
import { Mail, RefreshCw } from "lucide-react";
import { AuthLayout } from "@/components/layouts/auth-layout";
import { Button } from "@/components/ui/button";
import { InputOTP, InputOTPGroup, InputOTPSlot } from "@/components/ui/input-otp";
import { authService } from "@/services/auth.service";

const searchSchema = z.object({
  email: z.string().email().optional(),
});

export const Route = createFileRoute("/verify-email")({
  validateSearch: (search) => searchSchema.parse(search),
  head: () => ({
    meta: [
      { title: "Verify your email — Multilingua" },
      { name: "robots", content: "noindex" },
    ],
  }),
  component: VerifyEmailPage,
});

function VerifyEmailPage() {
  const navigate = useNavigate();
  const { email } = useSearch({ from: "/verify-email" });
  const [code, setCode] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function verify() {
    if (code.length !== 6) return;
    setSubmitting(true);
    try {
      await authService.verifyEmail(code);
      toast.success("Email verified");
      navigate({ to: "/dashboard" });
    } finally {
      setSubmitting(false);
    }
  }

  async function resend() {
    if (!email) return;
    await authService.resendEmailVerification(email);
    toast.success("Verification email resent");
  }

  return (
    <AuthLayout
      title="Verify your email"
      subtitle={
        email
          ? `We sent a verification code to ${email}. Enter it below to activate your workspace.`
          : "Enter the code from the verification email to continue."
      }
      footer={
        <Link to="/dashboard" className="text-muted-foreground hover:text-foreground">
          Skip for now
        </Link>
      }
    >
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        className="space-y-6"
      >
        <div className="flex items-center justify-center gap-3 rounded-lg border border-border bg-muted/40 p-4 text-sm text-muted-foreground">
          <Mail className="h-4 w-4 text-primary" />
          Verification code sent
        </div>

        <div className="flex justify-center">
          <InputOTP maxLength={6} value={code} onChange={setCode}>
            <InputOTPGroup>
              {[0, 1, 2, 3, 4, 5].map((i) => (
                <InputOTPSlot key={i} index={i} />
              ))}
            </InputOTPGroup>
          </InputOTP>
        </div>

        <Button className="w-full" onClick={verify} disabled={code.length !== 6 || submitting}>
          {submitting ? "Verifying…" : "Verify email"}
        </Button>

        <button
          type="button"
          onClick={resend}
          className="mx-auto flex items-center gap-1.5 text-xs font-medium text-primary hover:underline"
        >
          <RefreshCw className="h-3 w-3" /> Resend code
        </button>
      </motion.div>
    </AuthLayout>
  );
}
