import { resolveKeyPrefix } from "./settings.js";

export function redisKey(key: string): string {
  return `${resolveKeyPrefix()}:${key}`;
}

export function signalKey(symbol: string): string {
  return `signal:${symbol}:latest`;
}

export function dashboardKey(): string {
  return "dashboard:account";
}

export function btcRegimeKey(): string {
  return "regime:btc";
}

export function positionsKey(): string {
  return "state:positions";
}

export function scannerStatusKey(): string {
  return "pipeline:scanner:status";
}

export function monitorStatusKey(): string {
  return "pipeline:monitor:status";
}
