import { useState } from "react";
import { createFileRoute, useNavigate, useSearch, Link } from "@tanstack/react-router";
import { z } from "zod";
import { motion } from "framer-motion";
import { toast } from "sonner";
import { AuthLayout } from "@/components/layouts/auth-layout";
import { Button } from "@/components/ui/button";
import { InputOTP, InputOTPGroup, InputOTPSlot } from "@/components/ui/input-otp";
import { authService } from "@/services/auth.service";

const searchSchema = z.object({
  email: z.string().email().optional(),
});

export const Route = createFileRoute("/verify-otp")({
  validateSearch: (search) => searchSchema.parse(search),
  head: () => ({
    meta: [
      { title: "Verify code — Multilingua" },
      { name: "robots", content: "noindex" },
    ],
  }),
  component: VerifyOtpPage,
});

function VerifyOtpPage() {
  const navigate = useNavigate();
  const { email } = useSearch({ from: "/verify-otp" });
  const [code, setCode] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit() {
    if (!email) return;
    setSubmitting(true);
    setError(null);
    try {
      const { token } = await authService.verifyOtp({ email, code });
      navigate({ to: "/reset-password", search: { token } });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Invalid code");
    } finally {
      setSubmitting(false);
    }
  }

  async function resend() {
    if (!email) return;
    await authService.requestPasswordReset(email);
    toast.success("A new code was sent");
  }

  return (
    <AuthLayout
      title="Enter verification code"
      subtitle={
        email
          ? `We sent a 6-digit code to ${email}. Enter it below to continue.`
          : "Enter the 6-digit code we sent to your email."
      }
      footer={
        <>
          Didn't get a code?{" "}
          <button
            type="button"
            onClick={resend}
            className="font-medium text-primary hover:underline"
          >
            Resend
          </button>{" "}
          ·{" "}
          <Link to="/forgot-password" className="font-medium text-primary hover:underline">
            Change email
          </Link>
        </>
      }
    >
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        className="space-y-6"
      >
        <div className="flex justify-center">
          <InputOTP maxLength={6} value={code} onChange={setCode}>
            <InputOTPGroup>
              {[0, 1, 2, 3, 4, 5].map((i) => (
                <InputOTPSlot key={i} index={i} />
              ))}
            </InputOTPGroup>
          </InputOTP>
        </div>
        {error && (
          <p className="text-center text-xs text-destructive" role="alert">
            {error}
          </p>
        )}
        <Button
          className="w-full"
          disabled={code.length !== 6 || submitting}
          onClick={onSubmit}
        >
          {submitting ? "Verifying…" : "Verify code"}
        </Button>
      </motion.div>
    </AuthLayout>
  );
}
