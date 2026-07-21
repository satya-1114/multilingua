import { createTypedSocket } from "./socket-client";

export interface ApprovalSocketEvent {
  type: "requested" | "approved" | "rejected" | "comment";
  campaignId: string;
  actor: string;
  timestamp: string;
  comment?: string;
}

export const approvalSocket = createTypedSocket<ApprovalSocketEvent>({
  url: "wss://gateway.example/approvals",
  reconnect: true,
});
