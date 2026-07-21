import type { AppNotification } from "@/types/notification";
import { mockNotifications } from "@/lib/mock/data";

const delay = <T>(v: T, ms = 280): Promise<T> =>
  new Promise((r) => setTimeout(() => r(v), ms));

let notifications: AppNotification[] = [...mockNotifications];

export const notificationService = {
  async list(): Promise<AppNotification[]> {
    return delay([...notifications]);
  },

  async markRead(id: string): Promise<void> {
    notifications = notifications.map((n) => (n.id === id ? { ...n, read: true } : n));
    return delay(undefined, 120);
  },

  async markAllRead(): Promise<void> {
    notifications = notifications.map((n) => ({ ...n, read: true }));
    return delay(undefined, 120);
  },

  async archive(id: string): Promise<void> {
    notifications = notifications.map((n) =>
      n.id === id ? { ...n, archived: true, read: true } : n,
    );
    return delay(undefined, 120);
  },
};
