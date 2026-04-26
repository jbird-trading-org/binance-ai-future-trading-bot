#!/usr/bin/env python3
"""
Near-High Filter Backtest for Neko Futures Trader

Tests different near-high filter thresholds (0%, 2%, 4%, 6%)
to find the optimal balance between win rate and opportunity cost.

Strategy:
- Walk through historical 1h candles bar-by-bar
- Generate simplified signals using Neko's core scoring logic
- Apply near-high filter at different thresholds
- Simulate trades with SL=5%, TP=15% (Neko defaults)
- Compare: win rate, total trades, net PNL, profit factor

Usage:
    python3 scripts/backtest_near_high.py [--symbols 20] [--days 90]
"""

import os
import sys
import json
import math
import time
import random
import argparse
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional

try:
    import requests
except ImportError:
    print("❌ requests required: pip install requests")
    sys.exit(1)

# === CONFIG (match Neko defaults) ===
PRICE_SL = 5.0    # Stop loss %
PRICE_TP = 15.0   # Take profit %
LEVERAGE = 10
MIN_SCORE = 4     # Minimum signal score to trigger trade

# Fetch Binance data (public, no auth needed)
BINANCE_FAPI = "https://fapi.binance.com"


def get_top_symbols(n=50):
    """Get top N USDT futures symbols by 24h volume."""
    try:
        r = requests.get(f"{BINANCE_FAPI}/fapi/v1/ticker/24hr", timeout=15)
        tickers = r.json()
        usdt = [t for t in tickers if t['symbol'].endswith('USDT')
                and float(t.get('quoteVolume', 0)) > 1_000_000
                and not any(x in t['symbol'] for x in ['UP', 'DOWN', 'BULL', 'BEAR'])]
        usdt.sort(key=lambda x: float(x.get('quoteVolume', 0)), reverse=True)
        return [t['symbol'] for t in usdt[:n]]
    except Exception as e:
        print(f"Error fetching symbols: {e}")
        return []


def get_klines(symbol, interval='1h', limit=1500):
    """Fetch historical klines from Binance Futures. Max 1500 per call."""
    try:
        url = f"{BINANCE_FAPI}/fapi/v1/klines"
        params = {'symbol': symbol, 'interval': interval, 'limit': limit}
        r = requests.get(url, params=params, timeout=15)
        data = r.json()
        if isinstance(data, list):
            return data
        return []
    except Exception as e:
        print(f"  Error fetching {symbol}: {e}")
        return []


def calc_ema(prices, period):
    """Calculate EMA from list of close prices."""
    if len(prices) < period:
        return None
    k = 2 / (period + 1)
    ema_val = prices[0]
    for price in prices[1:]:
        ema_val = price * k + ema_val * (1 - k)
    return ema_val


def calc_rsi(closes, period=14):
    """Calculate RSI."""
    if len(closes) < period + 1:
        return 50
    deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
    gains = [d if d > 0 else 0 for d in deltas[-period:]]
    losses = [-d if d < 0 else 0 for d in deltas[-period:]]
    avg_gain = sum(gains) / period if gains else 0
    avg_loss = sum(losses) / period if losses else 0
    if avg_loss == 0:
        return 100
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def calc_stochrsi(closes, rsi_period=14, stoch_period=14, k_period=3, d_period=3):
    """Simplified StochRSI."""
    if len(closes) < rsi_period + stoch_period:
        return {'k': 50, 'd': 50, 'prev_k': 50}
    
    # Calculate RSI values
    rsi_vals = []
    for i in range(rsi_period, len(closes)):
        deltas = [closes[j] - closes[j-1] for j in range(i-rsi_period+1, i+1)]
        gains = [d if d > 0 else 0 for d in deltas]
        losses = [-d if d < 0 else 0 for d in deltas]
        avg_g = sum(gains) / rsi_period
        avg_l = sum(losses) / rsi_period
        if avg_l == 0:
            rsi_vals.append(100)
        else:
            rs = avg_g / avg_l
            rsi_vals.append(100 - (100 / (1 + rs)))
    
    if len(rsi_vals) < stoch_period:
        return {'k': 50, 'd': 50, 'prev_k': 50}
    
    # StochRSI %K
    recent_rsi = rsi_vals[-stoch_period:]
    min_rsi = min(recent_rsi)
    max_rsi = max(recent_rsi)
    if max_rsi == min_rsi:
        k = 50
    else:
        k = ((rsi_vals[-1] - min_rsi) / (max_rsi - min_rsi)) * 100
    
    # Simple %D = SMA of %K
    k_vals = []
    for i in range(stoch_period - 1, len(rsi_vals)):
        window = rsi_vals[i - stoch_period + 1:i + 1]
        mn, mx = min(window), max(window)
        if mx == mn:
            k_vals.append(50)
        else:
            k_vals.append(((rsi_vals[i] - mn) / (mx - mn)) * 100)
    
    d = sum(k_vals[-d_period:]) / d_period if len(k_vals) >= d_period else k
    prev_k = k_vals[-2] if len(k_vals) >= 2 else k
    
    return {'k': k, 'd': d, 'prev_k': prev_k}


