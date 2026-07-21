import type { ActiveSession, LoginEvent, SecurityAlert, PasswordPolicy } from "@/types/security";
import { mockSessions, mockLogins, mockAlerts, defaultPasswordPolicy } from "@/lib/mock/platform";

const delay = <T>(v: T, ms = 220): Promise<T> => new Promise((r) => setTimeout(() => r(v), ms));

let sessions: ActiveSession[] = [...mockSessions];
let alerts: SecurityAlert[] = [...mockAlerts];
let policy: PasswordPolicy = { ...defaultPasswordPolicy };

export const securityService = {
  async sessions(): Promise<ActiveSession[]> { return delay([...sessions]); },
  async revokeSession(id: string): Promise<void> {
    sessions = sessions.filter((s) => s.id !== id);
    return delay(undefined, 140);
  },
  async logins(): Promise<LoginEvent[]> { return delay([...mockLogins]); },
  async alerts(): Promise<SecurityAlert[]> { return delay([...alerts]); },
  async acknowledgeAlert(id: string): Promise<void> {
    alerts = alerts.map((a) => (a.id === id ? { ...a, status: "acknowledged" } : a));
    return delay(undefined, 120);
  },
  async resolveAlert(id: string): Promise<void> {
    alerts = alerts.map((a) => (a.id === id ? { ...a, status: "resolved" } : a));
    return delay(undefined, 120);
  },
  async policy(): Promise<PasswordPolicy> { return delay({ ...policy }); },
  async updatePolicy(patch: Partial<PasswordPolicy>): Promise<PasswordPolicy> {
    policy = { ...policy, ...patch };
    return delay({ ...policy });
  },
};
