import type { AuditAction, AuditListQuery, AuditLogEntry, AuditModule } from "@/types/audit";
import type { Paginated } from "@/types/common";
import { mockAuditLogs } from "@/lib/mock/audience";

const NETWORK_DELAY = 200;
const delay = <T>(v: T, ms = NETWORK_DELAY) => new Promise<T>((r) => setTimeout(() => r(v), ms));

let logs: AuditLogEntry[] = [...mockAuditLogs];

export const auditService = {
  record(
    action: AuditAction,
    module: AuditModule,
    entityId?: string,
    entityLabel?: string,
    metadata?: Record<string, unknown>,
  ) {
    logs = [
      {
        id: `log-${crypto.randomUUID().slice(0, 8)}`,
        action,
        module,
        entityId,
        entityLabel,
        actorId: "user-1",
        actorName: "Ananya Iyer",
        ipAddress: "10.0.0.1",
        userAgent: typeof navigator !== "undefined" ? navigator.userAgent : "Server",
        metadata,
        createdAt: new Date().toISOString(),
      },
      ...logs,
    ];
  },

  async list(query: AuditListQuery = {}): Promise<Paginated<AuditLogEntry>> {
    const page = query.page ?? 1;
    const pageSize = query.pageSize ?? 25;
    let items = [...logs];

    if (query.search) {
      const q = query.search.toLowerCase();
      items = items.filter(
        (l) =>
          l.actorName.toLowerCase().includes(q) ||
          l.entityLabel?.toLowerCase().includes(q) ||
          l.module.includes(q) ||
          l.action.includes(q),
      );
    }
    if (query.action?.length) items = items.filter((l) => query.action!.includes(l.action));
    if (query.module?.length) items = items.filter((l) => query.module!.includes(l.module));
    if (query.actorId) items = items.filter((l) => l.actorId === query.actorId);
    if (query.from) items = items.filter((l) => l.createdAt >= query.from!);
    if (query.to) items = items.filter((l) => l.createdAt <= query.to!);

    items.sort((a, b) => (a.createdAt < b.createdAt ? 1 : -1));

    const start = (page - 1) * pageSize;
    return delay({
      items: items.slice(start, start + pageSize),
      total: items.length,
      page,
      pageSize,
    });
  },
};
