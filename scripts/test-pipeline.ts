import { config } from "../src/config.js";
import { loadEnv } from "../src/lib/env.js";
import { calcEma, calcRsi, calcMacd } from "../src/lib/indicators.js";
import { filterSignal } from "../src/lib/signalFilter.js";
import { refreshCoins } from "../src/lib/dynamicCoins.js";
import { getRuntimeConfig } from "../src/lib/runtimeConfig.js";
import { cacheGet, cacheGetJson, cacheSet, clearMemoryCache } from "../src/redis/cache.js";
import { resetRedisState } from "../src/redis/client.js";
import { getBtcRegime } from "../src/scanner/btcRegime.js";
import { analyzeSymbol } from "../src/scanner/analyzer.js";
import { runScannerCycle } from "../src/scanner/index.js";
import { runMonitorCycle } from "../src/monitor/index.js";
import { fetchAccountData } from "../src/dashboard/accountData.js";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

loadEnv();
clearMemoryCache();
resetRedisState();

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");

async function step(name: string, fn: () => Promise<void>): Promise<void> {
  console.log(`\n=== Pipeline: ${name} ===`);
  await fn();
  console.log(`✓ ${name} OK`);
}

async function main(): Promise<void> {
  console.log("=== Neko TypeScript Pipeline Test ===\n");

  await step("build-artifacts", async () => {
    const required = [
      "dist/src/index.js",
      "dist/scripts/test-pipeline.js",
      "dist/src/scanner/index.js",
      "dist/src/monitor/index.js",
      "dist/src/dashboard/server.js",
    ];
    for (const rel of required) {
      const full = path.join(ROOT, rel);
      if (!fs.existsSync(full)) {
        throw new Error(`Missing build output: ${rel} — run npm run build first`);
      }
    }
  });

  await step("config", async () => {
    if (config.leverage !== 10) throw new Error("config.leverage mismatch");
    if (!config.dynamicCoinsEnabled) throw new Error("dynamic coins disabled");
    const runtime = getRuntimeConfig();
    if (runtime.maxPositions < 1) throw new Error("invalid maxPositions");
    console.log(`  maxPositions=${runtime.maxPositions} sleepMode=${runtime.sleepMode}`);
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

  await step("dynamic-coins", async () => {
    const coins = await refreshCoins(true);
    if (coins.size < 50) {
      throw new Error(`expected >= 50 dynamic coins, got ${coins.size}`);
    }
    const btc = await refreshCoins();
    if (!btc.has("BTCUSDT")) throw new Error("BTCUSDT missing from dynamic universe");
    console.log(`  dynamic universe: ${coins.size} symbols`);
  });

  await step("btc-regime", async () => {
    const regime = await getBtcRegime();
    if (!["BULLISH", "BEARISH", "NEUTRAL"].includes(regime)) {
      throw new Error(`invalid regime: ${regime}`);
    }
    const cached = await cacheGetJson<{ regime: string }>("regime:btc");
    if (!cached?.regime) throw new Error("BTC regime not cached");
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
    const status = await cacheGetJson<{ phase?: string; scanned?: number }>("pipeline:scanner:status");
    if (status?.phase !== "complete") {
      throw new Error(`scanner status not complete: ${JSON.stringify(status)}`);
    }
    if ((status.scanned ?? 0) < 1) throw new Error("scanner scanned 0 symbols");
  });

  await step("monitor-cycle", async () => {
    await runMonitorCycle();
    const status = await cacheGetJson<{ positions?: number }>("pipeline:monitor:status");
    if (status?.positions == null) {
      throw new Error(`monitor status missing: ${JSON.stringify(status)}`);
    }
  });

  await step("dashboard-api", async () => {
    const data = await fetchAccountData(true);
    if (typeof data.bal !== "number") throw new Error("dashboard bal missing");
    if (!Array.isArray(data.pos)) throw new Error("dashboard pos not array");
    console.log(`  dashboard payload: bal=${data.bal} positions=${data.pos.length}`);
  });

  console.log("\n=== Pipeline OK ===");
}

main().catch((err) => {
  console.error("\nPipeline FAILED:", err);
  process.exit(1);
});
