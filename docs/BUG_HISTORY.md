# 🐛 Neko Futures Trader — Full Bug History
## March 2026 — June 2026

> Dicatat: 2026-06-02 | Total: 47 bugs terdokumentasi
> Tujuan: Hindari bug yang sama terulang

---

## 🔴 CRITICAL (Loss > $50 / Crash Loop / Data Loss)

### BUG-001: Scanner Crash Loop — `cleanup_orphan_orders` NameError
- **Tanggal:** May 3, 2026
- **Symptom:** Scanner crash loop 27 jam, 1,393 error cycles
- **Root cause:** File `scanner.py` di-edit saat service restart → Python load partial version
- **Fix:** Wrap `cleanup_orphan_orders()` di try/except NameError
- **Commit:** N/A (session fix)
- **Lesson:** JANGAN edit file saat service restart. Selalu `py_compile` sebelum restart.

### BUG-002: Loss -$219 — Chase Entries di Market Crash
- **Tanggal:** May 15, 2026
- **Symptom:** 4 positions (COIN, MSTR, INJ, ZEC) rugi total -$219.32 (-13.1%)
- **Root cause:** Chase entries di 3.6-7.5% pump, volume rendah (0.3-1.8x), MIN_SCORE terlalu longgar (6)
- **Fix:** Volume filter ≥1.0x, chase limit 4%, RSI penalty, MIN_SCORE=7, LLM gate enabled
- **Commit:** `ffb6380`, `3776993`
- **Lesson:** Jangan masuk market tanpa volume confirmation. Chase limit harus ketat.

### BUG-003: Double-Close TP — TP1 Fire 3x, Close 75% instead of 25%
- **Tanggal:** May 10, 2026
- **Symptom:** AXSUSDT, CHZUSDT, KAVAUSDT, NEARUSDT, SUIUSDT — TP1 triggered 3x
- **Root cause:** No `tp1_done`/`tp2_done` persistent flags; `remaining_pct` check unreliable
- **Fix:** Added boolean flags di `pos_data` dict, changed `elif` ke independent `if`
- **File:** `price-monitor.py` lines 596-643
- **Lesson:** Partial close HARUS pakai persistent flags, bukan amount check.

### BUG-004: FIDAUSDT -$65 — Chase Exception >15% Breakout
- **Tanggal:** May 18, 2026
- **Symptom:** FIDA entered di 38.1% pump → rugi -$65.28
- **Root cause:** Chase exception >15% breakout membolehkan entry di pump extreme
- **Fix:** REMOVE chase exception entirely, hard reject di chase limit
- **Commit:** `ee79965`
- **Lesson:** NEVER ada exception untuk chase filter. Hard reject = hard reject.

### BUG-005: Win Rate 19% — 81/100 Trades Losing
- **Tanggal:** May 18, 2026 (pre-overhaul)
- **Symptom:** WR 19%, net PNL -$186.89
- **Root cause:** SL 5% + 10x leverage = 50% margin risk, TP 15% terlalu ambitious, volume filter 1.0x terlalu rendah
- **Fix:** Full overhaul: SL 3%, TP 8%, volume 1.5x, chase 4%, BTC regime check, loss cooldown 48h
- **Commit:** `ee79965`
- **Lesson:** R:R ratio harus realistis. TP 15% di crypto = jarang kena.

---

## 🟠 HIGH (Loss $10-50 / Feature Broken / Wrong Behavior)

### BUG-006: BTC Regime Terlalu Permissive — 3/3 Unanimous
- **Tanggal:** June 2, 2026
- **Symptom:** LONG entries masuk di market bearish → cut loss terus, balance $1600→$1200
- **Root cause:** BTC regime butuh 3/3 timeframe setuju BEARISH. Kalau 1 NEUTRAL → result NEUTRAL → LONG lolos
- **Fix:** Changed ke 2/3 majority
- **Commit:** `9a9130d`
- **Lesson:** Majority voting > unanimous untuk market regime.

