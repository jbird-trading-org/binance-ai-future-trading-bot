import { config } from "../config.js";
import { binanceGet } from "./binance.js";
import { cacheGetJson, cacheSetJson } from "../redis/cache.js";

const REFRESH_INTERVAL_SEC = 3600;
const BYPASS_VOLUME_FILTER = new Set([
  "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT",
  "ADAUSDT", "AVAXUSDT", "DOTUSDT", "LINKUSDT", "LTCUSDT", "BCHUSDT",
  "ATOMUSDT", "UNIUSDT", "ETCUSDT", "XLMUSDT", "FILUSDT",
  "APTUSDT", "NEARUSDT", "ARBUSDT", "OPUSDT", "INJUSDT", "SUIUSDT",
  "SEIUSDT", "TIAUSDT", "AAVEUSDT", "MKRUSDT",
  "QQQUSDT", "SPYUSDT", "BTCDOMUSDT", "ALLUSDT",
  "XAUUSDT", "XAGUSDT", "XPTUSDT", "XPDUSDT",
]);

interface CoinCache {
  coins: string[];
  lastRefresh: number;
  tradableInfo: Record<string, { volume: number; price: number; pct_change: number }>;
}

const CACHE_KEY = "dynamic:coins";

let memoryCache: CoinCache = { coins: [], lastRefresh: 0, tradableInfo: {} };

async function loadCache(): Promise<CoinCache> {
  const cached = await cacheGetJson<CoinCache>(CACHE_KEY);
  if (cached?.coins?.length) {
    memoryCache = cached;
    return cached;
  }
  return memoryCache;
}

async function saveCache(data: CoinCache): Promise<void> {
  memoryCache = data;
  await cacheSetJson(CACHE_KEY, data, REFRESH_INTERVAL_SEC);
}

export async function refreshCoins(force = false): Promise<Set<string>> {
  const cache = await loadCache();
  const now = Date.now() / 1000;
  if (!force && cache.coins.length && now - cache.lastRefresh < REFRESH_INTERVAL_SEC) {
    return new Set(cache.coins);
  }

  const [exchangeInfo, tickers] = await Promise.all([
    binanceGet<{ symbols?: Array<{ symbol: string; status: string; contractType?: string }> }>(
      "/fapi/v1/exchangeInfo",
    ),
    binanceGet<Array<{ symbol: string; quoteVolume: string; lastPrice: string; priceChangePercent: string }>>(
      "/fapi/v1/ticker/24hr",
    ),
  ]);

  if (!exchangeInfo?.symbols || !Array.isArray(tickers)) {
    return new Set(cache.coins);
  }

  const tickerMap: Record<string, { volume: number; price: number; pct_change: number }> = {};
  for (const t of tickers) {
    tickerMap[t.symbol] = {
      volume: Number.parseFloat(t.quoteVolume ?? "0"),
      price: Number.parseFloat(t.lastPrice ?? "0"),
      pct_change: Number.parseFloat(t.priceChangePercent ?? "0"),
    };
  }

  const dynamicCoins = new Set<string>();
  const tradableInfo: CoinCache["tradableInfo"] = {};

  for (const sym of exchangeInfo.symbols) {
    if (sym.status !== "TRADING") continue;
    if (!sym.symbol.endsWith("USDT")) continue;
    if (sym.contractType === "CURRENT_QUARTER" || sym.contractType === "NEXT_QUARTER") continue;

    const ticker = tickerMap[sym.symbol];
    if (!ticker) continue;

    if (BYPASS_VOLUME_FILTER.has(sym.symbol) || ticker.volume >= config.dynamicMinVolume) {
      dynamicCoins.add(sym.symbol);
      tradableInfo[sym.symbol] = ticker;
    }
  }

  await saveCache({
    coins: [...dynamicCoins],
    lastRefresh: now,
    tradableInfo,
  });

  return dynamicCoins;
}

export async function getCoins(): Promise<Set<string>> {
  return refreshCoins();
}

export async function getCoinInfo(symbol: string) {
  await refreshCoins();
  return memoryCache.tradableInfo[symbol] ?? {};
}

export async function getMovers(limitGainers = 50, limitLosers = 75): Promise<string[]> {
  await refreshCoins();
  const info = memoryCache.tradableInfo;
  const movers = memoryCache.coins
    .map((s) => ({ symbol: s, pct: info[s]?.pct_change ?? 0 }))
    .filter((m) => Math.abs(m.pct) >= config.minPriceChange)
    .sort((a, b) => b.pct - a.pct);

  const gainers = movers.slice(0, limitGainers).map((m) => m.symbol);
  const losers = movers.slice(-limitLosers).map((m) => m.symbol);
  return [...new Set([...gainers, ...losers])];
}
