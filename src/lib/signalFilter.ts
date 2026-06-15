import type { SignalAnalysis } from "../types.js";

const WHALE_TOKENS = new Set([
  "SHIB", "DOGE", "PEPE", "WIF", "FLOKI", "BONK", "SATS", "RATS", "MOTHER", "AI", "NEIRO",
]);

export function filterSignal(
  symbol: string,
  analysis: SignalAnalysis,
): { passed: boolean; reason: string } {
  const symbolClean = symbol.replace("USDT", "").replace("BTC", "");
  if (WHALE_TOKENS.has(symbolClean)) {
    return { passed: false, reason: `REJECT: ${symbol} is whale-manipulated token` };
  }

  const volRatio = Number(analysis.vol_ratio ?? 0);
  if (volRatio < 2) {
    return { passed: false, reason: `REJECT: Volume too low (${volRatio}x)` };
  }

  const priceChange = Math.abs(Number(analysis.price_change ?? 0));
  if (priceChange < 2) {
    return { passed: false, reason: `REJECT: Price change too small (${priceChange}%)` };
  }

  const rsi = Number(analysis.rsi ?? 50);
  const score = Number(analysis.runner_score ?? 0);
  if ((rsi < 20 || rsi > 80) && score < 4) {
    return { passed: false, reason: `REJECT: RSI extreme without confirmation (${rsi})` };
  }

  if (score < 3) {
    return { passed: false, reason: `REJECT: Score too low (${score})` };
  }

  const change1h = Number(analysis.change_1h ?? 0);
  if (change1h * priceChange < 0 && Math.abs(change1h) > Math.abs(priceChange) * 0.3) {
    return { passed: false, reason: `REJECT: 1h reversal (${change1h}%) vs 4h (${priceChange}%)` };
  }

  return { passed: true, reason: "PASSED" };
}

export function getFilterStats() {
  return {
    whale_tokens: WHALE_TOKENS.size,
    min_volume_ratio: 2.0,
    min_price_change: 2.0,
    min_score: 3,
    cooldown_minutes: 30,
  };
}
