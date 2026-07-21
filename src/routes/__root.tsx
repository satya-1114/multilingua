import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  Outlet,
  Link,
  createRootRouteWithContext,
  useRouter,
  HeadContent,
  Scripts,
} from "@tanstack/react-router";
import { useEffect, type ReactNode } from "react";
import "@/lib/i18n";
import { syncClientLocale } from "@/lib/i18n";
import { installTokenRefresh } from "@/api/interceptors/token-refresh";


import appCss from "../styles.css?url";
import { reportClientError } from "../lib/error-reporting";
import { ThemeProvider } from "@/contexts/theme-context";
import { AuthProvider } from "@/contexts/auth-context";
import { Toaster } from "@/components/ui/sonner";
import { ErrorBoundary } from "@/components/common/error-boundary";
import { CommandPaletteProvider } from "@/components/common/command-palette";
import { OfflineBanner } from "@/components/common/offline-banner";
import { KeyboardShortcutDialog, useKeyboardShortcutDialog } from "@/components/common/keyboard-shortcut-dialog";
import { Button } from "@/components/ui/button";

function NotFoundComponent() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <div className="max-w-md text-center">
        <p className="text-sm font-semibold text-primary">404</p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight text-foreground">
          Page not found
        </h1>
        <p className="mt-2 text-sm text-muted-foreground">
          The page you're looking for doesn't exist or has been moved.
        </p>
        <div className="mt-6">
          <Button asChild>
            <Link to="/">Return home</Link>
          </Button>
        </div>
      </div>
    </div>
  );
}

function ErrorComponent({ error, reset }: { error: Error; reset: () => void }) {
  const router = useRouter();
  useEffect(() => {
    reportClientError(error, { boundary: "tanstack_root_error_component" });
  }, [error]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <div className="max-w-md text-center">
        <h1 className="text-xl font-semibold tracking-tight text-foreground">
          This page didn't load
        </h1>
        <p className="mt-2 text-sm text-muted-foreground">
          Something went wrong on our end. You can try refreshing or head back home.
        </p>
        <div className="mt-6 flex flex-wrap justify-center gap-2">
          <Button
            onClick={() => {
              router.invalidate();
              reset();
            }}
          >
            Try again
          </Button>
          <Button variant="outline" asChild>
            <a href="/">Go home</a>
          </Button>
        </div>
      </div>
    </div>
  );
}

export const Route = createRootRouteWithContext<{ queryClient: QueryClient }>()({
  head: () => ({
    meta: [
      { charSet: "utf-8" },
      { name: "viewport", content: "width=device-width, initial-scale=1" },
      { title: "Multilingua — AI Multilingual Communication Platform" },
      {
        name: "description",
        content:
          "Enterprise platform to plan, personalize, and deliver AI-powered multilingual public awareness and mass communication campaigns.",
      },
      {
        property: "og:title",
        content: "Multilingua — AI Multilingual Communication Platform",
      },
      {
        property: "og:description",
        content:
          "Plan, personalize, and deliver AI-powered multilingual campaigns at scale.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
    links: [
      { rel: "stylesheet", href: appCss },
      { rel: "icon", href: "/favicon.ico", type: "image/x-icon" },
    ],
  }),
  shellComponent: RootShell,
  component: RootComponent,
  notFoundComponent: NotFoundComponent,
  errorComponent: ErrorComponent,
});

function RootShell({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <head>
        <HeadContent />
      </head>
      <body>
        {children}
        <Scripts />
      </body>
    </html>
  );
}

function RootComponent() {
  const { queryClient } = Route.useRouteContext();
  const [shortcutsOpen, setShortcutsOpen] = useKeyboardShortcutDialog();

  // Client-only initialization. Language detection happens after hydration
  // to avoid SSR/client mismatches (see src/lib/i18n.ts). The token-refresh
  // interceptor is idempotent — safe to call on every mount.
  useEffect(() => {
    syncClientLocale();
    installTokenRefresh();
  }, []);

  return (

    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <ThemeProvider>
          <AuthProvider>
            <CommandPaletteProvider>
              <OfflineBanner />
              <Outlet />
              <KeyboardShortcutDialog open={shortcutsOpen} onOpenChange={setShortcutsOpen} />
              <Toaster richColors position="top-right" />
            </CommandPaletteProvider>
          </AuthProvider>
        </ThemeProvider>
      </QueryClientProvider>
    </ErrorBoundary>
  );
}