### BUG-007: SHORT Candidates Gak Pernah di-Scan
- **Tanggal:** June 2, 2026
- **Symptom:** Market crash tapi 0 SHORT entries. 500+ losers gak pernah ke-scan.
- **Root cause:** `top_gainers + bottom_losers[:100]` → 95 gainers + 5 losers (-0.1%). Losers tergeser.
- **Fix:** Split scan by regime: BEARISH=85 losers + 15 gainers, BULLISH=85 gainers + 15 losers
- **Commit:** `75f3b06`
- **Lesson:** Selalu verify scan coverage. Gainers dan losers HARUS di-scan terpisah.

### BUG-008: TP1 Missed di +5% Profit
- **Tanggal:** May 12, 2026
- **Symptom:** Position di +5% profit tapi TP1 gak trigger
- **Root cause:** CHECK_INTERVAL=60s terlalu lambat + no high-water mark tracking
- **Fix:** CHECK_INTERVAL → 15 detik + `peak_profit` tracking (persist ke file)
- **Lesson:** Check interval harus cepat untuk SL/TP. Peak profit = safety net.

### BUG-009: Duplicate Algo Orders — 10 SL/TP di 4 Positions
- **Tanggal:** May 16, 2026
- **Symptom:** Health check place SL/TP baru tanpa cek existing → 10 duplicate orders
- **Root cause:** Health check gak query `openAlgoOrders` sebelum place baru
- **Fix:** HARUS query `/fapi/v1/openAlgoOrders` sebelum place SL/TP
- **Lesson:** Algo orders ≠ regular orders. Selalu cek endpoint yang benar.

### BUG-010: Orphaned Positions Tanpa SL/TP
- **Tanggal:** May 2026
- **Symptom:** Position di Binance tapi gak ada di `.positions_sl_tp.json` → makan margin
- **Root cause:** Scanner place order tapi gagal save ke tracking file
- **Fix:** Auto-detect di health check + auto-place SL/TP
- **Lesson:** Selalu verify position tercatat di tracking file setelah entry.

### BUG-011: Algo Order API Error -4120
- **Tanggal:** March-April 2026
- **Symptom:** SL/TP orders gagal dengan error `-4120: Order type not supported`
- **Root cause:** Pakai `/fapi/v1/order` (regular) instead of `/fapi/v1/algoOrder`
- **Fix:** SEMUA SL/TP harus pakai algo order API
- **Lesson:** Binance futures SL/TP = algo orders only.

### BUG-012: Precision Error — Float Artifacts di Quantity
- **Tanggal:** May 15, 2026
- **Symptom:** Order gagal: "Precision is over the maximum defined for this asset"
- **Root cause:** `qty_steps * step_size` produce `123.45670000000001`
- **Fix:** `quantity = float(f"{quantity:.{decimals}f}")`
- **Lesson:** SELALU format quantity ke step_size decimals.

### BUG-013: LLM Gate 98.5% Rejection Rate
- **Tanggal:** May 2026
- **Symptom:** 0 signals masuk, scanner idle terus
- **Root cause:** LLM terlalu ketat, reject 98.5% signals
- **Fix:** Disabled LLM gate sementara, kemudian overhaul prompt
- **Commit:** `9cbd1a1`
- **Lesson:** LLM filter harus balanced. Test rejection rate setelah deploy.

### BUG-014: LLM mimo-v2-pro Broken — Switch ke hermes-4-70b
- **Tanggal:** May 2026
- **Symptom:** LLM analyzer error, gak bisa analyze signals
- **Root cause:** `xiaomi/mimo-v2-pro` down via Nous endpoint
- **Fix:** Switch ke `hermes-4-70b`
- **Commit:** `4c39e4f`
- **Lesson:** Selalu ada fallback LLM model.

---

## 🟡 MEDIUM (Config Mismatch / Filter Issue / Minor Loss)

### BUG-015: Config Mismatch — `lib/config.py` vs `config.py`
- **Tanggal:** May 2026 (recurring)
- **Symptom:** Scanner pakai value berbeda dari config
- **Root cause:** `lib/config.py` copy terpisah, gak sync
- **Fix:** SELALU update kedua file saat ganti config
- **Lesson:** 2 config files = 2x risk. Consider single source of truth.

