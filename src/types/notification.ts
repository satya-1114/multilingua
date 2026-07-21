export type NotificationCategory = "campaign" | "system" | "team" | "billing" | "security";
export type NotificationPriority = "low" | "normal" | "high" | "critical";

export interface AppNotification {
  id: string;
  title: string;
  message: string;
  category: NotificationCategory;
  priority: NotificationPriority;
  read: boolean;
  archived: boolean;
  timestamp: string;
  href?: string;
  actor?: string;
}
