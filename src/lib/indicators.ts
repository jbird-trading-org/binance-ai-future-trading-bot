import type { Candle, Direction } from "../types.js";

export type OhlcTuple = [number, number, number, number];

export function calcEma(prices: number[], period: number): number | null {
  if (prices.length < period) return null;
  const mul = 2 / (period + 1);
  let ema = prices.slice(0, period).reduce((a, b) => a + b, 0) / period;
  for (const p of prices.slice(period)) {
    ema = (p - ema) * mul + ema;
  }
  return ema;
}

export function calcRsi(prices: number[], period = 14): number {
  if (prices.length < period + 1) return 50;
  const deltas = prices.slice(1).map((p, i) => p - prices[i]);
  const gains = deltas.slice(-period).map((d) => (d > 0 ? d : 0));
  const losses = deltas.slice(-period).map((d) => (d < 0 ? -d : 0));
  const avgGain = gains.reduce((a, b) => a + b, 0) / period;
  const avgLoss = losses.reduce((a, b) => a + b, 0) / period;
  if (avgLoss === 0) return 100;
  const rs = avgGain / avgLoss;
  return 100 - 100 / (1 + rs);
}

export function calcAtr(candles: number[][], period = 14): number | null {
  if (candles.length < period + 1) return null;
  const trs: number[] = [];
  for (let i = 1; i <= Math.min(period, candles.length - 1); i++) {
    const idx = candles.length - i;
    const high = candles[idx][2];
    const low = candles[idx][3];
    const prevClose = candles[idx - 1][4];
    trs.push(Math.max(high - low, Math.abs(high - prevClose), Math.abs(low - prevClose)));
  }
  return trs.length ? trs.reduce((a, b) => a + b, 0) / trs.length : null;
}

export function calcMacd(
  prices: number[],
  fast = 12,
  slow = 26,
  signal = 9,
): { macd: number; signal: number; histogram: number } {
  if (prices.length < slow + signal) {
    return { macd: 0, signal: 0, histogram: 0 };
  }

  const emaSeries = (period: number): number[] => {
    const out: number[] = [];
    let ema = prices.slice(0, period).reduce((a, b) => a + b, 0) / period;
    out.push(ema);
    const mul = 2 / (period + 1);
    for (let i = period; i < prices.length; i++) {
      ema = (prices[i] - ema) * mul + ema;
      out.push(ema);
    }
    return out;
  };

  const fastEma = emaSeries(fast);
  const slowEma = emaSeries(slow);
  const offset = slow - fast;
  const macdLine: number[] = [];
  for (let i = 0; i < slowEma.length; i++) {
    macdLine.push(fastEma[i + offset] - slowEma[i]);
  }
  const signalLine = emaSeries(signal);
  const sigOffset = macdLine.length - signalLine.length;
  const macd = macdLine[macdLine.length - 1] ?? 0;
  const sig = signalLine[signalLine.length - 1] ?? 0;
  return { macd, signal: sig, histogram: macd - sig };
}

export function toOhlc(candles: number[][]): OhlcTuple[] {
  return candles.map((c) => [c[1], c[2], c[3], c[4]]);
}

export function detectEngulfing(candles: OhlcTuple[]): { type: "bullish" | "bearish" | "none"; strength: number } {
  if (candles.length < 2) return { type: "none", strength: 0 };
  const [prevOpen, , , prevClose] = candles[candles.length - 2];
  const [currOpen, , , currClose] = candles[candles.length - 1];
  const prevBody = Math.abs(prevClose - prevOpen);
  const currBody = Math.abs(currClose - currOpen);

  if (prevClose < prevOpen && currClose > currOpen && currOpen < prevClose && currClose > prevOpen) {
    const avgBody = (prevBody + currBody) / 2;
    return { type: "bullish", strength: avgBody > 0 ? Math.min(1, currBody / (avgBody * 1.5)) : 0.5 };
  }
  if (prevClose > prevOpen && currClose < currOpen && currOpen > prevClose && currClose < prevOpen) {
    const avgBody = (prevBody + currBody) / 2;
    return { type: "bearish", strength: avgBody > 0 ? Math.min(1, currBody / (avgBody * 1.5)) : 0.5 };
  }
  return { type: "none", strength: 0 };
}

export function calcFibRetracement(candles: OhlcTuple[]): Record<number, number> {
  if (candles.length < 20) return {};
  const recent = candles.slice(-20);
  const highs = recent.map((c) => c[1]);
  const lows = recent.map((c) => c[2]);
  const swingHigh = Math.max(...highs);
  const swingLow = Math.min(...lows);
  const diff = swingHigh - swingLow;
  if (diff === 0) return {};
  return {
    0.382: swingHigh - diff * 0.382,
    0.5: swingHigh - diff * 0.5,
    0.618: swingHigh - diff * 0.618,
    0.786: swingHigh - diff * 0.786,
    1.0: swingLow,
  };
}

export function rangePosition(candles: OhlcTuple[], current: number): number {
  if (candles.length < 20) return 50;
  const recent = candles.slice(-20);
  const high = Math.max(...recent.map((c) => c[1]));
  const low = Math.min(...recent.map((c) => c[2]));
  if (high === low) return 50;
  return ((current - low) / (high - low)) * 100;
}

export function scoreDirection(
  direction: Direction,
  rsi: number,
  histogram: number,
  volRatio: number,
): number {
  let score = 0;
  if (direction === "LONG") {
    if (rsi >= 40 && rsi <= 65) score += 2;
    if (histogram > 0) score += 2;
  } else {
    if (rsi >= 35 && rsi <= 70) score += 2;
    if (histogram < 0) score += 2;
  }
  if (volRatio >= 1.5) score += 2;
  if (volRatio >= 2.5) score += 1;
  return score;
}

export function candleFromKline(k: number[]): Candle {
  return {
    time: k[0],
    open: k[1],
    high: k[2],
    low: k[3],
    close: k[4],
    volume: k[5],
  };
}
