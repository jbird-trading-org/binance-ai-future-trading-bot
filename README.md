<div align="center">

# 🐱 Neko Futures Trader

**Autonomous Binance Futures bot with adaptive bear-market signal detection**

[![TypeScript](https://img.shields.io/badge/TypeScript-5.8+-blue.svg)](https://www.typescriptlang.org/)
[![Node](https://img.shields.io/badge/Node-20+-green.svg)](https://nodejs.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

*Quant-grade signal scoring · Real-time risk management · Redis-backed cache*

</div>

---

## Quick Start

```bash
git clone https://github.com/lukmanc405/neko-futures-trader.git
cd neko-futures-trader
npm install
cp .env.example .env   # add Binance + optional Redis keys
npm run build
npm run test:pipeline  # verify full pipeline
```

### Run services

```bash
npm run start:scanner    # signal scanner (60s cycle)
npm run start:monitor    # SL/TP price monitor
npm run start:dashboard  # dashboard API on :8080
```

### CLI

```bash
npm run balance          # account balance
npm run positions        # open positions + SL/TP
npm run redis:health     # Redis or memory fallback
```

---

## Architecture

```
Binance Futures API
       │
       ├── scanner (src/scanner/)     — 60s signal cycle
       ├── monitor (src/monitor/)     — SL/TP + trailing
       └── dashboard (src/dashboard/) — :8080 + Redis cache
              │
              └── redis (ioredis-os) — shared state / cache
```

---

## Configuration

Trading parameters live in `src/config.ts`. Override sleep mode via `.env`:

```bash
SLEEP_MODE=true   # fewer positions, higher min score
```

Redis (optional):

```bash
REDIS_URL=redis://127.0.0.1:6379
REDIS_KEY_PREFIX=neko
```

---

## systemd (production)

```ini
[Service]
WorkingDirectory=/path/to/neko-futures-trader
ExecStart=/usr/bin/npm run start:scanner
Environment=NODE_ENV=production
Restart=always
```

Repeat for `start:monitor` and `start:dashboard`.

---

## Project Structure

```
neko-futures-trader/
├── src/
│   ├── config.ts           # trading parameters
│   ├── lib/                # binance, indicators, filters, dynamic coins
│   ├── redis/              # ioredis-os client + cache
│   ├── scanner/            # signal scanner
│   ├── monitor/            # price monitor
│   └── dashboard/          # web dashboard API
├── scripts/
│   ├── test-pipeline.ts    # full pipeline test
│   ├── check-balance.ts
│   └── positions.ts
├── static/                 # dashboard UI
└── tests/                  # vitest unit tests
```

---

## Testing

```bash
npm test                 # unit tests
npm run test:pipeline    # end-to-end pipeline (public Binance API)
```

---

## Disclaimer

This is a personal trading project, not financial advice. Crypto futures trading carries substantial risk.

MIT License — see [LICENSE](LICENSE).