def calc_adx_simple(candles, period=14):
    """Simplified ADX calculation."""
    if len(candles) < period + 1:
        return {'adx': 25, 'plus_di': 25, 'minus_di': 25}
    
    highs = [float(c[2]) for c in candles]
    lows = [float(c[3]) for c in candles]
    closes = [float(c[4]) for c in candles]
    
    tr_list = []
    plus_dm = []
    minus_dm = []
    
    for i in range(1, len(candles)):
        tr = max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1]))
        tr_list.append(tr)
        
        up_move = highs[i] - highs[i-1]
        down_move = lows[i-1] - lows[i]
        
        if up_move > down_move and up_move > 0:
            plus_dm.append(up_move)
        else:
            plus_dm.append(0)
        
        if down_move > up_move and down_move > 0:
            minus_dm.append(down_move)
        else:
            minus_dm.append(0)
    
    if len(tr_list) < period:
        return {'adx': 25, 'plus_di': 25, 'minus_di': 25}
    
    # Smooth
    atr = sum(tr_list[-period:]) / period
    plus_di_val = (sum(plus_dm[-period:]) / period / atr * 100) if atr > 0 else 25
    minus_di_val = (sum(minus_dm[-period:]) / period / atr * 100) if atr > 0 else 25
    
    dx = abs(plus_di_val - minus_di_val) / (plus_di_val + minus_di_val) * 100 if (plus_di_val + minus_di_val) > 0 else 25
    adx_val = dx  # Simplified (proper ADX uses EMA of DX)
    
    return {'adx': min(100, adx_val), 'plus_di': plus_di_val, 'minus_di': minus_di_val}


def calc_fisher_simple(candles, period=9):
    """Simplified Fisher Transform."""
    if len(candles) < period + 2:
        return 0.0
    
    highs = [float(c[2]) for c in candles]
    lows = [float(c[3]) for c in candles]
    mid = [(h + l) / 2 for h, l in zip(highs, lows)]
    
    value1 = 0.0
    fisher = 0.0
    
    for i in range(period, len(mid)):
        max_h = max(mid[i - period + 1:i + 1])
        min_l = min(mid[i - period + 1:i + 1])
        
        if max_h - min_l == 0:
            value0 = 0.0
        else:
            value0 = 0.33 * 2 * ((mid[i] - min_l) / (max_h - min_l) - 0.5) + 0.67 * value1
        
        value0 = max(-0.999, min(0.999, value0))
        
        if value0 != 0:
            fisher = 0.5 * math.log((1 + value0) / (1 - value0)) + 0.5 * fisher
        
        value1 = value0
    
    return fisher


