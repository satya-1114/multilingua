export type ScheduleMode = "immediate" | "scheduled" | "recurring";
export type RecurrencePattern = "daily" | "weekly" | "monthly" | "custom";

export interface ScheduleWindow {
  start: string;
  end: string;
}

export interface ScheduleConfig {
  id: string;
  campaignId: string;
  campaignName: string;
  mode: ScheduleMode;
  timezone: string;
  startAt?: string;
  endAt?: string;
  recurrence?: {
    pattern: RecurrencePattern;
    interval: number;
    daysOfWeek?: number[];
    dayOfMonth?: number;
    cronExpression?: string;
  };
  estimatedWindow?: ScheduleWindow;
  createdAt: string;
  updatedAt: string;
}

export interface ScheduleConflict {
  scheduleId: string;
  campaignName: string;
  reason: string;
  severity: "warning" | "critical";
}
