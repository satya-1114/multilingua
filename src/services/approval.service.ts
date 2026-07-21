import type { Campaign } from "@/types/campaign";
import { campaignService } from "@/services/campaign.service";
import { auditService } from "@/services/audit.service";

const NETWORK_DELAY = 180;
const delay = <T>(v: T, ms = NETWORK_DELAY) => new Promise<T>((r) => setTimeout(() => r(v), ms));

interface Actor {
  id: string;
  name: string;
  role?: string;
}

export const approvalService = {
  async submit(id: string, actor: Actor, comment?: string): Promise<Campaign> {
    const updated = await campaignService.pushApproval(id, {
      actorId: actor.id,
      actorName: actor.name,
      actorRole: actor.role,
      status: "pending",
      comment,
    });
    await campaignService.setStatus(id, "pending_approval", actor.name, comment);
    auditService.record("updated", "campaign", id, updated.name, { approval: "submitted" });
    const fresh = await campaignService.get(id);
    return delay(fresh!);
  },

  async approve(id: string, actor: Actor, comment?: string): Promise<Campaign> {
    await campaignService.pushApproval(id, {
      actorId: actor.id,
      actorName: actor.name,
      actorRole: actor.role,
      status: "approved",
      comment,
    });
    await campaignService.setStatus(id, "approved", actor.name, comment);
    auditService.record("updated", "campaign", id, undefined, { approval: "approved" });
    const fresh = await campaignService.get(id);
    return delay(fresh!);
  },

  async reject(id: string, actor: Actor, comment?: string): Promise<Campaign> {
    await campaignService.pushApproval(id, {
      actorId: actor.id,
      actorName: actor.name,
      actorRole: actor.role,
      status: "rejected",
      comment,
    });
    await campaignService.setStatus(id, "cancelled", actor.name, comment);
    auditService.record("updated", "campaign", id, undefined, { approval: "rejected" });
    const fresh = await campaignService.get(id);
    return delay(fresh!);
  },

  async sendBack(id: string, actor: Actor, comment?: string): Promise<Campaign> {
    await campaignService.pushApproval(id, {
      actorId: actor.id,
      actorName: actor.name,
      actorRole: actor.role,
      status: "sent_back",
      comment,
    });
    await campaignService.setStatus(id, "draft", actor.name, comment);
    auditService.record("updated", "campaign", id, undefined, { approval: "sent_back" });
    const fresh = await campaignService.get(id);
    return delay(fresh!);
  },

  async pendingQueue(): Promise<Campaign[]> {
    return campaignService.listAll({ status: ["pending_approval"] });
  },
};