def calc_choppiness(candles, period=14):
    """Choppiness Index."""
    if len(candles) < period + 1:
        return 50.0
    
    highs = [float(c[2]) for c in candles[-period:]]
    lows = [float(c[3]) for c in candles[-period:]]
    closes_prev = [float(c[4]) for c in candles[-period-1:-1]]
    
    atr_sum = 0
    for i in range(len(highs)):
        tr = max(highs[i] - lows[i], abs(highs[i] - closes_prev[i]), abs(lows[i] - closes_prev[i]))
        atr_sum += tr
    
    max_h = max(highs)
    min_l = min(lows)
    
    if max_h == min_l or atr_sum == 0:
        return 50.0
    
    chop = 100.0 * (atr_sum / (period * (max_h - min_l)))
    return min(100.0, max(0.0, chop))


def score_signal(candles, idx, direction):
    """Calculate signal score at a specific bar, matching Neko's scoring logic.
    
    Uses candles up to and including idx (exclusive of idx+1).
    Returns dict with score and individual indicator values.
    """
    if idx < 50:
        return None
    
    window = candles[:idx + 1]
    closes = [float(c[4]) for c in window]
    opens = [float(c[1]) for c in window]
    highs = [float(c[2]) for c in window]
    lows = [float(c[3]) for c in window]
    volumes = [float(c[5]) for c in window]
    
    current = closes[-1]
    
    # Volume
    avg_vol = sum(volumes[-24:]) / 24 if len(volumes) >= 24 else sum(volumes) / len(volumes)
    recent_vol = volumes[-1]
    vol_ratio = recent_vol / avg_vol if avg_vol > 0 else 1
    
    # Price change (24h)
    price_change = ((closes[-1] - closes[-24]) / closes[-24]) * 100 if len(closes) >= 24 else 0
    
    # EMAs
    ema_9 = calc_ema(closes, 9)
    ema_21 = calc_ema(closes, 21)
    ema_50 = calc_ema(closes, 50) if len(closes) >= 50 else current
    sma_50 = sum(closes[-50:]) / 50 if len(closes) >= 50 else current
    
    # RSI
    rsi_14 = calc_rsi(closes, 14)
    
    # StochRSI
    stoch_rsi = calc_stochrsi(closes)
    
    # ADX
    adx_data = calc_adx_simple(window)
    adx_val = adx_data['adx']
    plus_di = adx_data['plus_di']
    minus_di = adx_data['minus_di']
    
    # Fisher
    fisher_val = calc_fisher_simple(window)
    fisher_prev = calc_fisher_simple(window[:-1]) if len(window) > 10 else 0
    
    # Choppiness
    chop_val = calc_choppiness(window)
    
    # VWAP (24h)
    if len(window) >= 24:
        typical = [(float(c[2]) + float(c[3]) + float(c[4])) / 3 for c in window[-24:]]
        vols_24 = [float(c[5]) for c in window[-24:]]
        vwap = sum(t * v for t, v in zip(typical, vols_24)) / sum(vols_24) if sum(vols_24) > 0 else current
    else:
        vwap = current
    
    # EMA position (ATR band position)
    tr_list = []
    for i in range(1, min(15, len(window))):
        h = float(window[-i][2])
        l = float(window[-i][3])
        pc = float(window[-i-1][4])
        tr_list.append(max(h - l, abs(h - pc), abs(l - pc)))
    atr = sum(tr_list) / len(tr_list) if tr_list else current * 0.02
    ema_21_val = ema_21 or current
    ema_position = ((current - (ema_21_val - atr)) / (atr * 2)) * 100 if atr > 0 else 50
    
    # Bollinger squeeze
    sma_20 = sum(closes[-20:]) / 20 if len(closes) >= 20 else current
    std_20 = (sum((c - sma_20) ** 2 for c in closes[-20:]) / 20) ** 0.5 if len(closes) >= 20 else sma_20 * 0.02
    bb_upper = sma_20 + (2 * std_20)
    bb_lower = sma_20 - (2 * std_20)
    bb_width = (bb_upper - bb_lower) / sma_20 * 100 if sma_20 > 0 else 5
    avg_bb_width = 5.0  # Approximate
    squeeze = 1 if bb_width < avg_bb_width * 0.7 else 0
    
    # WMA trend
    wma_10 = sum(closes[-10:]) / 10 if len(closes) >= 10 else current
    wma_30 = sum(closes[-30:]) / 30 if len(closes) >= 30 else current
    trend_base = (current > sma_50) and (wma_10 > wma_30)
    
    # MACD histogram
    if len(closes) >= 35:
        ema_12 = calc_ema(closes[-26:], 12) or current
        ema_26 = calc_ema(closes[-26:], 26) or current
        macd_line = ema_12 - ema_26
        signal_line = calc_ema([macd_line] * 9, 9) or macd_line
        histogram = macd_line - signal_line
    else:
        histogram = 0
    
    score = 0
    
    if direction == "LONG":
        if vol_ratio >= 3: score += 1
        if price_change > 10: score += 2
        elif price_change > 5: score += 1
        if current > sma_50 and wma_10 > wma_30: score += 1
        if 0 <= ema_position <= 100 and ema_position < 50: score += 1
        if rsi_14 < 30: score += 1
        if current > vwap: score += 1
        if ema_9 and current > ema_9: score += 1
        if current > vwap and (ema_9 and current > ema_9): score += 1
        if squeeze > 0: score += 1
        if stoch_rsi['k'] < 30: score += 1
        if stoch_rsi['k'] > stoch_rsi['d'] and stoch_rsi['prev_k'] < stoch_rsi['d'] and stoch_rsi['k'] < 50: score += 1
        if adx_val > 25: score += 1
        if plus_di > minus_di: score += 1
        if fisher_val > 0 and fisher_val > fisher_prev: score += 1
        if fisher_val > 0 and fisher_prev < 0: score += 1
    else:  # SHORT
        if ema_9 and ema_21 and ema_9 < ema_21: score += 2
        if ema_9 and ema_21 and current < ema_9 and current < ema_21: score += 1
        if rsi_14 < 50: score += 1
        if histogram < 0: score += 2
        if price_change < -2: score += 2
        if current < vwap: score += 1
        if ema_9 and current < ema_9: score += 1
        if current < vwap and (ema_9 and current < ema_9): score += 1
        if stoch_rsi['k'] > 70: score += 1
        if stoch_rsi['k'] < stoch_rsi['d'] and stoch_rsi['prev_k'] > stoch_rsi['d'] and stoch_rsi['k'] > 50: score += 1
        if adx_val > 25: score += 1
        if minus_di > plus_di: score += 1
        if fisher_val < 0 and fisher_val < fisher_prev: score += 1
        if fisher_val < 0 and fisher_prev > 0: score += 1
    
    return {
        'score': score,
        'rsi': rsi_14,
        'adx': adx_val,
        'fisher': fisher_val,
        'chop': chop_val,
        'vol_ratio': vol_ratio,
        'ema_position': ema_position,
        'histogram': histogram,
    }


