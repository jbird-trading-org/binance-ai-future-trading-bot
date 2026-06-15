import fs from "node:fs";
import path from "node:path";
import { loadEnv, getProjectRoot } from "../src/lib/env.js";
import { binanceGet } from "../src/lib/binance.js";
import { getRuntimeConfig } from "../src/lib/runtimeConfig.js";

loadEnv();

interface PositionRow {
  symbol: string;
  positionAmt: string;
  entryPrice: string;
  markPrice: string;
  unRealizedProfit: string;
}

async function main(): Promise<void> {
  const cfg = getRuntimeConfig();
  const positions = await binanceGet<PositionRow[]>("/fapi/v2/positionRisk", "", true);
  const open = (positions ?? []).filter((p) => Number.parseFloat(p.positionAmt) !== 0);
  const balance = await binanceGet<{ totalMarginBalance?: string }>("/fapi/v3/account", "", true);
  const bal = Number.parseFloat(balance?.totalMarginBalance ?? "0");

  const slTpPath = path.join(getProjectRoot(), ".positions_sl_tp.json");
  let slTp: Record<string, { sl?: number; tp1?: number }> = {};
  if (fs.existsSync(slTpPath)) {
    slTp = JSON.parse(fs.readFileSync(slTpPath, "utf8")) as typeof slTp;
  }

  console.log("📊 POSISI TERKINI\n");
  console.log(`💰 Balance: $${bal.toFixed(2)}`);
  console.log(`📊 Positions: ${open.length}/${cfg.maxPositions}`);

  if (!open.length) {
    console.log("\nNo open positions.");
    return;
  }

  console.log("\n" + "─".repeat(40));
  let totalPnl = 0;
  for (const p of open) {
    const amt = Number.parseFloat(p.positionAmt);
    const entry = Number.parseFloat(p.entryPrice);
    const mark = Number.parseFloat(p.markPrice);
    const pnl = Number.parseFloat(p.unRealizedProfit);
    totalPnl += pnl;
    const direction = amt > 0 ? "LONG" : "SHORT";
    const saved = slTp[p.symbol];
    console.log(
      `\n${p.symbol} ${direction}\n` +
        `  Entry: ${entry.toFixed(6)} | Mark: ${mark.toFixed(6)}\n` +
        `  Size: ${Math.abs(amt)} | uPnL: ${pnl >= 0 ? "+" : ""}${pnl.toFixed(2)} USDT` +
        (saved?.sl ? `\n  SL: ${saved.sl.toFixed(6)} | TP: ${saved.tp1?.toFixed(6) ?? "n/a"}` : ""),
    );
  }
  console.log(`\n📈 Total Unrealized: ${totalPnl >= 0 ? "+" : ""}${totalPnl.toFixed(2)} USDT`);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
