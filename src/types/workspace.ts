export interface Workspace {
  id: string;
  tenantId: string;
  name: string;
  slug: string;
  logoUrl?: string;
  colorAccent: string;
  organizationType: string;
  plan: "starter" | "growth" | "enterprise";
  region: string;
  timezone: string;
  languages: string[];
  primaryLanguage: string;
  storageQuotaGb: number;
  storageUsedGb: number;
  apiQuotaMonthly: number;
  apiUsedThisMonth: number;
  memberCount: number;
  isDefault?: boolean;
  isFavorite?: boolean;
  lastAccessedAt: string;
  createdAt: string;
}

export interface WorkspaceContext {
  workspace: Workspace;
  role: string;
  permissions: string[];
}

export interface WorkspaceBranding {
  logoUrl?: string;
  faviconUrl?: string;
  primaryColor: string;
  accentColor: string;
  emailFooter: string;
  supportEmail: string;
}

export interface WorkspaceUsage {
  storageUsedGb: number;
  storageQuotaGb: number;
  apiUsedThisMonth: number;
  apiQuotaMonthly: number;
  seatsUsed: number;
  seatsQuota: number;
}
