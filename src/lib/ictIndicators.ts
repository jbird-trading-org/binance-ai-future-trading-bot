export {
  detectEngulfing,
  calcFibRetracement,
  toOhlc,
  type OhlcTuple,
} from "./indicators.js";

export function detectFvg(candles: Array<[number, number, number, number]>): {
  type: "bullish" | "bearish" | "none";
  gap_top: number;
  gap_bottom: number;
} {
  if (candles.length < 3) return { type: "none", gap_top: 0, gap_bottom: 0 };
  const [, , , c1] = candles[candles.length - 3];
  const [, h2, l2] = candles[candles.length - 2];
  const [, h3, l3, c3] = candles[candles.length - 1];

  if (c3 > c1 && l2 > h3) {
    return { type: "bullish", gap_top: l2, gap_bottom: h3 };
  }
  if (c3 < c1 && h2 < l3) {
    return { type: "bearish", gap_top: h3, gap_bottom: l2 };
  }
  return { type: "none", gap_top: 0, gap_bottom: 0 };
}

export function detectOrderBlock(
  candles: Array<[number, number, number, number]>,
  direction: "LONG" | "SHORT",
): { type: "bullish" | "bearish" | "none"; zone_top: number; zone_bottom: number } {
  if (candles.length < 10) return { type: "none", zone_top: 0, zone_bottom: 0 };
  const recent = candles.slice(-5);
  for (let i = 0; i < recent.length - 1; i++) {
    const [o, h, l, c] = recent[i];
    if (direction === "LONG" && c > o && c - o > (h - l) * 0.5) {
      return { type: "bullish", zone_top: h, zone_bottom: l };
    }
    if (direction === "SHORT" && c < o && o - c > (h - l) * 0.5) {
      return { type: "bearish", zone_top: h, zone_bottom: l };
    }
  }
  return { type: "none", zone_top: 0, zone_bottom: 0 };
}
