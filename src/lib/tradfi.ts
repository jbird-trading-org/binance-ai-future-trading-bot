const TRADFI_STOCKS = new Set([
  "TSLA", "NVDA", "AAPL", "AMZN", "GOOGL", "META", "MSFT", "AMD", "COIN", "MSTR",
  "HOOD", "CRCL", "PLTR", "BABA", "INTC", "TSM", "AVGO", "QCOM", "MU", "BILL",
  "SNDK", "EWY", "EWJ", "USAR", "PAYP", "BB", "BA", "NFLX", "DIS", "PYPL", "SQ",
  "UBER", "ABNB", "SHOP", "RIVN", "SOFI", "ARM", "SMCI", "MRVL", "LRCX", "KLAC",
  "SNAP", "PINS", "RBLX", "NET", "DDOG", "SNOW", "PANW", "CRWD", "TEAM", "NOW",
  "WDAY", "TTD", "MELI", "SE", "GRAB", "CPNG", "LI", "NIO", "XPEV", "LCID",
  "GME", "AMC", "NKLA", "DJT", "ROKU", "TTWO", "EA", "SONY", "WMT", "JPM",
  "GS", "V", "MA", "BAC", "F", "GM", "RACE", "HON", "CAT", "DE", "UNH", "JNJ",
  "PFE", "MRK", "ABBV", "LLY", "COST", "HD", "NKE", "SBUX", "MCD", "PEP", "KO",
]);

const TRADFI_COMMODITIES = new Set(["XAU", "XAG", "XPT", "XPD", "CL", "NATGAS", "COPPER", "BZ"]);
const TRADFI_INDICES = new Set(["QQQ", "SPY", "DIA", "IWM", "BTCDOM", "ALL"]);

export function isTradfi(symbol: string): boolean {
  const base = symbol.replace("USDT", "");
  return TRADFI_STOCKS.has(base) || TRADFI_COMMODITIES.has(base) || TRADFI_INDICES.has(base);
}
