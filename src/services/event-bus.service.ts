/**
 * Typed pub-sub event bus for cross-module coordination
 * (workspace switches, cache invalidations, toast broadcasts).
 */
type Handler<T> = (payload: T) => void;

export interface EventMap {
  "workspace:switched": { workspaceId: string };
  "notification:new": { id: string };
  "cache:invalidate": { key: string };
  "toast": { title: string; description?: string; variant?: "default" | "destructive" };
  "connectivity:offline": undefined;
  "connectivity:online": undefined;
}

class EventBus {
  private handlers = new Map<keyof EventMap, Set<Handler<unknown>>>();

  on<K extends keyof EventMap>(event: K, handler: Handler<EventMap[K]>): () => void {
    const set = this.handlers.get(event) ?? new Set();
    set.add(handler as Handler<unknown>);
    this.handlers.set(event, set);
    return () => set.delete(handler as Handler<unknown>);
  }

  emit<K extends keyof EventMap>(event: K, payload: EventMap[K]): void {
    this.handlers.get(event)?.forEach((h) => {
      try { (h as Handler<EventMap[K]>)(payload); } catch { /* noop */ }
    });
  }
}

export const eventBus = new EventBus();
