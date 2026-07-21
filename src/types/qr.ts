/**
 * Campaign QR Code types.
 *
 * Every campaign optionally owns a single QR code. The QR encodes the
 * public campaign URL (`/public/campaigns/{id}` or `/campaigns/{slug}`)
 * and the backend tracks scan analytics per code.
 */

export type QrStatus = "active" | "disabled";

export interface CampaignQrCode {
  id: string;
  campaignId: string;
  /** Absolute URL the QR encodes. Backend is the source of truth. */
  targetUrl: string;
  /** Short opaque token used in the public URL, e.g. `/public/campaigns/{token}`. */
  token: string;
  status: QrStatus;
  version: number;
  createdAt: string;
  updatedAt: string;
  createdBy?: string;
  lastScanAt?: string;
  totalScans: number;
  uniqueScans: number;
}

export type QrDeviceType = "mobile" | "tablet" | "desktop" | "unknown";

export interface QrScanEvent {
  id: string;
  qrId: string;
  campaignId: string;
  at: string;
  country?: string;
  deviceType: QrDeviceType;
  language?: string;
  isUnique: boolean;
}

export interface QrAnalytics {
  totalScans: number;
  uniqueScans: number;
  lastScanAt?: string;
  byCountry: { country: string; count: number }[];
  byDevice: { device: QrDeviceType; count: number }[];
  byLanguage: { language: string; count: number }[];
  trend: { day: string; scans: number }[];
}

export interface PublicCampaign {
  id: string;
  slug?: string;
  title: string;
  description?: string;
  languages: string[];
  images: { url: string; alt?: string }[];
  videos: { url: string; poster?: string }[];
  resources: { name: string; url: string; sizeBytes?: number }[];
  organizationName?: string;
  updatedAt: string;
  /** Populated when the requested language has AI-generated TTS audio. */
  audioUrl?: string;
}
