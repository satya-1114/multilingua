export type TemplateCategory =
  | "email"
  | "sms"
  | "whatsapp"
  | "push"
  | "banner"
  | "social"
  | "emergency_alert"
  | "government_notice"
  | "healthcare"
  | "education"
  | "internal"
  | "custom";

export type TemplateStatus = "draft" | "published" | "archived";

export interface TemplateVariable {
  key: string;
  label: string;
  example?: string;
  required?: boolean;
}

export interface TemplateVersion {
  id: string;
  version: number;
  subject?: string;
  body: string;
  authorId: string;
  authorName: string;
  note?: string;
  createdAt: string;
}

export interface CommunicationTemplate {
  id: string;
  name: string;
  category: TemplateCategory;
  language: string;
  status: TemplateStatus;
  subject?: string;
  body: string;
  variables: TemplateVariable[];
  version: number;
  versions: TemplateVersion[];
  usageCount: number;
  createdBy: string;
  createdByName: string;
  createdAt: string;
  updatedAt: string;
  archivedAt?: string;
}

export interface TemplateInput {
  name: string;
  category: TemplateCategory;
  language: string;
  status?: TemplateStatus;
  subject?: string;
  body: string;
  variables?: TemplateVariable[];
  versionNote?: string;
}

export interface TemplateListQuery {
  page?: number;
  pageSize?: number;
  search?: string;
  category?: TemplateCategory[];
  language?: string[];
  status?: TemplateStatus[];
  createdBy?: string;
  sortBy?: string;
  sortDir?: "asc" | "desc";
}
