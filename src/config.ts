/** Trading configuration — ported from config.py */
export const config = {
  leverage: 10,
  maxPositions: 3,
  scanIntervalSec: 60,
} as const;

export type NekoConfig = typeof config;
