import { config } from "../config.js";
import { loadEnv } from "../lib/env.js";
import { runScannerCycle } from "./index.js";

loadEnv();

async function main(): Promise<void> {
  const intervalMs = config.scanIntervalSec * 1000;
  while (true) {
    try {
      await runScannerCycle();
    } catch (err) {
      console.error("Scanner error:", err);
    }
    console.log(`Sleeping ${config.scanIntervalSec}s...`);
    await new Promise((r) => setTimeout(r, intervalMs));
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