def passes_filters(candles, idx, direction, indicators, near_high_pct):
    """Check if a signal passes Neko's anti-chase filters.
    
    near_high_pct: 0.0 = no filter, 2.0 = 2%, 4.0 = 4%, etc.
    """
    closes = [float(c[4]) for c in candles[:idx + 1]]
    highs = [float(c[2]) for c in candles[:idx + 1]]
    lows = [float(c[3]) for c in candles[:idx + 1]]
    current = closes[-1]
    
    rsi_14 = indicators['rsi']
    ema_position = indicators['ema_position']
    chop_val = indicators['chop']
    adx_val = indicators['adx']
    histogram = indicators['histogram']
    
    # EMA position filter
    if direction == "LONG" and ema_position > 70:
        return False
    if direction == "SHORT" and ema_position < 30:
        return False
    
    # RSI filter
    if direction == "LONG" and rsi_14 > 65:
        return False
    if direction == "SHORT" and rsi_14 < 35:
        return False
    
    # Near high/low filter (the one we're testing)
    if near_high_pct > 0:
        if direction == "LONG":
            recent_high = max(highs[-20:]) if len(highs) >= 20 else max(highs)
            threshold = 1.0 - (near_high_pct / 100.0)
            if current >= recent_high * threshold:
                return False
        else:
            recent_low = min(lows[-20:]) if len(lows) >= 20 else min(lows)
            threshold = 1.0 + (near_high_pct / 100.0)
            if current <= recent_low * threshold:
                return False
    
    # Choppiness filter
    if chop_val > 60:
        return False
    
    # ADX filter
    if adx_val < 20:
        return False
    
    # MACD histogram filter
    if direction == "LONG" and histogram < 0:
        return False
    if direction == "SHORT" and histogram > 0:
        return False
    
    return True


