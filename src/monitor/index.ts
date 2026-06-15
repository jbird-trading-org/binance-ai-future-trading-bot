import fs from "node:fs";
import path from "node:path";
import { config } from "../config.js";
import { getProjectRoot } from "../lib/env.js";
import { getMarkPrice } from "../lib/binance.js";
import { setPipelineStatus } from "../redis/publish.js";

const ROOT = getProjectRoot();
const POSITIONS_FILE = path.join(ROOT, ".positions_sl_tp.json");
const CHECK_INTERVAL = 15;

interface PositionRow {
  symbol: string;
  positionAmt: string;
  entryPrice: string;
  markPrice: string;
}

interface PosSlTp {
  entry: number;
  sl: number;
  tp1: number;
  side: string;
  peak_profit?: number;
  trailing_tp_active?: boolean;
  original_amt?: number;
}

function loadPositionsSlTp(): Record<string, PosSlTp> {
  try {
    if (fs.existsSync(POSITIONS_FILE)) {
      return JSON.parse(fs.readFileSync(POSITIONS_FILE, "utf8")) as Record<string, PosSlTp>;
    }
  } catch {
    /* ignore */
  }
  return {};
}

function savePositionsSlTp(data: Record<string, PosSlTp>): void {
  fs.writeFileSync(POSITIONS_FILE, JSON.stringify(data, null, 2));
}

async function getPositions(): Promise<PositionRow[]> {
  const { binanceGet } = await import("../lib/binance.js");
  const data = await binanceGet<PositionRow[]>("/fapi/v2/positionRisk", "", true);
  if (!Array.isArray(data)) return [];
  return data.filter((p) => Number.parseFloat(p.positionAmt) !== 0);
}

function profitPct(side: string, entry: number, current: number): number {
  return side === "LONG"
    ? ((current - entry) / entry) * 100
    : ((entry - current) / entry) * 100;
}

export async function runMonitorCycle(): Promise<void> {
  const positions = await getPositions();
  const saved = loadPositionsSlTp();
  const openSymbols = new Set(positions.map((p) => p.symbol));

  for (const sym of Object.keys(saved)) {
    if (!openSymbols.has(sym)) delete saved[sym];
  }

  if (!positions.length) {
    console.log(`[${new Date().toISOString()}] No positions`);
    await setPipelineStatus("monitor", { positions: 0, at: Date.now() });
    return;
  }

  for (const p of positions) {
    const symbol = p.symbol;
    const amt = Number.parseFloat(p.positionAmt);
    let entry = Number.parseFloat(p.entryPrice);
    let current = Number.parseFloat(p.markPrice);
    const side = amt > 0 ? "LONG" : "SHORT";

    if (!entry) entry = await getMarkPrice(symbol);
    if (!current) current = await getMarkPrice(symbol);

    let pos = saved[symbol];
    if (!pos?.sl || !pos?.tp1) {
      const slPct = config.priceSl / 100;
      const tpPct = config.priceTp / 100;
      pos = {
        entry,
        sl: side === "LONG" ? entry * (1 - slPct) : entry * (1 + slPct),
        tp1: side === "LONG" ? entry * (1 + tpPct) : entry * (1 - tpPct),
        side: side === "LONG" ? "BUY" : "SELL",
        original_amt: Math.abs(amt),
        peak_profit: 0,
      };
      saved[symbol] = pos;
    }

    const profit = profitPct(side, entry, current);
    pos.peak_profit = Math.max(pos.peak_profit ?? 0, profit);

    if (profit >= config.minProfitBreakeven) {
      const lock = config.trailSlLock / 100;
      const newSl = side === "LONG" ? entry * (1 + lock) : entry * (1 - lock);
      if (side === "LONG" && newSl > pos.sl) pos.sl = newSl;
      if (side === "SHORT" && newSl < pos.sl) pos.sl = newSl;
    }

    console.log(
      `  ${symbol} ${side} entry=${entry.toFixed(4)} mark=${current.toFixed(4)} ` +
        `pnl=${profit.toFixed(2)}% SL=${pos.sl.toFixed(4)} TP=${pos.tp1.toFixed(4)}`,
    );
  }

  savePositionsSlTp(saved);
  await setPipelineStatus("monitor", { positions: positions.length, at: Date.now() });
}

export function getPeakProfitState(): Record<string, PosSlTp> {
  return loadPositionsSlTp();
}
