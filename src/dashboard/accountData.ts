import type { DashboardPayload, DashboardStats } from "../types.js";
import { config } from "../config.js";
import { binanceGet } from "../lib/binance.js";
import { cacheGetJson, cacheSetJson } from "../redis/cache.js";
import { dashboardKey } from "../redis/keys.js";

interface PositionRiskRow {
  symbol: string;
  positionAmt: string;
  entryPrice: string;
  markPrice: string;
  unRealizedProfit: string;
}

interface AccountRow {
  totalMarginBalance?: string;
  totalInitialMargin?: string;
  positions?: Array<{ symbol: string; positionAmt: string; unrealizedProfit?: string }>;
}

async function getIncomeHistory(days = 7): Promise<DashboardStats | null> {
  const now = Date.now();
  const startTime = now - days * 24 * 60 * 60 * 1000;
  const data = await binanceGet<Array<{ incomeType: string; income: string }>>(
    "/fapi/v1/income",
    `startTime=${startTime}&limit=100`,
    true,
  );
  if (!Array.isArray(data)) return null;

  const realized = data.filter((t) => t.incomeType === "REALIZED_PNL");
  const wins = realized.filter((t) => Number.parseFloat(t.income) > 0);
  const losses = realized.filter((t) => Number.parseFloat(t.income) < 0);
  const closedPnl = realized.reduce((s, t) => s + Number.parseFloat(t.income), 0);
  const totalWins = wins.reduce((s, t) => s + Number.parseFloat(t.income), 0);
  const totalLosses = Math.abs(losses.reduce((s, t) => s + Number.parseFloat(t.income), 0));

  return {
    closed_pnl: closedPnl,
    total_trades: realized.length,
    wins: wins.length,
    losses: losses.length,
    winrate: realized.length ? (wins.length / realized.length) * 100 : 0,
    avg_win: wins.length ? totalWins / wins.length : 0,
    avg_loss: losses.length ? totalLosses / losses.length : 0,
    expectancy:
      realized.length
        ? (totalWins + -totalLosses) / realized.length
        : 0,
  };
}

export async function fetchAccountData(force = false): Promise<DashboardPayload & { cached?: boolean }> {
  if (!force) {
    const cached = await cacheGetJson<DashboardPayload & { cached?: boolean }>(dashboardKey());
    if (cached) return { ...cached, cached: true };
  }

  const positionRisk = await binanceGet<PositionRiskRow[]>("/fapi/v2/positionRisk", "", true);
  const account = await binanceGet<AccountRow>("/fapi/v3/account", "", true);

  if (!account?.totalMarginBalance) {
    return { bal: 0, margin: 0, pnl: 0, pos: [], algos: [], stats: null, closed_trades: [] };
  }

  const balance = Number.parseFloat(account.totalMarginBalance);
  const marginUsed = Number.parseFloat(account.totalInitialMargin ?? "0");
  const marginPct = balance ? (marginUsed / balance) * 100 : 0;

  const posMap: Record<string, { e: number; m: number; u: number }> = {};
  if (Array.isArray(positionRisk)) {
    for (const p of positionRisk) {
      if (Number.parseFloat(p.positionAmt) !== 0) {
        posMap[p.symbol] = {
          e: Number.parseFloat(p.entryPrice) || 0,
          m: Number.parseFloat(p.markPrice) || 0,
          u: Number.parseFloat(p.unRealizedProfit) || 0,
        };
      }
    }
  }

  const positions = (account.positions ?? [])
    .filter((p) => Number.parseFloat(p.positionAmt) !== 0)
    .map((p) => {
      const extra = posMap[p.symbol] ?? { e: 0, m: 0, u: 0 };
      return {
        s: p.symbol,
        d: Number.parseFloat(p.positionAmt) > 0 ? "LONG" as const : "SHORT" as const,
        a: Math.abs(Number.parseFloat(p.positionAmt)),
        u: extra.u || Number.parseFloat(p.unrealizedProfit ?? "0"),
        m: extra.m,
        e: extra.e,
      };
    });

  const stats = await getIncomeHistory(7);
  const pnl = positions.reduce((s, p) => s + p.u, 0);

  const payload: DashboardPayload = {
    bal: balance,
    margin: marginPct,
    pnl,
    pos: positions,
    algos: [],
    stats,
    closed_trades: [],
  };

  await cacheSetJson(dashboardKey(), payload, config.dashboardCacheTtlSec);
  return { ...payload, cached: false };
}
