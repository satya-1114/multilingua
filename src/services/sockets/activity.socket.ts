import { createTypedSocket } from "./socket-client";

export interface ActivitySocketEvent {
  type: "activity";
  actor: string;
  action: string;
  entity: string;
  entityId?: string;
  timestamp: string;
  metadata?: Record<string, unknown>;
}

export const activitySocket = createTypedSocket<ActivitySocketEvent>({
  url: "wss://gateway.example/activity",
  reconnect: true,
});
