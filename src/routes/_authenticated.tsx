import { createFileRoute, Outlet, redirect, useRouterState } from "@tanstack/react-router";
import { AppLayout } from "@/components/layouts/app-layout";
import { NotificationProvider } from "@/contexts/notification-context";
import { tokenStorage } from "@/lib/token-storage";
import { useAuth } from "@/contexts/auth-context";
import { isRouteAllowed } from "@/lib/route-access";
import { ForbiddenView } from "@/components/common/forbidden-view";

/**
 * Pathless layout that gates every child route behind an authenticated
 * session. `ssr: false` because the session lives in client memory and
 * refresh cookies — SSR has no session context.
 *
 * Auth is checked in `beforeLoad` (no token → /login). Role-based access is
 * enforced inside the component via `isRouteAllowed`. Unauthorized paths
 * render an INLINE 403 view inside this same shell — we never navigate
 * away, so the user keeps their session, tokens, and sidebar. Backend RBAC
 * remains authoritative.
 */
export const Route = createFileRoute("/_authenticated")({
  ssr: false,
  beforeLoad: ({ location }) => {
    if (!tokenStorage.getAccessToken() && !tokenStorage.getRefreshToken()) {
      throw redirect({ to: "/login", search: { redirect: location.href } });
    }
  },
  component: AuthenticatedLayout,
});

function AuthenticatedLayout() {
  const { user, isLoading } = useAuth();
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  const denied = !isLoading && user && !isRouteAllowed(pathname, user.role);

  return (
    <NotificationProvider>
      <AppLayout>{denied ? <ForbiddenView /> : <Outlet />}</AppLayout>
    </NotificationProvider>
  );
}
