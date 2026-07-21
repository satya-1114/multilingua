export interface FeatureFlag {
  key: string;
  name: string;
  description: string;
  enabled: boolean;
  scope: "global" | "workspace" | "environment";
  rolloutPercent: number;
  updatedAt: string;
  updatedBy: string;
}

export interface PlatformConfigSection {
  id: string;
  label: string;
  description: string;
  entries: PlatformConfigEntry[];
}

export interface PlatformConfigEntry {
  key: string;
  label: string;
  value: string | number | boolean;
  kind: "text" | "number" | "boolean" | "select";
  options?: string[];
  helper?: string;
}

export interface ReleaseNote {
  version: string;
  date: string;
  title: string;
  highlights: string[];
}

export interface LicenseInfo {
  plan: string;
  seats: number;
  seatsUsed: number;
  renewsOn: string;
  features: string[];
  contractId: string;
}
