import type { Integration, Webhook, WebhookDelivery } from "@/types/integration";
import { mockIntegrations, mockWebhooks, mockWebhookDeliveries } from "@/lib/mock/platform";

const delay = <T>(v: T, ms = 220): Promise<T> => new Promise((r) => setTimeout(() => r(v), ms));

let integrations: Integration[] = [...mockIntegrations];
let webhooks: Webhook[] = [...mockWebhooks];
const deliveries: WebhookDelivery[] = [...mockWebhookDeliveries];

export const integrationService = {
  async list(): Promise<Integration[]> {
    return delay([...integrations]);
  },
  async get(id: string): Promise<Integration | undefined> {
    return delay(integrations.find((i) => i.id === id));
  },
  async setStatus(id: string, status: Integration["status"]): Promise<void> {
    integrations = integrations.map((i) => (i.id === id ? { ...i, status, lastSyncAt: new Date().toISOString() } : i));
    return delay(undefined, 200);
  },
  async webhooks(): Promise<Webhook[]> {
    return delay([...webhooks]);
  },
  async createWebhook(input: Omit<Webhook, "id" | "successCount" | "failureCount">): Promise<Webhook> {
    const wh: Webhook = { ...input, id: `wh-${Date.now()}`, successCount: 0, failureCount: 0 };
    webhooks = [wh, ...webhooks];
    return delay(wh, 180);
  },
  async toggleWebhook(id: string): Promise<void> {
    webhooks = webhooks.map((w) => (w.id === id ? { ...w, active: !w.active } : w));
    return delay(undefined, 160);
  },
  async deleteWebhook(id: string): Promise<void> {
    webhooks = webhooks.filter((w) => w.id !== id);
    return delay(undefined, 140);
  },
  async testWebhook(id: string): Promise<{ status: number; latencyMs: number }> {
    return delay({ status: 200, latencyMs: 120 + Math.round(Math.random() * 200) }, 500);
  },
  async deliveries(webhookId?: string): Promise<WebhookDelivery[]> {
    return delay(webhookId ? deliveries.filter((d) => d.webhookId === webhookId) : [...deliveries]);
  },
};
