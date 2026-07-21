import { createTypedSocket } from "./socket-client";

export interface CampaignSocketEvent {
  type: "status_changed" | "delivery_update" | "engagement";
  campaignId: string;
  payload: Record<string, unknown>;
}

export const campaignSocket = createTypedSocket<CampaignSocketEvent>({
  url: "wss://gateway.example/campaigns",
  reconnect: true,
});
