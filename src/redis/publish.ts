import type { SignalAnalysis } from "../types.js";
import { cacheSetJson } from "./cache.js";
import { getRedisSettings } from "./settings.js";
import { signalKey } from "./keys.js";

export async function publishSignal(analysis: SignalAnalysis): Promise<void> {
  const ttl = getRedisSettings().signalTtlSec;
  await cacheSetJson(signalKey(analysis.symbol), analysis, ttl);
  await cacheSetJson("signal:latest", analysis, ttl);
}

export async function setPipelineStatus(
  service: "scanner" | "monitor",
  status: Record<string, unknown>,
): Promise<void> {
  const key = service === "scanner" ? "pipeline:scanner:status" : "pipeline:monitor:status";
  await cacheSetJson(key, { ...status, updatedAt: Date.now() }, 300);
}
