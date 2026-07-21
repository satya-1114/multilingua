import { createFileRoute, Link } from "@tanstack/react-router";
import { motion } from "framer-motion";
import { Clock } from "lucide-react";
import { AuthLayout } from "@/components/layouts/auth-layout";
import { Button } from "@/components/ui/button";

export const Route = createFileRoute("/session-expired")({
  head: () => ({
    meta: [
      { title: "Session expired — Multilingua" },
      { name: "robots", content: "noindex" },
    ],
  }),
  component: SessionExpiredPage,
});

function SessionExpiredPage() {
  return (
    <AuthLayout
      title="Your session has expired"
      subtitle="For your security, we've signed you out. Please sign in again to continue."
    >
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        className="space-y-6"
      >
        <div className="flex items-center gap-3 rounded-lg border border-border bg-muted/40 p-4 text-sm text-muted-foreground">
          <div className="flex h-9 w-9 items-center justify-center rounded-full bg-warning/15 text-warning-foreground">
            <Clock className="h-4 w-4" />
          </div>
          Sessions expire after a period of inactivity to keep your workspace safe.
        </div>
        <Button asChild className="w-full">
          <Link to="/login">Sign in again</Link>
        </Button>
      </motion.div>
    </AuthLayout>
  );
}
