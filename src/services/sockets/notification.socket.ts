import { createTypedSocket } from "./socket-client";
import type { AppNotification } from "@/types/notification";

export interface NotificationSocketEvent {
  type: "created" | "updated" | "read";
  notification: AppNotification;
}

export const notificationSocket = createTypedSocket<NotificationSocketEvent>({
  url: "wss://gateway.example/notifications",
  reconnect: true,
});
