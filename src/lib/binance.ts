import crypto from "node:crypto";
import { config } from "../config.js";
import { envOr, loadEnv } from "./env.js";

loadEnv();

const API_KEY = () => envOr("BINANCE_API_KEY");
const SECRET = () => envOr("BINANCE_SECRET");

export function getSignature(params: string): string {
  return crypto.createHmac("sha256", SECRET()).update(params).digest("hex");
}

export async function binanceGet<T = unknown>(
  endpoint: string,
  params = "",
  signed = false,
): Promise<T | null> {
  const base = config.binanceBaseUrl;
  let query = params;
  if (signed) {
    const ts = Date.now();
    query = params ? `${params}&timestamp=${ts}` : `timestamp=${ts}`;
    query = `${query}&signature=${getSignature(query)}`;
  }
  const url = query ? `${base}${endpoint}?${query}` : `${base}${endpoint}`;
  try {
    const headers: Record<string, string> = {};
    if (signed) headers["X-MBX-APIKEY"] = API_KEY();
    const res = await fetch(url, { headers, signal: AbortSignal.timeout(15_000) });
    if (!res.ok) return null;
    return (await res.json()) as T;
  } catch {
    return null;
  }
}

export async function binancePost<T = unknown>(
  endpoint: string,
  params: Record<string, string | number>,
): Promise<T | null> {
  const ts = Date.now();
  const entries = Object.entries({ ...params, timestamp: String(ts) }).map(
    ([k, v]) => [k, String(v)] as [string, string],
  );
  const body = new URLSearchParams(entries);
  const sig = getSignature(body.toString());
  body.append("signature", sig);
  try {
    const res = await fetch(`${config.binanceBaseUrl}${endpoint}`, {
      method: "POST",
      headers: {
        "X-MBX-APIKEY": API_KEY(),
        "Content-Type": "application/x-www-form-urlencoded",
      },
      body: body.toString(),
      signal: AbortSignal.timeout(15_000),
    });
    if (!res.ok) return null;
    return (await res.json()) as T;
  } catch {
    return null;
  }
}

export async function getKlines(
  symbol: string,
  interval = "1h",
  limit = 100,
): Promise<number[][]> {
  const data = await binanceGet<Array<Array<string | number>>>(
    "/fapi/v1/klines",
    `symbol=${symbol}&interval=${interval}&limit=${limit}`,
  );
  if (!Array.isArray(data)) return [];
  return data.map((k) => [
    Number(k[0]),
    Number(k[1]),
    Number(k[2]),
    Number(k[3]),
    Number(k[4]),
    Number(k[5]),
  ]);
}

export async function get24hTickers(): Promise<Record<string, { volume: number; price: number; pct_change: number }>> {
  const data = await binanceGet<Array<Record<string, string>>>("/fapi/v1/ticker/24hr");
  if (!Array.isArray(data)) return {};
  const out: Record<string, { volume: number; price: number; pct_change: number }> = {};
  for (const t of data) {
    out[t.symbol] = {
      volume: Number.parseFloat(t.quoteVolume ?? "0"),
      price: Number.parseFloat(t.lastPrice ?? "0"),
      pct_change: Number.parseFloat(t.priceChangePercent ?? "0"),
    };
  }
  return out;
}

export async function getMarkPrice(symbol: string): Promise<number> {
  const data = await binanceGet<{ price?: string }>("/fapi/v1/ticker/price", `symbol=${symbol}`);
  return Number.parseFloat(data?.price ?? "0");
}

export async function getBalance(): Promise<number> {
  const data = await binanceGet<{ totalMarginBalance?: string }>("/fapi/v3/account", "", true);
  return Number.parseFloat(data?.totalMarginBalance ?? "0");
}
