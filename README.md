<div align="center">

# Binance AI Future Trading Bot

**TypeScript autonomous trading system for Binance USDT-M Futures**

[![TypeScript](https://img.shields.io/badge/TypeScript-5.8+-blue.svg)](https://www.typescriptlang.org/)
[![Node.js](https://img.shields.io/badge/Node.js-20+-green.svg)](https://nodejs.org/)
[![Redis](https://img.shields.io/badge/Redis-ioredis--os-red.svg)](https://www.npmjs.com/package/ioredis-xyz)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

[Repository](https://github.com/jbird-trading-org/binance-ai-future-trading-bot) · Adaptive signal engine · Redis-backed cache · Live dashboard

*Formerly known as Neko Futures Trader — fully migrated to TypeScript*

</div>

---

## Overview

**Binance AI Future Trading Bot** is a production-oriented futures trading stack built for [Binance USDT-M Futures](https://www.binance.com/en/futures). It scans hundreds of perpetual contracts every minute, scores momentum setups with a multi-stage filter chain, manages stop-loss and take-profit in real time, and exposes account metrics through a web dashboard.

The bot adapts to **BTC market regime** (bullish / bearish / neutral) using multi-timeframe EMA analysis and relaxes or tightens filters accordingly — designed to perform in both trending and bear markets.

| Capability | Description |
|------------|-------------|
| **Signal scanner** | 60s cycle · dynamic coin universe · BTC regime gate · weighted scoring |
| **Price monitor** | Adaptive 5s/15s polling · trailing SL/TP · partial take-profit stages |
| **Dashboard API** | Live balance, positions, PnL · Redis-cached Binance snapshots |
| **Redis layer** | `ioredis-xyz` shared cache · graceful in-memory fallback |
| **Pipeline tests** | End-to-end verification against public Binance endpoints |

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Runtime | Node.js 20+, TypeScript 5.8 |
| Exchange | Binance Futures REST API (`/fapi/v1`, `/fapi/v3`) |
| Cache / state | [ioredis-xyz](https://www.npmjs.com/package/ioredis-xyz) |
| Testing | Vitest + custom pipeline runner |
| Config | `src/config.ts` + `.env` overrides |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  Binance USDT-M Futures API                 │
└───────────────┬─────────────────────┬───────────────────────┘
                │                     │
        ┌───────▼────────┐    ┌───────▼────────┐    ┌──────────▼─────────┐
        │    Scanner     │    │ Price Monitor  │    │  Dashboard :8080   │
        │  src/scanner/  │    │  src/monitor/  │    │  src/dashboard/    │
        │   60s cycle    │    │  SL/TP/trail   │    │  /api + static UI  │
        └───────┬────────┘    └───────┬────────┘    └──────────┬─────────┘
                │                     │                          │
                └─────────────────────┼──────────────────────────┘
                                      ▼
                         ┌────────────────────────┐
                         │   Redis (ioredis-xyz)   │
                         │  cache · pipeline state│
                         └────────────────────────┘
```

### Signal pipeline (per symbol)

1. Fetch klines, 24h ticker, volume ratio
2. Compute RSI, MACD, EMA, ATR, range position
3. Detect BTC regime (15m / 1h / 4h EMA majority)
4. Apply hard filters — chase limit, volume, MACD flat, range, direction conflict
5. Score signal (minimum 8 LONG / 6 SHORT-bear) and run quality filter chain
6. Publish status to Redis · log structured rejection reasons

---

## Quick Start

### Prerequisites

- Node.js **20+**
- Binance Futures API key (Futures enabled, **withdrawals disabled**)
- Optional: Redis 6+ for shared cache across services

### Install

```bash
git clone https://github.com/jbird-trading-org/binance-ai-future-trading-bot.git
cd binance-ai-future-trading-bot
npm install
cp .env.example .env
```

Edit `.env` with your credentials:

```bash
BINANCE_API_KEY=your_key
BINANCE_SECRET=your_secret

# Optional
REDIS_URL=redis://127.0.0.1:6379
REDIS_KEY_PREFIX=neko
SLEEP_MODE=false
```

### Build & verify

```bash
npm run build
npm test                 # unit tests
npm run test:pipeline    # full E2E pipeline (builds first)
```

### Run services

```bash
npm run start:scanner    # signal scanner (default entry)
npm run start:monitor    # SL/TP + trailing monitor
npm run start:dashboard  # http://localhost:8080
```

### CLI utilities

```bash
npm run balance          # wallet + margin summary
npm run positions        # open positions with SL/TP
npm run redis:health     # Redis connectivity check
```

---

## Configuration

Primary defaults live in [`src/config.ts`](src/config.ts):

| Parameter | Default | Description |
|-----------|---------|-------------|
| `leverage` | 10 | Futures leverage |
| `maxPositions` | 3 | Max concurrent positions |
| `minScoreNormal` | 8 | Min score for LONG entries |
| `minScoreShortBear` | 6 | Min score for SHORT in bear regime |
| `priceSl` / `priceTp` | 3% / 6% | Base stop-loss / take-profit |
| `useAtrSltp` | true | Dynamic SL/TP from ATR |
| `dynamicCoinsEnabled` | true | Auto-discover coin universe (≥ $2M volume) |
| `btcRegimeCheck` | true | Block LONG when BTC is bearish |
| `scanIntervalSec` | 60 | Scanner cycle interval |

**Sleep mode** — set `SLEEP_MODE=true` in `.env` to reduce position count and tighten entry criteria without code changes.

---

## Redis integration

Redis is optional. When `REDIS_URL` or `REDIS_HOST` is set, the bot uses `ioredis-xyz` for:

- Dashboard account cache (25s TTL)
- Dynamic coin list cache (1h TTL)
- BTC regime snapshot
- Scanner / monitor pipeline status keys

If Redis is unreachable, all cache operations fall back to in-memory storage so local development works without a server.

```bash
npm run redis:health
```

---

## Production deployment (systemd)

Example unit for the scanner:

```ini
[Unit]
Description=Binance AI Future Trading Bot — Scanner
After=network.target

[Service]
Type=simple
User=trader
WorkingDirectory=/opt/binance-ai-future-trading-bot
ExecStart=/usr/bin/npm run start:scanner
Environment=NODE_ENV=production
EnvironmentFile=/opt/binance-ai-future-trading-bot/.env
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Duplicate for `start:monitor` and `start:dashboard`. Use `./neko.sh` for operational shortcuts (balance, positions, sleep mode, logs).

---

## Project structure

```
binance-ai-future-trading-bot/
├── src/
│   ├── config.ts              # trading parameters
│   ├── types.ts               # shared TypeScript types
│   ├── lib/
│   │   ├── binance.ts         # signed REST client
│   │   ├── indicators.ts      # RSI, MACD, EMA, ATR
│   │   ├── signalFilter.ts    # quality filter chain
│   │   ├── dynamicCoins.ts    # auto coin universe
│   │   └── runtimeConfig.ts   # env-aware config
│   ├── redis/                 # ioredis-xyz client + cache
│   ├── scanner/               # signal engine + BTC regime
│   ├── monitor/               # SL/TP price monitor
│   └── dashboard/             # HTTP API + static UI
├── scripts/
│   ├── test-pipeline.ts       # full pipeline verification
│   ├── check-balance.ts
│   └── positions.ts
├── static/                    # dashboard HTML (neko-light.html)
├── tests/                     # vitest unit tests
└── neko.sh                    # ops helper script
```

---

## Testing

```bash
npm test                 # 15+ unit tests (config, indicators, redis, filters)
npm run test:pipeline    # 11-step E2E: build → coins → regime → scanner → monitor → dashboard
```

The pipeline test uses **public Binance endpoints** and does not require API keys for most steps.

---

## Environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `BINANCE_API_KEY` | Yes* | Binance Futures API key |
| `BINANCE_SECRET` | Yes* | Binance API secret |
| `REDIS_URL` | No | Redis connection URL |
| `REDIS_KEY_PREFIX` | No | Key namespace (default: `neko`) |
| `SLEEP_MODE` | No | `true` / `false` — conservative trading mode |
| `TELEGRAM_BOT_TOKEN` | No | Telegram notifications |
| `OPENROUTER_API_KEY` | No | LLM signal gate (future use) |

\*Required for live trading, balance, and positions commands.

---

## Risk disclaimer

**This software is for educational and research purposes.** Cryptocurrency futures trading involves substantial risk of loss. Past performance does not guarantee future results. Never trade with funds you cannot afford to lose. The authors and [jbird-trading-org](https://github.com/jbird-trading-org) are not responsible for any financial losses.

---

## License

MIT — see [LICENSE](LICENSE).

---

<div align="center">

**Binance AI Future Trading Bot** · [jbird-trading-org](https://github.com/jbird-trading-org)

</div>
