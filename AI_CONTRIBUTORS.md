# AI Contributors

This project is developed with significant AI assistance, primarily through
**Claude (Anthropic)** orchestrated via **[Hermes Agent](https://github.com/NousResearch/hermes-agent)**.

In the spirit of transparent attribution, this file documents what AI
contributed and where the human (the maintainer) directed, decided, and
verified.

## Contribution model

- **Maintainer (`@lukmanc405`)** — defines product goals, trading strategy,
  risk parameters, market intuition (entry-timing pathology, bear/bull
  regime calls), and approves every change before it ships.
- **Claude (via Hermes Agent)** — implementation, refactors, debugging,
  log analysis, documentation, code review, and infrastructure scripting.

Every commit is reviewed and run by the maintainer. Trading decisions,
parameter values, and the overall design are human-owned.

## Tooling

- **Hermes Agent** — task orchestration, terminal/file/git tools, persistent
  skills, cron jobs (daily eval, win-rate monitor, health checks).
- **Claude (Sonnet / Opus)** — primary code generator and reviewer.
- **OpenRouter / Nous models** — used inside the trading bot itself for the
  LLM signal-quality gate (`xiaomi/mimo-v2-pro`, `hermes-4-70b`,
  `MiniMax-M2.5`). Independent of the development workflow.

## Contribution log

Reverse-chronological. Commits are tagged where applicable.

### 2026-05-19 — README & docs accuracy pass
- Full README rewrite to portfolio-grade structure (`7d55fa5`)
- README accuracy audit — 13 corrections to match actual code (`ea8222b`)
  - Scan interval, price-monitor cadence, LLM order, coin coverage,
    project tree, pipeline steps, changelog
- Skill `neko-service-debugging` updated with `range_pos` protection notes

### 2026-05-19 — Bear market SHORT filters + range_pos protection (`ee79965`)
- Diagnosis: 19% win rate, 81 losses on bear regime
- Maintainer's intuition: "entri short dari bawah kena perlawanan candle"
  → translated to a 30-bar range-position filter
- Implementation: `range_pos > 70%` rejects LONG (chasing tops),
  `range_pos < 30%` rejects SHORT (shorting bottoms), with TradFi
  variants and a `|price_change| > 7%` breakout escape hatch
- Bear-market SHORT relaxations: direction-conflict allowed,
  RSI guard 35 → 15, MACD-flat exception with vol ≥ 1.0x
- Result: WR 19% → 67% on the next batch

### 2026-05-18 — Trading pattern overhaul (`3a4c462`)
- Diagnosis of -$117 / 22% WR drawdown
- Tightened SL 5% → 3%, TP 15% → 8%, MIN_VOLUME_RATIO 1.0 → 1.5,
  CHASE_LIMIT 6%/8% → 4%/5% (no exception)
- Added BTC regime check, EMA9/EMA21 trend filter, 48h loss cooldown
- Dynamic coin universe (Binance API) replacing static SAFE_COINS

### 2026-05-13 — TradFi support
- Stocks/indices/commodities perp filters and delisting whitelist
- Crypto-index perps (BTCDOMUSDT, ALLUSDT) (`af1b0c5`)

### 2026-05-06 — LLM gate tuning, SL/TP overhaul (`9cbd1a1`, `99fdbfa`)
- LLM rejection rate analysis (98.5% → fail-open with relaxed
  anti-chasing 5%)
- Trailing SL order fix, auto-calculate missing SL/TP, persist state

### 2026-04 — Foundation
- Initial scanner + price-monitor + dashboard architecture
- Algo-order migration (Binance `/fapi/v1/algoOrder`)
- Multi-timeframe analysis, partial TPs, delisting monitor

## Verification

Every change shipped here is:
1. `py_compile` checked
2. Restarted on the live service (`neko-scanner`, `neko-monitor`)
3. Monitored for 3+ scan cycles before being trusted
4. Audited via `npm run test:pipeline` and monitoring services
   cron job

When AI-suggested changes degraded performance, they were reverted by the
maintainer — see the May 14-18 drawdown and the subsequent overhaul above.

## Why disclose

Transparent attribution is becoming standard practice in serious open-source
projects. AI accelerated this work by an order of magnitude, but it also
introduced regressions that had to be caught and reverted. Saying so
plainly is more useful than pretending otherwise.

If you're forking or studying this repo, you should know the work split.
The trading edge comes from the maintainer's market intuition; the
implementation velocity comes from AI.
