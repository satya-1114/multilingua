import type { DashboardOverview } from "@/types/dashboard";
import { mockDashboard } from "@/lib/mock/data";

const delay = <T>(v: T, ms = 350): Promise<T> =>
  new Promise((r) => setTimeout(() => r(v), ms));

export const dashboardService = {
  async getOverview(): Promise<DashboardOverview> {
    return delay(mockDashboard);
  },
};
