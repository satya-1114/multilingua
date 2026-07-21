import { useEffect, useState } from "react";
import { WifiOff, Wifi } from "lucide-react";
import { cn } from "@/lib/utils";
import { eventBus } from "@/services/event-bus.service";

/**
 * Renders nothing on the server and during the first client render, then
 * hydrates from the real `navigator.onLine` flag inside `useEffect`. This
 * avoids two SSR pitfalls:
 *   1. Server runtimes (Nitro / Cloudflare Workers) polyfill `navigator`
 *      without `onLine`, so `navigator.onLine` is `undefined` → falsy, which
 *      previously made the banner render "You are offline" for every SSR
 *      response.
 *   2. Reading browser state in a `useState` initializer would still
 *      hydration-mismatch on returning visitors when the real value differs
 *      from the SSR default.
 */
export function OfflineBanner() {
  const [ready, setReady] = useState(false);
  const [online, setOnline] = useState(true);
  const [justReconnected, setJustReconnected] = useState(false);

  useEffect(() => {
    const isOnline = typeof navigator === "undefined" || navigator.onLine !== false;
    setOnline(isOnline);
    setReady(true);

    const on = () => {
      setOnline(true);
      setJustReconnected(true);
      eventBus.emit("connectivity:online", undefined);
      setTimeout(() => setJustReconnected(false), 3000);
    };
    const off = () => {
      setOnline(false);
      eventBus.emit("connectivity:offline", undefined);
    };
    window.addEventListener("online", on);
    window.addEventListener("offline", off);
    return () => {
      window.removeEventListener("online", on);
      window.removeEventListener("offline", off);
    };
  }, []);

  if (!ready) return null;
  if (online && !justReconnected) return null;

  return (
    <div
      role="status"
      className={cn(
        "flex w-full items-center justify-center gap-2 px-4 py-2 text-xs font-medium",
        online ? "bg-success/10 text-success" : "bg-warning/10 text-warning",
      )}
    >
      {online ? <Wifi className="h-3.5 w-3.5" /> : <WifiOff className="h-3.5 w-3.5" />}
      {online ? "Reconnected — syncing latest data" : "You are offline. Some actions are unavailable."}
    </div>
  );
}