### BUG-016: `ema_50` Not Defined — NameError
- **Tanggal:** April 21, 2026
- **Symptom:** Scanner crash di symbol tertentu (THETAUSDT), 65 occurrences
- **Root cause:** `calc_ema(closes, 50)` gagal di try/except → ema_50 tetap None
- **Fix:** Fallback ke SMA: `(ema_50 or sma_50)`
- **Commit:** `8c3b933`
- **Lesson:** SEMUA variable yang bisa None harus punya fallback.

### BUG-017: Duplicate Orders & Telegram Posts
- **Tanggal:** April 27, 2026
- **Symptom:** Order yang sama di-place 2x, signal di-post 2x ke Telegram
- **Root cause:** Race condition di scanner loop
- **Fix:** Check existing orders sebelum place baru + posted signals tracking
- **Commit:** `6cad164`
- **Lesson:** SELALU cek existing state sebelum action.

### BUG-018: Trailing SL Gak Trigger untuk Saved Positions
- **Tanggal:** April 2026
- **Symptom:** Position di +5% profit tapi trailing SL gak activate
- **Root cause:** Position di-load dari file tapi trailing state gak ke-load
- **Fix:** Persist trailing state ke `.positions_sl_tp.json`
- **Commit:** `6e5dadd`
- **Lesson:** SEMUA runtime state harus persist ke file.

### BUG-019: Trailing TP Wrong Side Placement
- **Tanggal:** April 2026
- **Symptom:** TP placed ABOVE current untuk LONG (should be BELOW)
- **Root cause:** Logic error di `update_tp_trailing()`
- **Fix:** Corrected placement logic
- **Lesson:** LONG TP = di atas entry. SHORT TP = di bawah entry. Verify direction.

### BUG-020: Trailing SL/TP Double Execution
- **Tanggal:** April 2026
- **Symptom:** Cancel/re-place race conditions di algo orders
- **Root cause:** Trailing logic DUPLICATE di `price-monitor.py`
- **Fix:** Remove duplicate logic
- **Commit:** `b1f82f6`
- **Lesson:** Satu function = satu logic. Jangan duplicate.

### BUG-021: `continue` Bug — Skip ALL SL/TP Logic
- **Tanggal:** April 2026
- **Symptom:** Position [SAVED] gak pernah di-check SL/TP-nya
- **Root cause:** `continue` statement setelah [SAVED] skip semua trailing logic
- **Fix:** Remove incorrect `continue`
- **Lesson:** Review loop flow carefully. `continue` = skip EVERYTHING after it.

### BUG-022: MACD Returning +0.0000
- **Tanggal:** April 28, 2026
- **Symptom:** MACD histogram selalu 0
- **Root cause:** Calculation error di `calc_macd()`
- **Fix:** Fixed EMA series calculation
- **Commit:** `ffb6380`
- **Lesson:** Verify indicator output dengan known values.

### BUG-023: Volume Ratio 0.0x-0.2x (Suspicious)
- **Tanggal:** April 28, 2026
- **Symptom:** Volume ratio terlalu rendah di semua symbol
- **Root cause:** Pakai `volumes[-1]` (current incomplete candle) instead of `volumes[-2]`
- **Fix:** Changed ke completed candle volume
- **Commit:** `ffb6380`
- **Lesson:** SELALU pakai completed candles untuk indicators.

### BUG-024: Delisting Monitor Crash di TradFi Symbols
- **Tanggal:** April 27, 2026
- **Symptom:** Delisting monitor crash karena TradFi symbols (EWYUSDT) gak ada di spot
- **Root cause:** Monitor check spot delisting untuk futures-only symbols
- **Fix:** Skip TradFi symbols di delisting check
- **Commit:** `1a45279`
- **Lesson:** TradFi perps berbeda dari crypto perps. Filter terpisah.

### BUG-025: Sector Map Typo — `RNDR USDT` (with space)
- **Tanggal:** April 27, 2026
- **Symptom:** RNDRUSDT gak ke-map ke sector yang benar
- **Root cause:** Typo di SECTOR_MAP: `RNDR USDT` instead of `RNDRUSDT`
- **Fix:** Corrected string
- **Commit:** `7e9db44`
- **Lesson:** String matching = exact. Spasi matters.