def simulate_trade(candles, entry_idx, direction):
    """Simulate a trade from entry bar. Returns (pnl_pct, exit_reason, bars_held).
    
    Uses SL=5%, TP=15% matching Neko's config.
    """
    entry_price = float(candles[entry_idx][4])
    
    if direction == "LONG":
        sl_price = entry_price * (1 - PRICE_SL / 100)
        tp_price = entry_price * (1 + PRICE_TP / 100)
    else:
        sl_price = entry_price * (1 + PRICE_SL / 100)
        tp_price = entry_price * (1 - PRICE_TP / 100)
    
    # Walk forward up to 48 bars (48h max hold)
    max_bars = min(48, len(candles) - entry_idx - 1)
    
    for i in range(1, max_bars + 1):
        bar = candles[entry_idx + i]
        high = float(bar[2])
        low = float(bar[3])
        
        if direction == "LONG":
            # Check SL first (conservative)
            if low <= sl_price:
                pnl_pct = -PRICE_SL
                return pnl_pct, 'SL', i
            if high >= tp_price:
                pnl_pct = PRICE_TP
                return pnl_pct, 'TP', i
        else:  # SHORT
            if high >= sl_price:
                pnl_pct = -PRICE_SL
                return pnl_pct, 'SL', i
            if low <= tp_price:
                pnl_pct = PRICE_TP
                return pnl_pct, 'TP', i
    
    # Time exit — close at last available price
    exit_price = float(candles[entry_idx + max_bars][4])
    if direction == "LONG":
        pnl_pct = ((exit_price - entry_price) / entry_price) * 100
    else:
        pnl_pct = ((entry_price - exit_price) / entry_price) * 100
    
    return pnl_pct, 'TIME', max_bars


def run_backtest(symbols, near_high_pct, min_score=MIN_SCORE):
    """Run backtest with a specific near-high filter threshold.
    
    Returns list of trade results.
    """
    trades = []
    
    for symbol in symbols:
        candles = get_klines(symbol, '1h', 1500)
        if len(candles) < 100:
            print(f"  ⚠️ {symbol}: only {len(candles)} candles, skipping")
            continue
        
        # Walk through candles bar-by-bar (start from bar 50 for indicator warmup)
        # Use a cooldown: 2 bars between signals for same symbol (like Neko's 2h cooldown)
        last_trade_bar = -10
        
        for idx in range(50, len(candles) - 49):  # Leave 49 bars for trade simulation
            if idx - last_trade_bar < 2:  # Cooldown
                continue
            
            # Determine direction from recent price action
            closes = [float(c[4]) for c in candles[:idx + 1]]
            price_change_24h = ((closes[-1] - closes[-24]) / closes[-24]) * 100 if len(closes) >= 24 else 0
            
            # Check both directions
            for direction in ["LONG", "SHORT"]:
                if direction == "LONG" and price_change_24h < 0:
                    continue  # Scanner uses price_change direction
                if direction == "SHORT" and price_change_24h >= 0:
                    continue
                
                indicators = score_signal(candles, idx, direction)
                if not indicators:
                    continue
                
                if indicators['score'] < min_score:
                    continue
                
                if not passes_filters(candles, idx, direction, indicators, near_high_pct):
                    continue
                
                # Signal generated — simulate trade
                pnl_pct, exit_reason, bars_held = simulate_trade(candles, idx, direction)
                
                trades.append({
                    'symbol': symbol,
                    'direction': direction,
                    'entry_bar': idx,
                    'pnl_pct': pnl_pct,
                    'exit_reason': exit_reason,
                    'bars_held': bars_held,
                    'score': indicators['score'],
                    'rsi': indicators['rsi'],
                    'adx': indicators['adx'],
                    'chop': indicators['chop'],
                    'fisher': indicators['fisher'],
                    'ema_position': indicators['ema_position'],
                })
                
                last_trade_bar = idx
                break  # One trade per bar
        
        time.sleep(0.1)  # Rate limit
    
    return trades


