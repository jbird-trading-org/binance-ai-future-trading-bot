import { loadEnv } from "../lib/env.js";
import { runMonitorCycle, getPeakProfitState } from "./index.js";

loadEnv();

const CHECK_INTERVAL = 15;

async function main(): Promise<void> {
  console.log("🔔 Neko Price Monitor (TypeScript) starting...");
  while (true) {
    try {
      await runMonitorCycle();
    } catch (err) {
      console.error("Monitor error:", err);
    }
    const hasProfit = Object.values(getPeakProfitState()).some((p) => (p.peak_profit ?? 0) > 3);
    await new Promise((r) => setTimeout(r, (hasProfit ? 5 : CHECK_INTERVAL) * 1000));
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