### BUG-026: OHLC Index Errors
- **Tanggal:** April 2026
- **Symptom:** Wrong candle data (open/high/low/close terbalik)
- **Root cause:** Index salah di klines array
- **Fix:** Corrected indices: open=1, high=2, low=3, close=4
- **Commit:** `60f8bbe`, `7e9db44`
- **Lesson:** Binance klines format: [timestamp, open, high, low, close, volume, ...]

### BUG-027: Silent Baseline Gak Jalan — Track Past Events
- **Tanggal:** May 2026
- **Symptom:** Bot nge-post signal yang sudah ada (duplicate alerts)
- **Root cause:** Track past events instead of diff NEW only
- **Fix:** Silent baseline first, then diff
- **Lesson:** Core rule: NEVER track past events. Silent baseline → diff NEW only.

### BUG-028: Chase Filter Gak Ada Exception untuk Trending
- **Tanggal:** May 2026
- **Symptom:** Coin trending 5-6% tapi di-reject chase filter
- **Root cause:** Chase limit 4% terlalu ketat untuk trending market
- **Fix:** Backup chase limit 8% untuk trending moves (ADX>25)
- **Commit:** `5be3778`, `9ee1398`
- **Lesson:** Chase filter perlu exception untuk strong trends.

### BUG-029: Range Position Filter Missing untuk SHORT
- **Tanggal:** May 19, 2026
- **Symptom:** SHORT entries di bottom range (29-39%) → bounce → loss
- **Root cause:** No range position filter untuk SHORT
- **Fix:** Reject SHORT jika price <40% dari 30-period range
- **Commit:** `ee79965`
- **Lesson:** Entry di extreme range = high bounce risk. Filter wajib.

### BUG-030: Red Candle Check Missing di Bear Market SHORT
- **Tanggal:** May 2026
- **Symptom:** Bear market SHORT entries tanpa momentum confirmation
- **Root cause:** Red candle check di-skip untuk bear market
- **Fix:** Re-enabled dengan exception untuk strong breakdown
- **Lesson:** Bear market SHORT tetap butuh momentum confirmation.

---

## 🔵 LOW (Dashboard / UI / Minor / Cosmetic)

### BUG-031: Dashboard PnL Display Wrong
- **Tanggal:** March 2026
- **Symptom:** PnL menunjukkan realized instead of unrealized
- **Root cause:** `data.stats` vs `data.income` vs `data.pnl` confusion
- **Fix:** Use correct key for unrealized PNL
- **Commits:** `788be7e`, `3c95077`, `e031004`, `6609cbc`

### BUG-032: Dashboard Table Overflow
- **Tanggal:** March 2026
- **Symptom:** Open positions table overlap di mobile
- **Fix:** `overflow-x: auto`, wider columns
- **Commits:** `f857faa`, `53a627d`

### BUG-033: Last Positions Display Issues
- **Tanggal:** March 2026
- **Symptom:** Last positions gak muncul, salah urutan, overlap
- **Fix:** Multiple iterations (5+ commits)
- **Commits:** `08b2783`, `aaf73e2`, `ed2e622`, `d667cc6`, `4341a52`

### BUG-034: Share PnL Feature Broken
- **Tanggal:** March 2026
- **Symptom:** Share PnL button gak fungsi
- **Fix:** Revert entire feature
- **Commit:** `ae946d8`

### BUG-035: Toggle Button Not Clickable
- **Tanggal:** March 2026
- **Symptom:** Theme toggle button gak bisa diklik
- **Fix:** CSS z-index fix
- **Commit:** `58add9d`

### BUG-036: .env Hardcoded API Keys di Git
- **Tanggal:** March 2026
- **Symptom:** API keys visible di git history
- **Root cause:** Hardcoded keys di source code
- **Fix:** Move ke `.env`, add `.gitignore`, git-filter-repo
- **Commits:** `4d6e2a3`, `67b2bb9`, `ca5258f`
- **Lesson:** NEVER commit API keys. SELALU pakai .env.

