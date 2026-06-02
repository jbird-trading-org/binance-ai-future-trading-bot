#!/usr/bin/env python3
"""
Neko Auto-Tuner v2 — Quality-focused, loss-aware
Analyzes trade history + rejection breakdown to find the RIGHT balance.
"""

import re
import os
import json
from collections import Counter
from datetime import datetime

LOG_PATH = "/root/workspace/neko-futures-trader/logs/scanner.log"
CONFIG_PATH = "/root/workspace/neko-futures-trader/config.py"
TRADES_PATH = "/root/workspace/neko-futures-trader/.trade_history.json"


def analyze_rejections(log_path, n_lines=3000):
    """Parse scanner log and count rejection reasons."""
    with open(log_path) as f:
        lines = f.readlines()[-n_lines:]
    
    rejections = Counter()
    for line in lines:
        m = re.search(r'\(([^)]+)\)\s*no signal', line)
        if m:
            reason = m.group(1)
            if 'macd_flat' in reason: rejections['macd_flat'] += 1
            elif 'chase_long' in reason or 'chase_short' in reason: rejections['chase'] += 1
            elif reason.startswith('ch='): rejections['price_change_low'] += 1
            elif 'score=' in reason: rejections['score'] += 1
            elif 'vol=' in reason: rejections['volume'] += 1
            elif 'red=' in reason: rejections['red_candles'] += 1
            elif 'ema_pos' in reason: rejections['ema_pos'] += 1
            elif 'trend_reject' in reason: rejections['ema_trend'] += 1
            elif 'dir_conflict' in reason: rejections['dir_conflict'] += 1
            elif 'rsi' in reason: rejections['rsi'] += 1
            elif 'momentum' in reason: rejections['momentum'] += 1
            elif 'range_pos' in reason: rejections['range_pos'] += 1
            elif 'green=' in reason: rejections['green_candles'] += 1
            elif 'near' in reason: rejections['near_hl'] += 1
            elif '4h=' in reason: rejections['4h_trend'] += 1
            elif 'hist=' in reason: rejections['macd_hist'] += 1
            elif 'btc_' in reason: rejections['btc_regime'] += 1
            else: rejections[reason] += 1
    return rejections


def analyze_trades(trades_path):
    """Analyze trade history for win/loss patterns."""
    if not os.path.exists(trades_path):
        return None
    with open(trades_path) as f:
        trades = json.load(f)
    
    if len(trades) < 5:
        return None
    
    wins = [t for t in trades if t['pnl'] > 0]
    losses = [t for t in trades if t['pnl'] < 0]
    
    if not wins or not losses:
        return None
    
    # Recent 20 trades
    recent = trades[-20:]
    r_wins = [t for t in recent if t['pnl'] > 0]
    r_losses = [t for t in recent if t['pnl'] < 0]
    
    # Signal characteristics of losers (where available)
    loss_scores = [t['signal'].get('score', 0) for t in losses if t.get('signal', {}).get('score', 0) > 0]
    win_scores = [t['signal'].get('score', 0) for t in wins if t.get('signal', {}).get('score', 0) > 0]
    
    return {
        'total_trades': len(trades),
        'win_rate': len(wins) / len(trades) * 100,
        'total_pnl': sum(t['pnl'] for t in trades),
        'avg_win': sum(t['pnl'] for t in wins) / len(wins),
        'avg_loss': sum(t['pnl'] for t in losses) / len(losses),
        'profit_factor': sum(t['pnl'] for t in wins) / abs(sum(t['pnl'] for t in losses)),
        'recent_wr': len(r_wins) / len(recent) * 100 if recent else 0,
        'recent_pnl': sum(t['pnl'] for t in recent),
        'loss_avg_score': sum(loss_scores) / len(loss_scores) if loss_scores else 0,
        'win_avg_score': sum(win_scores) / len(win_scores) if win_scores else 0,
        'loss_scores': loss_scores,
        'win_scores': win_scores,
    }


def read_config_val(config_path, key):
    """Read a single config value."""
    with open(config_path) as f:
        for line in f:
            if line.strip().startswith(key + ' ') or line.strip().startswith(key + '='):
                m = re.search(r'=\s*([\d.]+)', line)
                if m:
                    return float(m.group(1))
    return None


def write_config_change(config_path, key, new_val, comment=""):
    """Update a single config value in config.py."""
    with open(config_path) as f:
        lines = f.readlines()
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith(key + ' ') or stripped.startswith(key + '='):
            # Preserve indentation
            indent = line[:len(line) - len(line.lstrip())]
            new_line = f"{indent}{key} = {new_val}"
            if comment:
                new_line += f"  # {comment}"
            lines[i] = new_line + "\n"
            break
    
    with open(config_path, 'w') as f:
        f.writelines(lines)
    return True