def analyze_results(trades, label=""):
    """Calculate and print trade statistics."""
    if not trades:
        print(f"\n{'='*60}")
        print(f"📊 {label or 'RESULTS'} — NO TRADES")
        print(f"{'='*60}")
        return {}
    
    wins = [t for t in trades if t['pnl_pct'] > 0]
    losses = [t for t in trades if t['pnl_pct'] <= 0]
    
    total = len(trades)
    num_wins = len(wins)
    num_losses = len(losses)
    win_rate = num_wins / total * 100 if total > 0 else 0
    
    gross_profit = sum(t['pnl_pct'] for t in wins) if wins else 0
    gross_loss = abs(sum(t['pnl_pct'] for t in losses)) if losses else 0
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else (999 if gross_profit > 0 else 0)
    
    net_pnl = sum(t['pnl_pct'] for t in trades)
    avg_win = sum(t['pnl_pct'] for t in wins) / num_wins if wins else 0
    avg_loss = sum(t['pnl_pct'] for t in losses) / num_losses if losses else 0
    
    # Exit reasons
    sl_count = len([t for t in trades if t['exit_reason'] == 'SL'])
    tp_count = len([t for t in trades if t['exit_reason'] == 'TP'])
    time_count = len([t for t in trades if t['exit_reason'] == 'TIME'])
    
    # Average score of winning vs losing trades
    avg_win_score = sum(t['score'] for t in wins) / num_wins if wins else 0
    avg_loss_score = sum(t['score'] for t in losses) / num_losses if losses else 0
    
    stats = {
        'total': total, 'wins': num_wins, 'losses': num_losses,
        'win_rate': win_rate, 'net_pnl': net_pnl,
        'profit_factor': profit_factor,
        'avg_win': avg_win, 'avg_loss': avg_loss,
        'sl_count': sl_count, 'tp_count': tp_count, 'time_count': time_count,
        'avg_win_score': avg_win_score, 'avg_loss_score': avg_loss_score,
    }
    
    print(f"\n{'='*60}")
    print(f"📊 {label or 'RESULTS'}")
    print(f"{'='*60}")
    print(f"  Total Trades:    {total}")
    print(f"  Win Rate:        {win_rate:.1f}% ({num_wins}W / {num_losses}L)")
    print(f"  Net PNL:         {net_pnl:+.1f}% (sum of all trade %)")
    print(f"  Profit Factor:   {profit_factor:.2f} {'✅' if profit_factor > 1.5 else '⚠️' if profit_factor > 1.0 else '❌'}")
    print(f"  Avg Win:         {avg_win:+.1f}%")
    print(f"  Avg Loss:        {avg_loss:+.1f}%")
    print(f"  Exits:           SL={sl_count} TP={tp_count} TIME={time_count}")
    print(f"  Avg Score (W/L): {avg_win_score:.1f} / {avg_loss_score:.1f}")
    
    return stats


