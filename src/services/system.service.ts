import type { FeatureFlag, PlatformConfigSection, ReleaseNote, LicenseInfo } from "@/types/system";
import { mockFeatureFlags, mockPlatformConfig, mockReleaseNotes, mockLicense } from "@/lib/mock/platform";

const delay = <T>(v: T, ms = 220): Promise<T> => new Promise((r) => setTimeout(() => r(v), ms));

let flags: FeatureFlag[] = [...mockFeatureFlags];
let config: PlatformConfigSection[] = [...mockPlatformConfig];
let maintenance = false;

export const systemService = {
  async flags(): Promise<FeatureFlag[]> { return delay([...flags]); },
  async toggleFlag(key: string): Promise<void> {
    flags = flags.map((f) => (f.key === key ? { ...f, enabled: !f.enabled, updatedAt: new Date().toISOString() } : f));
    return delay(undefined, 120);
  },
  async setRollout(key: string, percent: number): Promise<void> {
    flags = flags.map((f) => (f.key === key ? { ...f, rolloutPercent: percent, updatedAt: new Date().toISOString() } : f));
    return delay(undefined, 120);
  },
  async config(): Promise<PlatformConfigSection[]> { return delay(config); },
  async updateConfig(sectionId: string, key: string, value: string | number | boolean): Promise<void> {
    config = config.map((s) =>
      s.id === sectionId
        ? { ...s, entries: s.entries.map((e) => (e.key === key ? { ...e, value } : e)) }
        : s,
    );
    return delay(undefined, 120);
  },
  async releaseNotes(): Promise<ReleaseNote[]> { return delay(mockReleaseNotes); },
  async license(): Promise<LicenseInfo> { return delay(mockLicense); },
  async maintenance(): Promise<boolean> { return delay(maintenance, 60); },
  async setMaintenance(on: boolean): Promise<void> { maintenance = on; return delay(undefined, 100); },
  async version(): Promise<{ version: string; environment: string; commit: string; builtAt: string }> {
    return delay({ version: "5.2.0", environment: "production", commit: "a41f9c2", builtAt: new Date().toISOString() });
  },
};