### BUG-037: Leaked Telegram Bot Token di Git History
- **Tanggal:** May 19, 2026
- **Symptom:** Token `8531470868:AAFG...0ZB8` visible di 6 commits
- **Root cause:** Token committed before .gitignore
- **Fix:** git-filter-repo rewrite + token rotation
- **Lesson:** SELALU cek git history sebelum push public.

---

## ⚪ CONFIG / TUNING (Bukan bug, tapi salah tuning)

### CFG-001: MIN_SCORE Terlalu Rendah (5→6→7→8)
- **Timeline:** March→June 2026 (4x diubah)
- **Pattern:** Turunin → loss → naikin → signal dikit → turunin lagi
- **Current:** 8 (LONG), 6 (SHORT bear market)
- **Lesson:** MIN_SCORE = quality gate. Jangan kompromi.

### CFG-002: SL/TP Ratio Tidak Realistis
- **Timeline:** March→May 2026
- **Pattern:** SL 5% + TP 15% = jarang TP kena
- **Current:** SL 3% + TP 8%, R:R 1:2.7
- **Lesson:** TP harus realistis. 15% di crypto = fantasy.

### CFG-003: Volume Filter Terlalu Longgar
- **Timeline:** March→May 2026
- **Pattern:** Volume 0.5x → entry di low-volume pumps → loss
- **Current:** 1.5x (normal), 0.3x (bear SHORT)
- **Lesson:** Volume = confirmation. Tanpa volume = gambling.

### CFG-004: Chase Limit Tidak Konsisten
- **Timeline:** April→June 2026 (6x diubah)
- **Pattern:** Ketat → gak ada signal → longgar → chase loss
- **Current:** 4% (normal), 12% (bear SHORT), 8% (trending)
- **Lesson:** Chase limit perlu contextual, bukan satu angka.

### CFG-005: Leverage 10x Terlalu Tinggi
- **Status:** Masih 10x
- **Risk:** SL 3% × 10x = 30% margin loss per trade
- **Consideration:** Turunin ke 5x untuk reduce risk

---

## 📊 STATISTIK

| Kategori | Jumlah | % |
|----------|--------|---|
| 🔴 Critical | 5 | 11% |
| 🟠 High | 9 | 19% |
| 🟡 Medium | 16 | 34% |
| 🔵 Low | 7 | 15% |
| ⚪ Config | 5 | 11% |
| **TOTAL** | **42** | |

### Bug Terbanyak per Area:
1. **SL/TP/Trailing:** 10 bugs (24%)
2. **Scanner/Filter:** 8 bugs (19%)
3. **Order/Execution:** 6 bugs (14%)
4. **Config Mismatch:** 5 bugs (12%)
5. **Dashboard/UI:** 5 bugs (12%)
6. **Security:** 2 bugs (5%)

### Recurring Patterns (Paling Sering Terulang):
1. **Config mismatch** (lib/config.py vs config.py) — 3x
2. **Chase filter terlalu ketat/longgar** — 4x
3. **MIN_SCORE naik-turun** — 4x
4. **SL/TP order duplicates** — 3x
5. **Variable None tanpa fallback** — 2x

---

## ✅ PREVENTION CHECKLIST (untuk masa depan)

### Sebelum Deploy:
- [ ] `py_compile scanner.py` — syntax check
- [ ] Config sync: `config.py` ↔ `lib/config.py` ↔ scanner fallback
- [ ] Cek git history: `git diff HEAD~1` untuk perubahan yang gak disengaja

### Setelah Deploy:
- [ ] Monitor 3 scan cycles pertama
- [ ] Verify signals masuk (gak semua di-reject)
- [ ] Verify position tercatat di tracking file
- [ ] Cek SL/TP orders di `/fapi/v1/openAlgoOrders`

### Weekly Review:
- [ ] Win rate trend (naik/turun?)
- [ ] Avg win vs avg loss ratio
- [ ] Biggest loss analysis
- [ ] Filter rejection breakdown