def main():
    parser = argparse.ArgumentParser(description='Near-High Filter Backtest for Neko')
    parser.add_argument('--symbols', type=int, default=30, help='Number of top symbols to test (default: 30)')
    parser.add_argument('--days', type=int, default=60, help='Approximate days of data (default: 60)')
    parser.add_argument('--min-score', type=int, default=4, help='Minimum score threshold (default: 4)')
    args = parser.parse_args()
    
    print("🐱 NEKO NEAR-HIGH FILTER BACKTEST")
    print(f"   Symbols: top {args.symbols} by volume")
    print(f"   Data: ~{args.days} days of 1h candles")
    print(f"   SL: {PRICE_SL}% | TP: {PRICE_TP}% | Min Score: {args.min_score}")
    print()
    
    # Get symbols
    print("📡 Fetching top symbols...")
    symbols = get_top_symbols(args.symbols)
    print(f"   Got {len(symbols)} symbols: {', '.join(symbols[:10])}...")
    print()
    
    # Test different thresholds
    thresholds = [0, 2, 4, 6]
    all_results = {}
    
    for threshold in thresholds:
        label = f"Near-High Filter: {threshold}%" if threshold > 0 else "No Near-High Filter (0%)"
        print(f"\n🔄 Running backtest: {label}...")
        
        trades = run_backtest(symbols, threshold, args.min_score)
        stats = analyze_results(trades, label)
        all_results[threshold] = stats
        
        time.sleep(1)  # Brief pause between runs
    
    # === COMPARISON TABLE ===
    print(f"\n\n{'='*70}")
    print("📊 COMPARISON: NEAR-HIGH FILTER THRESHOLDS")
    print(f"{'='*70}")
    print(f"{'Threshold':<15} {'Trades':>8} {'Win%':>8} {'Net PNL':>10} {'PF':>8} {'SL%':>8} {'TP%':>8}")
    print("-" * 70)
    
    for thresh in thresholds:
        s = all_results.get(thresh, {})
        if not s:
            continue
        
        total = s.get('total', 0)
        sl_pct = s.get('sl_count', 0) / total * 100 if total > 0 else 0
        tp_pct = s.get('tp_count', 0) / total * 100 if total > 0 else 0
        
        label = f"{thresh}%" if thresh > 0 else "OFF"
        print(f"  {label:<13} {total:>8} {s.get('win_rate', 0):>7.1f}% {s.get('net_pnl', 0):>+9.1f}% {s.get('profit_factor', 0):>7.2f} {sl_pct:>7.1f}% {tp_pct:>7.1f}%")
    
    print("-" * 70)
    
    # Recommendation
    best_pf = max(thresholds, key=lambda t: all_results.get(t, {}).get('profit_factor', 0))
    best_wr = max(thresholds, key=lambda t: all_results.get(t, {}).get('win_rate', 0))
    
    print(f"\n💡 RECOMMENDATION:")
    print(f"   Best Profit Factor:  {best_pf}% filter (PF={all_results[best_pf].get('profit_factor', 0):.2f})")
    print(f"   Best Win Rate:       {best_wr}% filter (WR={all_results[best_wr].get('win_rate', 0):.1f}%)")
    
    if best_pf == best_wr:
        print(f"\n   ✅ Clear winner: {best_pf}% near-high filter")
    else:
        tradeoff_4 = all_results.get(4, {})
        tradeoff_0 = all_results.get(0, {})
        if tradeoff_4 and tradeoff_0:
            wr_diff = tradeoff_4.get('win_rate', 0) - tradeoff_0.get('win_rate', 0)
            trade_diff = tradeoff_0.get('total', 0) - tradeoff_4.get('total', 0)
            print(f"\n   ⚖️ Tradeoff with 4% filter:")
            print(f"      +{wr_diff:.1f}% win rate improvement")
            print(f"      -{trade_diff} fewer trades (opportunity cost)")
    
    # Save results
    output_file = os.path.expanduser('~/workspace/neko-futures-trader/scripts/backtest_results.json')
    with open(output_file, 'w') as f:
        json.dump({
            'config': {'sl': PRICE_SL, 'tp': PRICE_TP, 'min_score': args.min_score, 'symbols': args.symbols},
            'results': {str(k): v for k, v in all_results.items()},
            'run_at': datetime.now().isoformat(),
        }, f, indent=2)
    print(f"\n💾 Results saved to: {output_file}")


if __name__ == "__main__":
    main()
