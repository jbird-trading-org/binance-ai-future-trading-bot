import { loadEnv, envOr } from "./env.js";
import { config as baseConfig } from "../config.js";

loadEnv();

/** Runtime config — honors SLEEP_MODE env override. */
export function getRuntimeConfig() {
  const sleepMode =
    envOr("SLEEP_MODE").toLowerCase() === "true" || baseConfig.sleepMode;

  return {
    ...baseConfig,
    sleepMode,
    maxPositions: sleepMode ? baseConfig.maxPositionsSleep : baseConfig.maxPositions,
    entryPercent: sleepMode ? baseConfig.entryPercentSleep : baseConfig.entryPercent,
    minScore: sleepMode ? baseConfig.minScoreSleep : baseConfig.minScoreNormal,
  };
}

export type RuntimeConfig = ReturnType<typeof getRuntimeConfig>;
