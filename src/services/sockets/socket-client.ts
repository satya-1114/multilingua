/**
 * Base WebSocket abstraction. Wraps browser WebSocket with typed handlers and
 * a reconnection strategy. Only the abstraction layer — real gateway URL will
 * be wired when the backend ships.
 */

export type SocketStatus = "idle" | "connecting" | "open" | "closed" | "error";

export interface SocketOptions {
  url: string;
  protocols?: string | string[];
  reconnect?: boolean;
  reconnectDelayMs?: number;
  maxReconnectAttempts?: number;
}

export interface TypedSocket<T> {
  status: SocketStatus;
  connect(): void;
  disconnect(): void;
  send(payload: T): void;
  onMessage(handler: (payload: T) => void): () => void;
  onStatus(handler: (status: SocketStatus) => void): () => void;
}

export function createTypedSocket<T = unknown>(options: SocketOptions): TypedSocket<T> {
  let ws: WebSocket | null = null;
  let status: SocketStatus = "idle";
  let attempts = 0;
  const messageHandlers = new Set<(payload: T) => void>();
  const statusHandlers = new Set<(status: SocketStatus) => void>();

  const setStatus = (next: SocketStatus) => {
    status = next;
    for (const handler of statusHandlers) handler(next);
  };

  const connect = () => {
    if (typeof window === "undefined") return;
    setStatus("connecting");
    try {
      ws = new WebSocket(options.url, options.protocols);
    } catch {
      setStatus("error");
      return;
    }
    ws.onopen = () => {
      attempts = 0;
      setStatus("open");
    };
    ws.onmessage = (event) => {
      try {
        const parsed = JSON.parse(event.data) as T;
        for (const handler of messageHandlers) handler(parsed);
      } catch {
        // Ignore malformed payloads.
      }
    };
    ws.onerror = () => setStatus("error");
    ws.onclose = () => {
      setStatus("closed");
      if (
        options.reconnect &&
        attempts < (options.maxReconnectAttempts ?? 5)
      ) {
        attempts += 1;
        setTimeout(connect, options.reconnectDelayMs ?? 2000 * attempts);
      }
    };
  };

  return {
    get status() {
      return status;
    },
    connect,
    disconnect() {
      ws?.close();
      ws = null;
      setStatus("closed");
    },
    send(payload) {
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify(payload));
      }
    },
    onMessage(handler) {
      messageHandlers.add(handler);
      return () => messageHandlers.delete(handler);
    },
    onStatus(handler) {
      statusHandlers.add(handler);
      return () => statusHandlers.delete(handler);
    },
  };
}
