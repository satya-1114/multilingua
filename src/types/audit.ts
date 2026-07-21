export type AuditAction =
  | "created"
  | "updated"
  | "deleted"
  | "restored"
  | "imported"
  | "exported"
  | "assigned"
  | "unassigned"
  | "logged_in"
  | "logged_out";

export type AuditModule =
  | "audience"
  | "audience_group"
  | "audience_tag"
  | "organization"
  | "user"
  | "campaign"
  | "auth"
  | "settings";

export interface AuditLogEntry {
  id: string;
  action: AuditAction;
  module: AuditModule;
  entityId?: string;
  entityLabel?: string;
  actorId: string;
  actorName: string;
  ipAddress: string;
  userAgent?: string;
  metadata?: Record<string, unknown>;
  createdAt: string;
}

export interface AuditListQuery {
  page?: number;
  pageSize?: number;
  search?: string;
  action?: AuditAction[];
  module?: AuditModule[];
  actorId?: string;
  from?: string;
  to?: string;
}
