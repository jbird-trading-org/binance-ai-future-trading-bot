export interface RedisSettings {
  enabled: boolean;
  url?: string;
  host: string;
  port: number;
  username?: string;
  password?: string;
  db: number;
  keyPrefix: string;
  signalTtlSec: number;
  dashboardTtlSec: number;
  publishChannel: string;
}

let settings: RedisSettings = defaultSettings();

function defaultSettings(): RedisSettings {
  return {
    enabled: false,
    host: "127.0.0.1",
    port: 6379,
    db: 0,
    keyPrefix: "neko",
    signalTtlSec: 3600,
    dashboardTtlSec: 25,
    publishChannel: "neko:signals",
  };
}

function parseIntOrDefault(value: string | undefined, fallback: number): number {
  const parsed = Number.parseInt(value ?? "", 10);
  return Number.isNaN(parsed) ? fallback : parsed;
}

export function getRedisSettings(): RedisSettings {
  return settings;
}

export function isRedisEnabled(): boolean {
  if (process.env.REDIS_ENABLED === "false") return false;
  if (process.env.REDIS_ENABLED === "true") return true;
  if (process.env.REDIS_URL?.trim() || process.env.REDIS_HOST?.trim()) return true;
  return settings.enabled;
}

export function resolveRedisConnection(): Pick<
  RedisSettings,
  "url" | "host" | "port" | "username" | "password" | "db"
> {
  const s = getRedisSettings();
  return {
    url: process.env.REDIS_URL?.trim() || s.url,
    host: process.env.REDIS_HOST?.trim() || s.host,
    port: parseIntOrDefault(process.env.REDIS_PORT, s.port),
    username: process.env.REDIS_USERNAME?.trim() || s.username,
    password: process.env.REDIS_PASSWORD?.trim() || s.password,
    db: parseIntOrDefault(process.env.REDIS_DB, s.db),
  };
}

export function resolveKeyPrefix(): string {
  return process.env.REDIS_KEY_PREFIX?.trim() || getRedisSettings().keyPrefix;
}
