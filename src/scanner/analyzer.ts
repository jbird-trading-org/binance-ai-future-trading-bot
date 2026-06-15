import { config } from "../config.js";
import { getKlines } from "../lib/binance.js";
import {
  calcEma,
  calcRsi,
  calcMacd,
  calcAtr,
  rangePosition,
  scoreDirection,
  toOhlc,
} from "../lib/indicators.js";
import { filterSignal } from "../lib/signalFilter.js";
import { isTradfi } from "../lib/tradfi.js";
import type { BtcRegime, Direction, SignalAnalysis } from "../types.js";

export interface TickerStat {
  priceChangePercent?: string | number;
  lastPrice?: string | number;
  quoteVolume?: string | number;
}

function reject(reason: string): null {
  process.stdout.write(`(${reason}) `);
  return null;
}

export async function analyzeSymbol(
  symbol: string,
  stats: Record<string, TickerStat>,
  btcRegime: BtcRegime = "NEUTRAL",
): Promise<SignalAnalysis | null> {
  const stat = stats[symbol] ?? {};
  const priceChange = Number.parseFloat(String(stat.priceChangePercent ?? 0));
  const tradfi = isTradfi(symbol);

  const candles = await getKlines(symbol, "1h", 50);
  if (candles.length < 20) return reject("no_candles");

  const closes = candles.map((c) => c[4]);
  const volumes = candles.map((c) => c[5]);
  const current = closes[closes.length - 1];
  const avgVol = volumes.slice(-25, -1).reduce((a, b) => a + b, 0) / 24;
  const recentVol = Math.max(volumes[volumes.length - 1], volumes[volumes.length - 2] ?? 0);
  const volRatio = avgVol > 0 ? recentVol / avgVol : 1;

  const ema9 = calcEma(closes, 9);
  const ema21 = calcEma(closes, 21);
  const rsi = calcRsi(closes);
  const { histogram } = calcMacd(closes);
  const atr = calcAtr(candles) ?? current * 0.02;
  const atrPct = (atr / current) * 100;
  const ohlc = toOhlc(candles);
  const rangePos = rangePosition(ohlc, current);

  let direction: Direction = priceChange >= 0 ? "LONG" : "SHORT";
  const emaBull = ema9 != null && ema21 != null && ema9 > ema21;
  const emaBear = ema9 != null && ema21 != null && ema9 < ema21;

  if (direction === "LONG" && btcRegime === "BEARISH" && config.btcRegimeCheck) {
    return reject("btc=BEARISH");
  }
  if (direction === "SHORT" && btcRegime === "BULLISH" && config.btcRegimeCheck) {
    return reject("btc=BULLISH");
  }

  const chaseLimit = tradfi ? config.chaseLimitTradfi : config.chaseLimitCrypto;
  if (Math.abs(priceChange) > chaseLimit) {
    return reject(`chase=${priceChange.toFixed(1)}%>${chaseLimit}%`);
  }

  if (volRatio < config.minVolumeRatio && !(btcRegime === "BEARISH" && direction === "SHORT")) {
    return reject(`vol=${volRatio.toFixed(1)}x`);
  }

  const macdFlat = tradfi ? config.macdFlatTradfi : config.macdFlatCrypto;
  if (Math.abs(histogram) < macdFlat && Math.abs(priceChange) > 3) {
    return reject(`hist=${histogram.toFixed(4)} flat`);
  }

  if (direction === "LONG" && rangePos < 40) return reject(`range=${rangePos.toFixed(0)}%`);
  if (direction === "SHORT" && rangePos < 40) return reject(`range_short=${rangePos.toFixed(0)}%`);

  if (direction === "LONG" && emaBear && btcRegime !== "BULLISH") {
    return reject("dir_conflict");
  }
  if (direction === "SHORT" && emaBull && btcRegime !== "BEARISH") {
    return reject("dir_conflict_short");
  }

  const change1h =
    closes.length >= 6
      ? ((closes[closes.length - 1] - closes[closes.length - 6]) / closes[closes.length - 6]) * 100
      : 0;

  let runnerScore = scoreDirection(direction, rsi, histogram, volRatio);
  if (Math.abs(histogram) > macdFlat) runnerScore += 1;
  if (rangePos >= 40 && rangePos <= 70) runnerScore += 1;
  if (Math.abs(priceChange) >= config.minPriceChange) runnerScore += 1;

  const minScore =
    direction === "SHORT" && btcRegime === "BEARISH"
      ? config.minScoreShortBear
      : config.minScoreNormal;

  if (runnerScore < minScore) {
    return reject(`score=${runnerScore}/${minScore}`);
  }

  const slPct = config.useAtrSltp
    ? Math.min(config.slMax, Math.max(config.slMin, atrPct * config.slAtrMultiplier))
    : config.priceSl;
  const tpPct = config.useAtrSltp
    ? Math.min(config.tpMax, Math.max(config.tpMin, atrPct * config.tpAtrMultiplier))
    : config.priceTp;

  const sl =
    direction === "LONG" ? current * (1 - slPct / 100) : current * (1 + slPct / 100);
  const tp1 =
    direction === "LONG" ? current * (1 + tpPct / 100) : current * (1 - tpPct / 100);

  const analysis: SignalAnalysis = {
    symbol,
    direction,
    runner_score: runnerScore,
    price_change: priceChange,
    change_1h: change1h,
    rsi,
    vol_ratio: volRatio,
    current,
    btc_regime: btcRegime,
    macd_histogram: histogram,
    ema_21: ema21 ?? undefined,
    atr_pct: atrPct,
    sl,
    tp1,
    sl_method: config.useAtrSltp ? "ATR" : "PRICE",
  };

  const { passed, reason } = filterSignal(symbol, analysis);
  if (!passed) return reject(reason.replace(/^REJECT: /, ""));

  return analysis;
}
