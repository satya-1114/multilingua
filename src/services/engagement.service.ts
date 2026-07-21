import type { EngagementOverview, EngagementReport } from "@/types/engagement";
import { mockEngagementOverview, mockEngagementReports } from "@/lib/mock/communication";

const delay = <T>(v: T, ms = 220): Promise<T> => new Promise((r) => setTimeout(() => r(v), ms));

let reports: EngagementReport[] = [...mockEngagementReports];

export const engagementService = {
  async overview(): Promise<EngagementOverview> { return delay(mockEngagementOverview); },
  async reports(): Promise<EngagementReport[]> { return delay(reports); },
  async saveReport(r: Omit<EngagementReport, "id" | "createdAt">): Promise<EngagementReport> {
    const rec: EngagementReport = { ...r, id: `er-${Date.now().toString(36)}`, createdAt: new Date().toISOString() };
    reports = [rec, ...reports];
    return delay(rec);
  },
  async deleteReport(id: string) {
    reports = reports.filter((r) => r.id !== id);
    return delay({ ok: true });
  },
};
