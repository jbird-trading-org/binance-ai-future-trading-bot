import { getKlines } from "../lib/binance.js";
import { calcEma } from "../lib/indicators.js";
import type { BtcRegime } from "../types.js";
import { cacheSetJson } from "../redis/cache.js";
import { btcRegimeKey } from "../redis/keys.js";

const TIGHT_ZONE_PCT = 0.0015;

async function regimeOnTimeframe(interval: string, limit: number): Promise<BtcRegime> {
  const candles = await getKlines("BTCUSDT", interval, limit);
  if (candles.length < 21) return "NEUTRAL";
  const closes = candles.map((c) => c[4]);
  const ema9 = calcEma(closes, 9);
  const ema21 = calcEma(closes, 21);
  if (ema9 == null || ema21 == null) return "NEUTRAL";
  const diffPct = Math.abs(ema9 / ema21 - 1);
  if (diffPct < TIGHT_ZONE_PCT) return "NEUTRAL";
  return ema9 > ema21 ? "BULLISH" : "BEARISH";
}

export async function getBtcRegime(): Promise<BtcRegime> {
  const [m15, h1, h4] = await Promise.all([
    regimeOnTimeframe("15m", 50),
    regimeOnTimeframe("1h", 50),
    regimeOnTimeframe("4h", 25),
  ]);
  const results = [m15, h1, h4];
  const bull = results.filter((r) => r === "BULLISH").length;
  const bear = results.filter((r) => r === "BEARISH").length;
  let combined: BtcRegime = "NEUTRAL";
  if (bull >= 2) combined = "BULLISH";
  else if (bear >= 2) combined = "BEARISH";
  console.log(`  📊 BTC TFs: 15m=${m15} 1h=${h1} 4h=${h4} → ${combined}`);
  await cacheSetJson(btcRegimeKey(), { regime: combined, at: Date.now() }, 300);
  return combined;
}
