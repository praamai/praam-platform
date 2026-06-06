/** Runtime config types returned by platform-config API. */

export type AppConfig = {
  version: number;
  app: string;
  schema: string;
  runtime: string;
  platform_wired: boolean;
  dependencies: string[];
  ports: Record<string, number>;
  port_env: Record<string, number>;
  postgres?: {
    host: string;
    host_port: number;
    database: string;
    schema: string;
    user: string;
    url: string;
  };
  redis?: {
    host_port: number;
    url: string;
    roles: Record<string, { db: number; url: string }>;
    celery_broker_url?: string;
    celery_result_backend?: string;
  };
  litellm?: {
    base_url: string;
    master_key: string;
    models: Record<string, string>;
  };
  config_api?: {
    host_port: number;
    base_url: string;
  };
  embed_urls: Record<string, string>;
  env: Record<string, string>;
};

export type LoadedPlatform = {
  config: AppConfig;
  secrets: Record<string, string>;
  applyEnv: (target?: NodeJS.ProcessEnv, override?: boolean) => void;
};

export type PlatformClientOptions = {
  baseUrl?: string;
  token?: string;
  timeoutMs?: number;
};

function envOr(key: string, fallback: string): string {
  return (typeof process !== "undefined" ? process.env[key] : undefined) ?? fallback;
}

async function fetchJson<T>(
  url: string,
  opts: { token?: string; timeoutMs?: number } = {},
): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), opts.timeoutMs ?? 10_000);
  try {
    const headers: Record<string, string> = { Accept: "application/json" };
    if (opts.token) headers.Authorization = `Bearer ${opts.token}`;
    const res = await fetch(url, { headers, signal: controller.signal });
    if (!res.ok) {
      const body = await res.text();
      throw new Error(`Platform API ${url} failed (${res.status}): ${body}`);
    }
    return (await res.json()) as T;
  } finally {
    clearTimeout(timer);
  }
}

export class PlatformClient {
  readonly app: string;
  readonly baseUrl: string;
  readonly token: string;
  readonly timeoutMs: number;

  constructor(app: string, options: PlatformClientOptions = {}) {
    this.app = app;
    this.baseUrl = (options.baseUrl ?? envOr("PRAAM_CONFIG_URL", "http://127.0.0.1:3180")).replace(/\/$/, "");
    this.token = options.token ?? envOr("PRAAM_SERVICE_TOKEN", "praam-platform-dev");
    this.timeoutMs = options.timeoutMs ?? 10_000;
  }

  async getConfig(runtime?: string): Promise<AppConfig> {
    const query = runtime ? `?runtime=${encodeURIComponent(runtime)}` : "";
    return fetchJson<AppConfig>(`${this.baseUrl}/v1/apps/${this.app}/config${query}`, {
      timeoutMs: this.timeoutMs,
    });
  }

  async getSecret(name: string): Promise<string> {
    const payload = await fetchJson<{ name: string; value: string }>(
      `${this.baseUrl}/v1/secrets/${name}`,
      { token: this.token, timeoutMs: this.timeoutMs },
    );
    return payload.value;
  }

  static async load(
    app: string,
    options: PlatformClientOptions & { fetchSecrets?: string[]; applyEnv?: boolean } = {},
  ): Promise<LoadedPlatform> {
    const client = new PlatformClient(app, options);
    const config = await client.getConfig();
    const secrets: Record<string, string> = {};
    for (const name of options.fetchSecrets ?? []) {
      secrets[name] = await client.getSecret(name);
    }
    const loaded: LoadedPlatform = {
      config,
      secrets,
      applyEnv(target = process.env, override = false) {
        for (const [key, value] of Object.entries(config.env)) {
          if (override || target[key] === undefined) target[key] = value;
        }
        for (const [name, value] of Object.entries(secrets)) {
          const key = name.toUpperCase().replace(/-/g, "_");
          if (override || target[key] === undefined) target[key] = value;
        }
      },
    };
    if (options.applyEnv !== false) {
      loaded.applyEnv();
    }
    return loaded;
  }
}

export async function getDatabaseUrl(app: string, options?: PlatformClientOptions): Promise<string> {
  const config = await new PlatformClient(app, options).getConfig();
  if (!config.postgres?.url) throw new Error(`No postgres config for app ${app}`);
  return config.postgres.url;
}

export async function getLitellmUrl(app: string, options?: PlatformClientOptions): Promise<string | undefined> {
  const config = await new PlatformClient(app, options).getConfig();
  return config.litellm?.base_url;
}

export { APP_KEYS, type AppKey } from "./generated/app-keys.js";
export { SDK_VERSION } from "./generated/version.js";
