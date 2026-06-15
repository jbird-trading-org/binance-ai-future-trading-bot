import { config } from "../src/config.js";
import { loadEnv } from "../src/lib/env.js";
import { calcEma, calcRsi, calcMacd } from "../src/lib/indicators.js";
import { filterSignal } from "../src/lib/signalFilter.js";
import { cacheGet, cacheSet, clearMemoryCache } from "../src/redis/cache.js";
import { resetRedisState } from "../src/redis/client.js";
import { getBtcRegime } from "../src/scanner/btcRegime.js";
import { analyzeSymbol } from "../src/scanner/analyzer.js";
import { runScannerCycle } from "../src/scanner/index.js";
import { runMonitorCycle } from "../src/monitor/index.js";

loadEnv();
clearMemoryCache();
resetRedisState();

async function step(name: string, fn: () => Promise<void>): Promise<void> {
  console.log(`\n=== Pipeline: ${name} ===`);
  await fn();
  console.log(`✓ ${name} OK`);
}

async function main(): Promise<void> {
  console.log("=== Neko TypeScript Pipeline Test ===\n");

  await step("config", async () => {
    if (config.leverage !== 10) throw new Error("config.leverage mismatch");
    if (!config.dynamicCoinsEnabled) throw new Error("dynamic coins disabled");
  });

  await step("indicators", async () => {
    const prices = Array.from({ length: 40 }, (_, i) => 100 + i * 0.3);
    if (calcEma(prices, 9) == null) throw new Error("EMA failed");
    if (calcRsi(prices) <= 0) throw new Error("RSI failed");
    if (!("histogram" in calcMacd(prices))) throw new Error("MACD failed");
  });

  await step("signal-filter", async () => {
    const r = filterSignal("TESTUSDT", {
      symbol: "TESTUSDT",
      direction: "LONG",
      runner_score: 8,
      price_change: 4,
      vol_ratio: 2.5,
      rsi: 55,
      change_1h: 0.5,
    });
    if (!r.passed) throw new Error(`filter rejected: ${r.reason}`);
  });

  await step("redis-fallback", async () => {
    await cacheSet("pipeline:test", "ok", 30);
    const val = await cacheGet("pipeline:test");
    if (val !== "ok") throw new Error("cache fallback failed");
  });

  await step("btc-regime-mock", async () => {
    // Uses public Binance klines — no API keys required
    const regime = await getBtcRegime();
    if (!["BULLISH", "BEARISH", "NEUTRAL"].includes(regime)) {
      throw new Error(`invalid regime: ${regime}`);
    }
    console.log(`  BTC regime: ${regime}`);
  });

  await step("analyzer-public", async () => {
    const stats = {
      BTCUSDT: { priceChangePercent: 1.5, lastPrice: 65000, quoteVolume: 1e9 },
    };
    const result = await analyzeSymbol("BTCUSDT", stats, "NEUTRAL");
    console.log(`  BTCUSDT analysis: ${result ? `signal ${result.direction}` : "no signal"}`);
  });

  await step("scanner-cycle", async () => {
    await runScannerCycle({ maxSymbols: 5 });
  });

  await step("monitor-cycle", async () => {
    await runMonitorCycle();
  });

  console.log("\n=== Pipeline OK ===");
}

main().catch((err) => {
  console.error("\nPipeline FAILED:", err);
  process.exit(1);
});
