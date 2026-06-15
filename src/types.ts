export type Direction = "LONG" | "SHORT";
export type BtcRegime = "BULLISH" | "BEARISH" | "NEUTRAL";

export interface Candle {
  open: number;
  high: number;
  low: number;
  close: number;
  volume?: number;
  time?: number;
}

export interface SignalAnalysis {
  symbol: string;
  direction: Direction;
  runner_score: number;
  price_change: number;
  change_1h?: number;
  rsi?: number;
  vol_ratio?: number;
  current?: number;
  btc_regime?: BtcRegime;
  macd_histogram?: number;
  ema_21?: number;
  ema_50?: number;
  atr_pct?: number;
  oi_change?: number;
  funding_rate?: number;
  trend?: string;
  structure?: string;
  breakout?: boolean;
  weekly_change?: number;
  sl?: number;
  tp1?: number;
  sl_method?: string;
  [key: string]: unknown;
}

export interface PositionSnapshot {
  symbol: string;
  direction: Direction;
  amount: number;
  entry: number;
  mark: number;
  unrealizedPnl: number;
}

export interface DashboardStats {
  closed_pnl: number;
  total_trades: number;
  wins: number;
  losses: number;
  winrate: number;
  avg_win: number;
  avg_loss: number;
  expectancy?: number;
}

export interface DashboardPayload {
  bal: number;
  margin: number;
  pnl: number;
  pos: Array<{
    s: string;
    d: Direction;
    a: number;
    u: number;
    m: number;
    e: number;
  }>;
  algos: Array<Record<string, unknown>>;
  stats: DashboardStats | null;
  closed_trades: Array<{
    symbol: string;
    side: string;
    pnl: number;
    time: number;
  }>;
}

export interface LlmDecision {
  decision: "YES" | "NO";
  confidence: number;
  reason: string;
}
