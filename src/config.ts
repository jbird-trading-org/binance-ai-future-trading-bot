/** Trading configuration — ported from config.py */

export const SAFE_COINS = [
  "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT",
  "ADAUSDT", "AVAXUSDT", "DOTUSDT", "LINKUSDT", "LTCUSDT", "BCHUSDT",
  "ATOMUSDT", "UNIUSDT", "ETCUSDT", "XLMUSDT", "FILUSDT",
  "APTUSDT", "NEARUSDT", "ARBUSDT", "OPUSDT", "AAVEUSDT", "MKRUSDT",
  "GRTUSDT", "SNXUSDT", "IMXUSDT", "ALGOUSDT", "SANDUSDT",
  "MANAUSDT", "AXSUSDT", "CHZUSDT", "ENJUSDT", "NEOUSDT", "ZECUSDT",
  "EOSUSDT", "THETAUSDT", "KAVAUSDT", "ZILUSDT", "KSMUSDT",
  "RUNEUSDT", "MINAUSDT", "QNTUSDT", "LDOUSDT", "SUIUSDT",
  "SEIUSDT", "TIAUSDT", "INJUSDT", "WIFUSDT", "ORDIUSDT",
  "RENDERUSDT", "TAOUSDT", "ONDOUSDT", "STXUSDT",
  "TRXUSDT", "EIGENUSDT", "DYDXUSDT", "CAKEUSDT", "ENSUSDT",
  "WLDUSDT", "JUPUSDT", "1000PEPEUSDT", "1000SHIBUSDT",
  "1000BONKUSDT", "ENAUSDT", "PENGUUSDT", "TRUMPUSDT", "TONUSDT",
  "HYPEUSDT", "POLUSDT",
  "TSLAUSDT", "NVDAUSDT", "AAPLUSDT", "AMZNUSDT", "GOOGLUSDT", "METAUSDT",
  "MSFTUSDT", "AMDUSDT", "COINUSDT", "MSTRUSDT", "HOODUSDT", "CRCLUSDT",
  "PLTRUSDT", "BABAUSDT", "TSMUSDT", "AVGOUSDT", "QCOMUSDT",
  "MUUSDT", "BILLUSDT", "SNDKUSDT",
  "QQQUSDT", "SPYUSDT",
  "BTCDOMUSDT", "ALLUSDT",
  "XAUUSDT", "XAGUSDT", "XPTUSDT", "XPDUSDT",
  "CLUSDT", "BZUSDT", "NATGASUSDT", "COPPERUSDT",
] as const;

export const BLACKLISTED_SYMBOLS = [
  "TRUSTUSDT", "B2USDT", "PROMPTUSDT", "MITOUSDT", "MAGMAUSDT",
  "FETUSDT", "XPLUSDT", "LABUSDT", "RVNUSDT", "INTCUSDT",
  "NAORISUSDT", "CLOUSDT", "FHEUSDT", "PLAYUSDT", "GWEIUSDT",
  "UAIUSDT", "AINUSDT", "VELVETUSDT", "MIRAUSDT", "AKTUSDT",
  "BIOUSDT", "DODOXUSDT", "CVCUSDT", "SIRENUSDT", "FUSDT",
  "PRLUSDT", "DUSKUSDT", "PENDLEUSDT", "GTCUSDT", "DEEPUSDT",
  "LAUSDT", "CGPTUSDT", "BEAMXUSDT", "XPINUSDT", "HIGHUSDT",
  "VVVUSDT", "EWYUSDT", "BANUSDT", "ORDIUSDT",
] as const;

export const config = {
  leverage: 10,
  maxPositions: 3,
  maxSameDirection: 2,
  autoFillEmptySlots: true,
  entryPercent: 8,

  sleepMode: false,
  maxPositionsSleep: 2,
  entryPercentSleep: 5,
  minScoreSleep: 7,

  minScoreNormal: 8,
  minScoreShortBear: 6,

  priceTp: 6.0,
  priceSl: 3.0,

  useAtrSltp: true,
  slAtrMultiplier: 1.5,
  tpAtrMultiplier: 3.0,
  slMin: 1.5,
  slMax: 5.0,
  tpMin: 3.0,
  tpMax: 10.0,

  minProfitBreakeven: 1.5,
  trailSlLock: 1.0,
  trailSlDistance: 1.0,
  minProfitTrailingTp: 6.0,
  trailPercent: 1.5,

  tp1Percent: 4.0,
  tp1ClosePct: 0.25,
  tp2Percent: 6.0,
  tp2ClosePct: 0.25,

  confidenceSizing: true,
  confidenceLow: 0.5,
  confidenceMed: 0.7,
  confidenceHigh: 0.85,

  minWinlossRatio: 1.0,
  wlRatioWindow: 50,
  wlRatioPauseHours: 6,

  cooldownLoss1: 24,
  cooldownLoss2: 72,
  cooldownLoss3: 168,

  autoBlacklistEnabled: true,
  autoBlacklistConsecutiveLosses: 3,

  postSignalsToTelegram: true,
  notifyOnOpen: true,
  notifyOnClose: true,
  notifyOnBreakeven: false,
  notifyOnTrailingSl: false,
  notifyOnTrailingTp: false,

  scanIntervalSec: 60,
  minPriceChange: 2.0,
  skipRecentHours: 24,
  lossCooldownHours: 48,
  minVolumeRatio: 1.5,
  chaseLimitCrypto: 3.5,
  chaseLimitTradfi: 5.0,
  macdFlatCrypto: 0.012,
  macdFlatTradfi: 0.001,
  emaPositionLimitCrypto: 65,
  emaPositionLimitTradfi: 80,
  btcRegimeCheck: true,

  dynamicCoinsEnabled: true,
  dynamicMinVolume: 2_000_000,
  blacklistedSymbols: [...BLACKLISTED_SYMBOLS],
  safeCoins: [...SAFE_COINS],

  llmEnabled: true,
  llmModel: "anthropic/claude-haiku-4.5",
  llmMinScore: 4,
  llmTemperature: 0.1,
  llmBaseUrl: "https://inference-api.nousresearch.com/v1/chat/completions",
  llmTimeout: 15,
  llmCacheTtl: 300,
  llmMinConfidence: 0.6,
  llmFallback1Enabled: false,
  llmFallback1BaseUrl: "https://openrouter.ai/api/v1/chat/completions",
  llmFallback1Model: "nousresearch/hermes-4-70b",
  llmFallback2Enabled: false,
  llmFallback2BaseUrl: "https://api.minimaxi.chat/v1/chat/completions",
  llmFallback2Model: "MiniMax-M2.5",

  maxMarginPercent: 45,
  maxRiskPercent: 1.5,

  binanceBaseUrl: "https://fapi.binance.com",
  dashboardPort: 8080,
  dashboardCacheTtlSec: 25,
} as const;

export type NekoConfig = typeof config;
