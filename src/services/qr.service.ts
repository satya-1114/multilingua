import type { CampaignQrCode, QrAnalytics, PublicCampaign, QrScanEvent } from "@/types/qr";
import { apiService } from "@/services/api.service";

/**
 * Campaign QR service.
 *
 * Thin facade over the existing apiService — no duplicate HTTP layer, no
 * hardcoded fixtures. Backend contract is documented in
 * `docs/BACKEND-QR.md`. All privileged actions are additionally guarded by
 * `campaign_qr:manage` on the server.
 */
export const qrService = {
  /** Fetch the QR code for a campaign, if one has been generated. */
  get(campaignId: string) {
    return apiService.get<CampaignQrCode | null>(`/v1/campaigns/${campaignId}/qr`);
  },

  /** Generate a QR code for a campaign that does not have one yet. */
  generate(campaignId: string) {
    return apiService.post<CampaignQrCode>(`/v1/campaigns/${campaignId}/qr`);
  },

  /**
   * Regenerate — rotates the token and invalidates the previous code.
   * Previously-printed codes stop working immediately.
   */
  regenerate(campaignId: string) {
    return apiService.post<CampaignQrCode>(`/v1/campaigns/${campaignId}/qr/regenerate`);
  },

  /** Enable / disable a QR code without rotating the token. */
  setStatus(campaignId: string, status: "active" | "disabled") {
    return apiService.patch<CampaignQrCode>(`/v1/campaigns/${campaignId}/qr`, { status });
  },

  analytics(campaignId: string) {
    return apiService.get<QrAnalytics>(`/v1/campaigns/${campaignId}/qr/analytics`);
  },

  scans(campaignId: string, params: { page?: number; pageSize?: number } = {}) {
    return apiService.get<{ items: QrScanEvent[]; total: number }>(
      `/v1/campaigns/${campaignId}/qr/scans`,
      { params },
    );
  },

  /**
   * Public (unauthenticated) endpoint used by the scan landing page.
   * Backend must expose this without auth and increment scan counters.
   */
  public(token: string, meta?: { language?: string }) {
    return apiService.get<PublicCampaign>(`/v1/public/campaigns/${token}`, { params: meta });
  },
};
