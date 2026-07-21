import type { CommunicationOverview, CommunicationTimelineEvent, NotificationPreferences } from "@/types/communication";
import { mockCommunicationOverview, mockCommunicationTimeline, mockPreferences } from "@/lib/mock/communication";

const delay = <T>(v: T, ms = 220): Promise<T> => new Promise((r) => setTimeout(() => r(v), ms));

let prefs: NotificationPreferences = { ...mockPreferences };

export const communicationService = {
  async overview(): Promise<CommunicationOverview> {
    return delay(mockCommunicationOverview);
  },
  async timeline(entityId: string): Promise<CommunicationTimelineEvent[]> {
    void entityId;
    return delay(mockCommunicationTimeline);
  },
  async getPreferences(): Promise<NotificationPreferences> {
    return delay(prefs);
  },
  async updatePreferences(patch: Partial<NotificationPreferences>): Promise<NotificationPreferences> {
    prefs = { ...prefs, ...patch, updatedAt: new Date().toISOString() };
    return delay(prefs);
  },
};
