#!/usr/bin/env python3
"""
Trade Analysis — Correlate Indicator Scores with PNL

Reads .trade_history.json (with enriched signal data) and produces:
1. Which indicators correlate with winning trades
2. Score distribution: avg score of winners vs losers
3. Fisher/Taker/ADX effectiveness analysis
4. Recommendations for scoring system changes

Usage:
    python3 scripts/analyze_trades.py
    python3 scripts/analyze_trades.py --file /path/to/trade_history.json
"""

import os
import sys
import json
import argparse
from collections import defaultdict
from datetime import datetime

HISTORY_FILE = os.path.expanduser('~/workspace/neko-futures-trader/.trade_history.json')


def load_trades(filepath=None):
    """Load trade history."""
    path = filepath or HISTORY_FILE
    if not os.path.exists(path):
        print(f"❌ No trade history found at {path}")
        return []
    
    with open(path, 'r') as f:
        trades = json.load(f)
    
    return trades


def has_signal_data(trades):
    """Check if trades have enriched signal data."""
    if not trades:
        return False
    return 'signal' in trades[0]


def correlate_indicator_with_pnl(trades, indicator_key, bins=None):
    """Correlate a specific indicator value with PNL outcome.
    
    Returns dict with binned analysis.
    """
    if not has_signal_data(trades):
        return None
    
    # Extract indicator values and PNL
    data = []
    for t in trades:
        signal = t.get('signal', {})
        val = signal.get(indicator_key)
        pnl = t.get('pnl_pct', t.get('pnl', 0))
        if val is not None:
            data.append({'val': val, 'pnl': pnl, 'win': pnl > 0})
    
    if not data:
        return None
    
    if bins:
        # Bin the data
        binned = defaultdict(lambda: {'wins': 0, 'losses': 0, 'total_pnl': 0, 'count': 0})
        for d in data:
            for bin_name, (lo, hi) in bins.items():
                if lo <= d['val'] < hi:
                    binned[bin_name]['count'] += 1
                    binned[bin_name]['total_pnl'] += d['pnl']
                    if d['win']:
                        binned[bin_name]['wins'] += 1
                    else:
                        binned[bin_name]['losses'] += 1
                    break
        
        result = {}
        for bin_name, stats in binned.items():
            total = stats['count']
            if total > 0:
                result[bin_name] = {
                    'count': total,
                    'win_rate': stats['wins'] / total * 100,
                    'avg_pnl': stats['total_pnl'] / total,
                    'total_pnl': stats['total_pnl'],
                }
        return result
    
    # Continuous: split into high/low halves
    vals = [d['val'] for d in data]
    median = sorted(vals)[len(vals) // 2]
    
    high = [d for d in data if d['val'] >= median]
    low = [d for d in data if d['val'] < median]
    
    def stats(group):
        if not group:
            return {'count': 0, 'win_rate': 0, 'avg_pnl': 0}
        wins = sum(1 for d in group if d['win'])
        return {
            'count': len(group),
            'win_rate': wins / len(group) * 100,
            'avg_pnl': sum(d['pnl'] for d in group) / len(group),
        }
    
    return {
        'high': stats(high),
        'low': stats(low),
        'median': median,
    }


def analyze_basic(trades):
    """Basic trade statistics."""
    if not trades:
        return {}
    
    wins = [t for t in trades if t.get('pnl_pct', t.get('pnl', 0)) > 0]
    losses = [t for t in trades if t.get('pnl_pct', t.get('pnl', 0)) <= 0]
    
    total = len(trades)
    num_wins = len(wins)
    num_losses = len(losses)
    win_rate = num_wins / total * 100 if total > 0 else 0
    
    pnls = [t.get('pnl_pct', t.get('pnl', 0)) for t in trades]
    gross_profit = sum(p for p in pnls if p > 0)
    gross_loss = abs(sum(p for p in pnls if p <= 0))
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else 999
    
    avg_win = sum(t.get('pnl_pct', t.get('pnl', 0)) for t in wins) / num_wins if wins else 0
    avg_loss = sum(t.get('pnl_pct', t.get('pnl', 0)) for t in losses) / num_losses if losses else 0
    
    # By exit reason
    sl_trades = [t for t in trades if t.get('reason') == 'SL']
    tp_trades = [t for t in trades if t.get('reason') == 'TP']
    
    return {
        'total': total,
        'wins': num_wins,
        'losses': num_losses,
        'win_rate': win_rate,
        'net_pnl': sum(pnls),
        'profit_factor': profit_factor,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'sl_count': len(sl_trades),
        'tp_count': len(tp_trades),
        'sl_win_rate': len([t for t in sl_trades if t.get('pnl_pct', t.get('pnl', 0)) > 0]) / len(sl_trades) * 100 if sl_trades else 0,
        'tp_win_rate': len([t for t in tp_trades if t.get('pnl_pct', t.get('pnl', 0)) > 0]) / len(tp_trades) * 100 if tp_trades else 0,
    }


def analyze_fisher_effectiveness(trades):
    """Detailed Fisher Transform analysis — is it adding value?"""
    if not has_signal_data(trades):
        return None
    
    # Group by Fisher direction and magnitude
    groups = {
        'strong_bullish': [],  # fisher > 0.5
        'mild_bullish': [],    # 0 < fisher <= 0.5
        'mild_bearish': [],    # -0.5 <= fisher < 0
        'strong_bearish': [],  # fisher < -0.5
        'zero': [],            # fisher ≈ 0
    }
    
    for t in trades:
        signal = t.get('signal', {})
        fisher = signal.get('fisher', 0)
        pnl = t.get('pnl_pct', t.get('pnl', 0))
        
        if fisher > 0.5:
            groups['strong_bullish'].append(pnl)
        elif fisher > 0:
            groups['mild_bullish'].append(pnl)
        elif fisher < -0.5:
            groups['strong_bearish'].append(pnl)
        elif fisher < 0:
            groups['mild_bearish'].append(pnl)
        else:
            groups['zero'].append(pnl)
    
    result = {}
    for name, pnls in groups.items():
        if pnls:
            wins = sum(1 for p in pnls if p > 0)
            result[name] = {
                'count': len(pnls),
                'win_rate': wins / len(pnls) * 100,
                'avg_pnl': sum(pnls) / len(pnls),
            }
    
    return result


def analyze_taker_effectiveness(trades):
    """Taker Buy/Sell Ratio analysis — does it predict direction?"""
    if not has_signal_data(trades):
        return None
    
    bullish_taker = []  # ratio > 1.05
    bearish_taker = []  # ratio < 0.95
    neutral_taker = []  # 0.95 <= ratio <= 1.05
    
    for t in trades:
        signal = t.get('signal', {})
        taker = signal.get('taker_ratio', 1.0)
        pnl = t.get('pnl_pct', t.get('pnl', 0))
        
        if taker > 1.05:
            bullish_taker.append(pnl)
        elif taker < 0.95:
            bearish_taker.append(pnl)
        else:
            neutral_taker.append(pnl)
    
    def stats(pnls):
        if not pnls:
            return {'count': 0, 'win_rate': 0, 'avg_pnl': 0}
        wins = sum(1 for p in pnls if p > 0)
        return {'count': len(pnls), 'win_rate': wins / len(pnls) * 100, 'avg_pnl': sum(pnls) / len(pnls)}
    
    return {
        'bullish (>1.05)': stats(bullish_taker),
        'bearish (<0.95)': stats(bearish_taker),
        'neutral': stats(neutral_taker),
    }


def analyze_score_correlation(trades):
    """Does higher score = better PNL?"""
    if not has_signal_data(trades):
        return None
    
    by_score = defaultdict(list)
    for t in trades:
        signal = t.get('signal', {})
        score = signal.get('score', 0)
        pnl = t.get('pnl_pct', t.get('pnl', 0))
        by_score[score].append(pnl)
    
    result = {}
    for score in sorted(by_score.keys()):
        pnls = by_score[score]
        wins = sum(1 for p in pnls if p > 0)
        result[score] = {
            'count': len(pnls),
            'win_rate': wins / len(pnls) * 100 if pnls else 0,
            'avg_pnl': sum(pnls) / len(pnls) if pnls else 0,
            'total_pnl': sum(pnls),
        }
    
    return result


def print_header(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def main():
    parser = argparse.ArgumentParser(description='Analyze Neko trade history')
    parser.add_argument('--file', type=str, default=None, help='Path to trade_history.json')
    args = parser.parse_args()
    
    trades = load_trades(args.file)
    
    if not trades:
        print("❌ No trades to analyze. Wait for some trades to close first.")
        print("   Trades are logged automatically when SL/TP hits.")
        sys.exit(1)
    
    has_signals = has_signal_data(trades)
    
    print("🐱 NEKO TRADE ANALYSIS")
    print(f"   Total trades: {len(trades)}")
    print(f"   Signal data:  {'✅ Enriched' if has_signals else '❌ Missing (need new trades)'}")
    
    # === BASIC STATS ===
    stats = analyze_basic(trades)
    print_header("BASIC STATS")
    print(f"  Total Trades:    {stats['total']}")
    print(f"  Win Rate:        {stats['win_rate']:.1f}% ({stats['wins']}W / {stats['losses']}L)")
    print(f"  Net PNL:         {stats['net_pnl']:+.2f}")
    print(f"  Profit Factor:   {stats['profit_factor']:.2f}")
    print(f"  Avg Win:         {stats['avg_win']:+.2f}")
    print(f"  Avg Loss:        {stats['avg_loss']:+.2f}")
    print(f"  SL Hits:         {stats['sl_count']} (WR: {stats['sl_win_rate']:.0f}%)")
    print(f"  TP Hits:         {stats['tp_count']} (WR: {stats['tp_win_rate']:.0f}%)")
    
    if not has_signals:
        print("\n⚠️ No signal data in trade history. Trades recorded before the update won't have indicator data.")
        print("   New trades will include signal scores. Run this again after 10+ new trades.")
        return
    
    # === SCORE CORRELATION ===
    score_corr = analyze_score_correlation(trades)
    if score_corr:
        print_header("SCORE vs PNL CORRELATION")
        print(f"  {'Score':<8} {'Trades':>8} {'Win%':>8} {'Avg PNL':>10} {'Total PNL':>10}")
        print("  " + "-" * 48)
        for score, data in sorted(score_corr.items()):
            print(f"  {score:<8} {data['count']:>8} {data['win_rate']:>7.1f}% {data['avg_pnl']:>+9.2f} {data['total_pnl']:>+9.2f}")
    
    # === FISHER ANALYSIS ===
    fisher = analyze_fisher_effectiveness(trades)
    if fisher:
        print_header("FISHER TRANSFORM EFFECTIVENESS")
        print(f"  {'Fisher State':<20} {'Trades':>8} {'Win%':>8} {'Avg PNL':>10}")
        print("  " + "-" * 50)
        for name, data in fisher.items():
            print(f"  {name:<20} {data['count']:>8} {data['win_rate']:>7.1f}% {data['avg_pnl']:>+9.2f}")
        
        # Recommendation
        bull = fisher.get('strong_bullish', {})
        bear = fisher.get('strong_bearish', {})
        if bull and bear:
            diff = bull.get('win_rate', 0) - bear.get('win_rate', 0)
            if abs(diff) < 5:
                print(f"\n  ⚠️ Fisher signal: weak correlation ({diff:+.1f}% WR difference)")
                print(f"     Consider removing Fisher from scoring (saves complexity)")
            else:
                print(f"\n  ✅ Fisher signal: useful ({diff:+.1f}% WR difference)")
    
    # === TAKER ANALYSIS ===
    taker = analyze_taker_effectiveness(trades)
    if taker:
        print_header("TAKER RATIO EFFECTIVENESS")
        print(f"  {'Taker State':<20} {'Trades':>8} {'Win%':>8} {'Avg PNL':>10}")
        print("  " + "-" * 50)
        for name, data in taker.items():
            print(f"  {name:<20} {data['count']:>8} {data['win_rate']:>7.1f}% {data['avg_pnl']:>+9.2f}")
        
        bull = taker.get('bullish (>1.05)', {})
        bear = taker.get('bearish (<0.95)', {})
        if bull and bear:
            diff = bull.get('win_rate', 0) - bear.get('win_rate', 0)
            if abs(diff) < 5:
                print(f"\n  ⚠️ Taker signal: weak correlation ({diff:+.1f}% WR difference)")
            else:
                print(f"\n  ✅ Taker signal: useful ({diff:+.1f}% WR difference)")
    
    # === INDICATOR BINNED ANALYSIS ===
    indicators = ['rsi', 'adx', 'chop', 'ema_position', 'vol_ratio', 'stoch_rsi_k']
    rsi_bins = {'oversold (<30)': (0, 30), 'neutral (30-50)': (30, 50), 'neutral (50-70)': (50, 70), 'overbought (>70)': (70, 101)}
    adx_bins = {'weak (<20)': (0, 20), 'moderate (20-25)': (20, 25), 'strong (>25)': (25, 101)}
    chop_bins = {'trending (<40)': (0, 40), 'neutral (40-60)': (40, 60), 'choppy (>60)': (60, 101)}
    ema_bins = {'low (<30)': (0, 30), 'mid (30-50)': (30, 50), 'high (50-70)': (50, 70), 'extended (>70)': (70, 101)}
    vol_bins = {'normal (<3x)': (0, 3), 'spike (3-5x)': (3, 5), 'mega (>5x)': (5, 100)}
    stoch_bins = {'oversold (<20)': (0, 20), 'low (20-40)': (20, 40), 'mid (40-60)': (40, 60), 'high (60-80)': (60, 80), 'overbought (>80)': (80, 101)}
    
    all_bins = {
        'rsi': rsi_bins, 'adx': adx_bins, 'chop': chop_bins,
        'ema_position': ema_bins, 'vol_ratio': vol_bins, 'stoch_rsi_k': stoch_bins,
    }
    
    for ind in indicators:
        bins = all_bins.get(ind)
        result = correlate_indicator_with_pnl(trades, ind, bins)
        if result:
            print_header(f"{ind.upper()} vs PNL (binned)")
            print(f"  {'Bin':<25} {'Trades':>8} {'Win%':>8} {'Avg PNL':>10}")
            print("  " + "-" * 55)
            for bin_name, data in result.items():
                print(f"  {bin_name:<25} {data['count']:>8} {data['win_rate']:>7.1f}% {data['avg_pnl']:>+9.2f}")
    
    # === RECOMMENDATIONS ===
    print_header("RECOMMENDATIONS")
    
    if score_corr:
        # Check if score matters
        scores = sorted(score_corr.keys())
        if len(scores) >= 2:
            low_scores = [s for s in scores if s <= 5]
            high_scores = [s for s in scores if s > 5]
            
            if low_scores and high_scores:
                low_wr = sum(score_corr[s]['win_rate'] * score_corr[s]['count'] for s in low_scores) / sum(score_corr[s]['count'] for s in low_scores)
                high_wr = sum(score_corr[s]['win_rate'] * score_corr[s]['count'] for s in high_scores) / sum(score_corr[s]['count'] for s in high_scores)
                
                print(f"  Score ≤5 avg WR: {low_wr:.1f}%")
                print(f"  Score >5 avg WR: {high_wr:.1f}%")
                
                if high_wr - low_wr > 10:
                    print(f"  ✅ Score threshold matters! Consider raising MIN_SCORE to {min(high_scores)}")
                elif high_wr - low_wr < 0:
                    print(f"  ⚠️ Higher scores don't correlate with better results")
                    print(f"     The scoring system may need recalibration")
                else:
                    print(f"  ➡️ Modest correlation ({high_wr - low_wr:+.1f}%)")
    
    # Fisher/Taker removal check
    if fisher:
        bull = fisher.get('strong_bullish', {})
        bear = fisher.get('strong_bearish', {})
        neutral = fisher.get('zero', {})
        if bull and bear and neutral:
            bull_wr = bull.get('win_rate', 0)
            bear_wr = bear.get('win_rate', 0)
            neutral_wr = neutral.get('win_rate', 0)
            if abs(bull_wr - bear_wr) < 5 and abs(bull_wr - neutral_wr) < 5:
                print(f"\n  🗑️ Fisher Transform: Consider removing (max {abs(bull_wr - bear_wr):.1f}% WR difference)")
                print(f"     Would reduce max score from 19 to 17 without impact")
    
    if taker:
        bull = taker.get('bullish (>1.05)', {})
        bear = taker.get('bearish (<0.95)', {})
        if bull and bear:
            bull_wr = bull.get('win_rate', 0)
            bear_wr = bear.get('win_rate', 0)
            if abs(bull_wr - bear_wr) < 5:
                print(f"\n  🗑️ Taker Ratio: Consider removing (max {abs(bull_wr - bear_wr):.1f}% WR difference)")
                print(f"     API call rate reduction — faster scanning")


if __name__ == "__main__":
    main()
