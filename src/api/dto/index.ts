/**
 * Data transfer objects consumed by services. Kept independent from UI
 * models so a future FastAPI backend can evolve without breaking the app.
 */

export interface IdentifiedDto {
  id: string;
  createdAt: string;
  updatedAt: string;
}

export interface AuthTokenDto {
  accessToken: string;
  refreshToken: string;
  expiresAt: string;
  tokenType: "Bearer";
}

export interface AuthSessionDto {
  user: UserDto;
  token: AuthTokenDto;
  workspaceId: string;
  permissions: string[];
}

export interface UserDto extends IdentifiedDto {
  email: string;
  fullName: string;
  avatarUrl?: string;
  status: "active" | "invited" | "suspended";
  roles: string[];
}

export interface OrganizationDto extends IdentifiedDto {
  name: string;
  slug: string;
  type: string;
  status: string;
  memberCount: number;
}

export interface WorkspaceDto extends IdentifiedDto {
  name: string;
  slug: string;
  plan: string;
  region: string;
  memberCount: number;
}

export interface AudienceContactDto extends IdentifiedDto {
  fullName: string;
  email?: string;
  phone?: string;
  language: string;
  tags: string[];
  status: string;
}

export interface CampaignDto extends IdentifiedDto {
  name: string;
  status: string;
  channels: string[];
  audienceCount: number;
  startsAt?: string;
  endsAt?: string;
}

export interface TemplateDto extends IdentifiedDto {
  name: string;
  category: string;
  channels: string[];
  language: string;
  version: number;
  status: string;
}

export interface CommunicationJobDto extends IdentifiedDto {
  campaignId: string;
  channel: string;
  status: string;
  scheduledAt?: string;
  attempts: number;
}

export interface DeliveryReceiptDto extends IdentifiedDto {
  jobId: string;
  recipientId: string;
  channel: string;
  status: "queued" | "sent" | "delivered" | "failed" | "bounced";
  attempts: number;
  deliveredAt?: string;
  errorCode?: string;
}

export interface AnalyticsKpiDto {
  key: string;
  label: string;
  value: number;
  delta?: number;
  unit?: string;
}

export interface ReportDto extends IdentifiedDto {
  name: string;
  kind: string;
  scheduled: boolean;
  lastRunAt?: string;
}

export interface AutomationDto extends IdentifiedDto {
  name: string;
  status: string;
  version: number;
  runsThisMonth: number;
}

export interface NotificationDto extends IdentifiedDto {
  title: string;
  message: string;
  category: string;
  priority: string;
  read: boolean;
}

export interface MediaAssetDto extends IdentifiedDto {
  name: string;
  mimeType: string;
  sizeBytes: number;
  url: string;
}

export interface AiGenerationDto extends IdentifiedDto {
  prompt: string;
  model: string;
  tokens: number;
  content: string;
}

export interface TranslationJobDto extends IdentifiedDto {
  sourceLanguage: string;
  targetLanguage: string;
  status: string;
  quality: number;
}

export interface MonitoringSampleDto {
  metric: string;
  value: number;
  at: string;
}

export interface SecurityEventDto extends IdentifiedDto {
  actor: string;
  severity: string;
  event: string;
  ip: string;
}

export interface HelpArticleDto extends IdentifiedDto {
  title: string;
  slug: string;
  category: string;
  updatedBy: string;
}