def auto_tune():
    """Main auto-tuner: quality-focused adjustments."""
    print("🔧 Neko Auto-Tuner v2 — Quality-Focused")
    print("=" * 55)
    
    # === TRADE ANALYSIS ===
    trade_stats = analyze_trades(TRADES_PATH)
    if trade_stats:
        print(f"\n📊 Trade History ({trade_stats['total_trades']} trades):")
        print(f"  WR: {trade_stats['win_rate']:.0f}% | PNL: ${trade_stats['total_pnl']:+.2f}")
        print(f"  Avg Win: ${trade_stats['avg_win']:+.2f} | Avg Loss: ${trade_stats['avg_loss']:+.2f}")
        print(f"  Profit Factor: {trade_stats['profit_factor']:.2f}")
        print(f"  Recent WR (20): {trade_stats['recent_wr']:.0f}% | Recent PNL: ${trade_stats['recent_pnl']:+.2f}")
        if trade_stats['loss_avg_score']:
            print(f"  Loser avg score: {trade_stats['loss_avg_score']:.1f} | Winner avg score: {trade_stats['win_avg_score']:.1f}")
    
    # === REJECTION ANALYSIS ===
    rejections = analyze_rejections(LOG_PATH)
    total = sum(rejections.values())
    print(f"\n📊 Rejection Breakdown ({total} total):")
    for reason, count in rejections.most_common():
        pct = count * 100 / total if total > 0 else 0
        bar = "█" * int(pct / 2)
        print(f"  {reason:20s}: {count:4d} ({pct:4.0f}%) {bar}")
    
    # === DECISION LOGIC ===
    changes = []
    current_score = read_config_val(CONFIG_PATH, 'MIN_SCORE_NORMAL') or 7
    current_vol = read_config_val(CONFIG_PATH, 'MIN_VOLUME_RATIO') or 1.5
    current_chase = read_config_val(CONFIG_PATH, 'CHASE_LIMIT_CRYPTO') or 4.0
    
    # Rule 1: MIN_SCORE — NEVER go below 8 (2026-06-02: WR 57% + avg_loss>avg_win, need quality)
    # If score blocking > 20% AND WR > 65%, we can try 8. Otherwise keep at 9.
    score_pct = rejections.get('score', 0) * 100 / total if total > 0 else 0
    wr = trade_stats['recent_wr'] if trade_stats else 50
    
    if score_pct > 20 and wr > 65 and current_score > 8:
        changes.append(('MIN_SCORE_NORMAL', 8, f'Score blocking {score_pct:.0f}% + WR {wr:.0f}% OK'))
    elif score_pct < 5 and current_score < 9:
        changes.append(('MIN_SCORE_NORMAL', 9, f'Score not blocking ({score_pct:.0f}%) — raise for quality'))
    elif current_score < 8:
        changes.append(('MIN_SCORE_NORMAL', 8, f'Revert to safe floor (was {current_score})'))
    
    # Rule 2: VOLUME — floor at 1.0x, normal at 1.5x
    vol_pct = rejections.get('volume', 0) * 100 / total if total > 0 else 0
    if vol_pct > 20 and current_vol > 1.0:
        new_vol = max(current_vol - 0.2, 1.0)
        changes.append(('MIN_VOLUME_RATIO', new_vol, f'Volume blocking {vol_pct:.0f}%'))
    elif vol_pct < 5 and current_vol < 1.5:
        new_vol = min(current_vol + 0.2, 1.5)
        changes.append(('MIN_VOLUME_RATIO', new_vol, f'Volume not blocking — raise for quality'))
    elif current_vol < 1.0:
        changes.append(('MIN_VOLUME_RATIO', 1.0, f'Revert to floor (was {current_vol})'))
    
    # Rule 3: CHASE LIMIT — cap at 6%, floor at 4%
    chase_pct = rejections.get('chase', 0) * 100 / total if total > 0 else 0
    if chase_pct > 30 and current_chase < 6.0:
        new_chase = min(current_chase + 0.5, 6.0)
        changes.append(('CHASE_LIMIT_CRYPTO', new_chase, f'Chase blocking {chase_pct:.0f}%'))
    elif chase_pct < 10 and current_chase > 4.0:
        new_chase = max(current_chase - 0.5, 4.0)
        changes.append(('CHASE_LIMIT_CRYPTO', new_chase, f'Chase not blocking — tighten'))
    elif current_chase < 4.0:
        changes.append(('CHASE_LIMIT_CRYPTO', 4.0, f'Revert to floor (was {current_chase})'))
    
    # Rule 4: MACD FLAT — this is scanner.py, just report
    macd_pct = rejections.get('macd_flat', 0) * 100 / total if total > 0 else 0
    if macd_pct > 30:
        print(f"\n  ⚠️ MACD flat blocking {macd_pct:.0f}% — check scanner.py _macd_flat_threshold")
    
    # === APPLY ===
    if not changes:
        print(f"\n✅ Config is balanced — no changes needed.")
        return
    
    print(f"\n🔧 Applying {len(changes)} adjustments:")
    for key, val, desc in changes:
        old = read_config_val(CONFIG_PATH, key)
        print(f"  • {key}: {old} → {val} ({desc})")
        write_config_change(CONFIG_PATH, key, val, f"Auto-tuner v2: {desc}")
    
    print(f"\n⚠️ Restart scanner to apply: sudo systemctl restart neko-scanner.service")


if __name__ == "__main__":
    auto_tune()
