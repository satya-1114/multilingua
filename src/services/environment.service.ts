/**
 * Environment configuration. Reads Vite env with typed defaults, exposes
 * feature toggles and network status.
 */

type Env = "development" | "testing" | "staging" | "production";

interface EnvironmentConfig {
  ENVIRONMENT: Env;
  API_BASE_URL: string;
  API_VERSION: string;
  MOCK_MODE: boolean;
  AI_MOCKS: boolean;
  DEBUG: boolean;
  LOG_LEVEL: "silent" | "error" | "warn" | "info" | "debug";
  DEFAULT_WORKSPACE?: string;
}

function readEnv<T>(key: string, fallback: T): T {
  if (typeof import.meta === "undefined" || !import.meta.env) return fallback;
  const raw = (import.meta.env as Record<string, string | undefined>)[key];
  if (raw === undefined) return fallback;
  if (typeof fallback === "boolean") return (raw === "true") as unknown as T;
  if (typeof fallback === "number") return Number(raw) as unknown as T;
  return raw as unknown as T;
}

class EnvironmentService {
  private config: EnvironmentConfig;
  private online = typeof navigator === "undefined" ? true : navigator.onLine;

  constructor() {
    const env = readEnv<Env>("VITE_ENVIRONMENT", "development");
    // Mock mode defaults to true only outside production; production
    // never silently falls back to fixtures.
    const mockDefault = env !== "production";
    this.config = {
      ENVIRONMENT: env,
      API_BASE_URL: readEnv<string>("VITE_API_BASE_URL", "/api"),
      API_VERSION: readEnv<string>("VITE_API_VERSION", "v1"),
      MOCK_MODE: readEnv<boolean>("VITE_MOCK_MODE", mockDefault),
      // AI mocks are DISABLED by default. A failed real AI request must
      // never return synthesised content — the caller sees the real error.
      // Set VITE_ENABLE_AI_MOCKS=true to opt into fixture-backed AI flows
      // for demos / offline development.
      AI_MOCKS: readEnv<boolean>("VITE_ENABLE_AI_MOCKS", false),
      DEBUG: readEnv<boolean>("VITE_DEBUG", false),
      LOG_LEVEL: readEnv<EnvironmentConfig["LOG_LEVEL"]>("VITE_LOG_LEVEL", "warn"),
      DEFAULT_WORKSPACE: readEnv<string | undefined>("VITE_DEFAULT_WORKSPACE", undefined),
    };
    if (typeof window !== "undefined") {
      window.addEventListener("online", () => { this.online = true; });
      window.addEventListener("offline", () => { this.online = false; });
    }
  }

  get<K extends keyof EnvironmentConfig>(key: K): EnvironmentConfig[K] { return this.config[key]; }
  all(): EnvironmentConfig { return { ...this.config }; }
  is(env: Env): boolean { return this.config.ENVIRONMENT === env; }
  isProduction(): boolean { return this.is("production"); }
  isMock(): boolean { return this.config.MOCK_MODE; }
  isAiMockEnabled(): boolean { return this.config.AI_MOCKS; }
  isOnline(): boolean { return this.online; }
}

export const environmentService = new EnvironmentService();
