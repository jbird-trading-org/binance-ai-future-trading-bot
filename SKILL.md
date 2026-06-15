# Neko Futures Trader — Agent Skill (TypeScript)

## Stack

- **Runtime:** Node.js 20+, TypeScript 5.8
- **Cache:** `ioredis-os` with in-memory fallback
- **Trading:** Binance Futures USDT-M via `src/lib/binance.ts`

## Layout

```
src/config.ts          — trading parameters
src/lib/               — binance, indicators, filters, dynamicCoins
src/redis/             — Redis client + cache
src/scanner/           — signal scanner (cli.ts = long-running entry)
src/monitor/           — SL/TP monitor
src/dashboard/         — dashboard API (:8080)
scripts/               — CLI utilities + test-pipeline.ts
```

## Commands

```bash
npm install && npm run build
npm test
npm run test:pipeline
npm run start:scanner
npm run start:monitor
npm run start:dashboard
npm run balance
npm run positions
```

## Config

- Static defaults: `src/config.ts`
- Env overrides: `.env` (`BINANCE_API_KEY`, `BINANCE_SECRET`, `REDIS_URL`, `SLEEP_MODE`)

## systemd

Use `npm run start:*` as `ExecStart` with `WorkingDirectory` set to project root.
