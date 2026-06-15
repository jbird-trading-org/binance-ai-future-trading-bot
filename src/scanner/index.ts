import { config } from "../config.js";
import { getRuntimeConfig } from "../lib/runtimeConfig.js";
import { get24hTickers, getBalance } from "../lib/binance.js";
import { getMovers } from "../lib/dynamicCoins.js";
import { getBtcRegime } from "./btcRegime.js";
import { analyzeSymbol } from "./analyzer.js";
import { setPipelineStatus } from "../redis/publish.js";

export async function runScannerCycle(options?: { maxSymbols?: number }): Promise<void> {
  const runtime = getRuntimeConfig();
  console.log("🔍 Neko Scanner (TypeScript) starting cycle...");
  if (runtime.sleepMode) console.log("  🌙 Sleep mode active");
  await setPipelineStatus("scanner", { phase: "start", at: Date.now() });

  const balance = await getBalance();
  const btcRegime = config.btcRegimeCheck ? await getBtcRegime() : "NEUTRAL";
  const tickers = await get24hTickers();
  const stats: Record<string, { priceChangePercent: number; lastPrice: number; quoteVolume: number }> = {};
  for (const [sym, t] of Object.entries(tickers)) {
    stats[sym] = {
      priceChangePercent: t.pct_change,
      lastPrice: t.price,
      quoteVolume: t.volume,
    };
  }

  const scanSymbols = config.dynamicCoinsEnabled
    ? await getMovers(50, 75)
    : [...config.safeCoins];

  const blacklist = new Set<string>(config.blacklistedSymbols);
  const filtered = scanSymbols.filter((s) => !blacklist.has(s));
  const limit = options?.maxSymbols ?? 120;

  console.log(`  Balance: $${balance.toFixed(2)} | BTC: ${btcRegime} | Scanning ${Math.min(filtered.length, limit)} symbols`);

  let signals = 0;
  for (const symbol of filtered.slice(0, limit)) {
    const change = stats[symbol]?.priceChangePercent ?? 0;
    process.stdout.write(`  Checking ${symbol} (${change.toFixed(1)}%)... `);
    try {
      const analysis = await analyzeSymbol(symbol, stats, btcRegime);
      if (analysis) {
        signals += 1;
        console.log(`✅ SIGNAL! ${analysis.direction} score=${analysis.runner_score}`);
      } else {
        console.log("no signal");
      }
    } catch (err) {
      console.log(`error: ${err instanceof Error ? err.message : String(err)}`);
    }
  }

  console.log(`✅ Scan complete — ${signals} signal(s) found`);
  await setPipelineStatus("scanner", {
    phase: "complete",
    signals,
    balance,
    btcRegime,
    scanned: Math.min(filtered.length, limit),
    at: Date.now(),
  });
}
