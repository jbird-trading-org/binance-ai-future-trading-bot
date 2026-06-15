import { describe, expect, it } from "vitest";
import { calcEma, calcRsi, calcMacd, detectEngulfing } from "../src/lib/indicators.js";
import { filterSignal } from "../src/lib/signalFilter.js";
import { isTradfi } from "../src/lib/tradfi.js";
import { CircuitBreaker } from "../src/lib/errorHandling.js";

describe("indicators", () => {
  const prices = Array.from({ length: 30 }, (_, i) => 100 + i * 0.5);

  it("calculates EMA", () => {
    const ema = calcEma(prices, 9);
    expect(ema).not.toBeNull();
    expect(ema!).toBeGreaterThan(100);
  });

  it("calculates RSI", () => {
    expect(calcRsi(prices)).toBeGreaterThan(50);
  });

  it("calculates MACD histogram", () => {
    const macd = calcMacd(prices);
    expect(macd).toHaveProperty("histogram");
  });

  it("detects bullish engulfing", () => {
    const candles: Array<[number, number, number, number]> = [
      [10, 11, 9, 9.5],
      [9.4, 12, 9.2, 11.5],
    ];
    expect(detectEngulfing(candles).type).toBe("bullish");
  });
});

describe("signalFilter", () => {
  it("rejects low volume", () => {
    const result = filterSignal("TESTUSDT", {
      symbol: "TESTUSDT",
      direction: "LONG",
      runner_score: 5,
      price_change: 3,
      vol_ratio: 1,
    });
    expect(result.passed).toBe(false);
  });

  it("passes valid signal", () => {
    const result = filterSignal("TESTUSDT", {
      symbol: "TESTUSDT",
      direction: "LONG",
      runner_score: 5,
      price_change: 3,
      vol_ratio: 2.5,
      rsi: 55,
      change_1h: 0.5,
    });
    expect(result.passed).toBe(true);
  });
});

describe("tradfi", () => {
  it("detects stock perps", () => {
    expect(isTradfi("TSLAUSDT")).toBe(true);
    expect(isTradfi("BTCUSDT")).toBe(false);
  });
});

describe("errorHandling", () => {
  it("opens circuit after failures", async () => {
    const breaker = new CircuitBreaker(2, 60);
    const fail = () => Promise.reject(new Error("fail"));
    await expect(breaker.call(fail)).rejects.toThrow();
    await expect(breaker.call(fail)).rejects.toThrow();
    expect(breaker.state).toBe("open");
  });
});
