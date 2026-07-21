import type { CampaignStatus } from "@/types/campaign";
import { CAMPAIGN_STATUS_META, CAMPAIGN_TRANSITIONS, isTransitionAllowed, WORKFLOW_STEPS } from "@/constants/campaign";

export interface WorkflowTransition {
  id: string;
  campaignId: string;
  from: CampaignStatus;
  to: CampaignStatus;
  actor: string;
  note?: string;
  at: string;
}

const history: WorkflowTransition[] = [];

export const workflowService = {
  steps: WORKFLOW_STEPS,

  allowedTransitions(from: CampaignStatus): CampaignStatus[] {
    return CAMPAIGN_TRANSITIONS[from] ?? [];
  },

  isAllowed(from: CampaignStatus, to: CampaignStatus): boolean {
    return isTransitionAllowed(from, to);
  },

  meta(status: CampaignStatus) {
    return CAMPAIGN_STATUS_META[status];
  },

  recordTransition(campaignId: string, from: CampaignStatus, to: CampaignStatus, actor: string, note?: string) {
    history.unshift({
      id: `wf-${crypto.randomUUID?.().slice(0, 6) ?? Math.random().toString(36).slice(2, 8)}`,
      campaignId,
      from,
      to,
      actor,
      note,
      at: new Date().toISOString(),
    });
  },

  historyFor(campaignId: string): WorkflowTransition[] {
    return history.filter((h) => h.campaignId === campaignId);
  },
};
