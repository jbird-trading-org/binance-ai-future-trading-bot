#!/usr/bin/env python3
"""
Comprehensive Daily Trading Evaluation
Includes: Winrate, R:R, Expectancy, Trade Analysis, Recommendations
"""
import requests, hmac, hashlib, time, os, json
from datetime import datetime
from collections import defaultdict

# Load env
for line in open('/root/.openclaw/workspace/neko-futures-trader/.env'):
    line = line.strip()
    if line and '=' in line and not line.startswith('#'):
        k, v = line.split('=', 1)
        os.environ[k] = v

API_KEY = os.environ.get('BINANCE_API_KEY')
SECRET = os.environ.get('BINANCE_SECRET')

def get_sig(params):
    return hmac.new(SECRET.encode(), params.encode(), hashlib.sha256).hexdigest()

def get_positions():
    ts = int(time.time() * 1000)
    params = f'timestamp={ts}'
    sig = get_sig(params)
    r = requests.get(f'https://fapi.binance.com/fapi/v2/positionRisk?{params}&signature={sig}',
                     headers={'X-MBX-APIKEY': API_KEY}, timeout=15)
    return [p for p in r.json() if float(p.get('positionAmt', 0)) != 0]

def get_balance():
    ts = int(time.time() * 1000)
    params = f'timestamp={ts}'
    sig = get_sig(params)
    r = requests.get(f'https://fapi.binance.com/fapi/v3/account?{params}&signature={sig}',
                    headers={'X-MBX-APIKEY': API_KEY}, timeout=15)
    data = r.json()
    return float(data.get('totalMarginBalance', 0)), float(data.get('totalMaintMargin', 0))

def get_trade_history(days=90):
    all_trades = []
    for d in [30, 60, 90]:
        ts = int(time.time() * 1000)
        start_time = int((time.time() - d*24*60*60) * 1000)
        params = f'timestamp={ts}&startTime={start_time}&limit=100'
        sig = get_sig(params)
        r = requests.get(f'https://fapi.binance.com/fapi/v1/income?{params}&signature={sig}',
                        headers={'X-MBX-APIKEY': API_KEY}, timeout=15)
        data = r.json()
        all_trades.extend(data)
        if len(data) < 100:
            break
    return [t for t in all_trades if t.get('incomeType') == 'REALIZED_PNL']

def analyze_trades(trades):
    if not trades:
        return {}
    
    wins = [t for t in trades if float(t.get('income', 0)) > 0]
    losses = [t for t in trades if float(t.get('income', 0)) < 0]
    total_pnl = sum(float(t.get('income', 0)) for t in trades)
    
    avg_win = sum(float(t.get('income', 0)) for t in wins) / len(wins) if wins else 0
    avg_loss = abs(sum(float(t.get('income', 0)) for t in losses) / len(losses)) if losses else 0
    
    winrate = len(wins) / len(trades) * 100 if trades else 0
    
    # R:R ratio
    rr = avg_win / avg_loss if avg_loss > 0 else 0
    
    # Expectancy per trade
    expectancy = (winrate/100 * avg_win) - ((1 - winrate/100) * avg_loss)
    
    # Break even winrate
    be_wr = (avg_loss / (avg_win + avg_loss) * 100) if (avg_win + avg_loss) > 0 else 50
    
    # Per symbol analysis
    by_symbol = defaultdict(list)
    for t in trades:
        by_symbol[t['symbol']].append(float(t.get('income', 0)))
    
    symbol_stats = {}
    for sym,pnls in by_symbol.items():
        w = len([p for p in pnls if p > 0])
        l = len([p for p in pnls if p < 0])
        symbol_stats[sym] = {
            'trades': len(pnls),
            'pnl': sum(pnls),
            'wins': w,
            'losses': l,
            'winrate': w/len(pnls)*100 if pnls else 0,
            'avg_win': sum(p for p in pnls if p>0)/w if w else 0,
            'avg_loss': abs(sum(p for p in pnls if p<0)/l) if l else 0
        }
    
    # Best and worst trades
    sorted_trades = sorted(trades, key=lambda x: float(x.get('income', 0)), reverse=True)
    best_trades = sorted_trades[:3]
    worst_trades = sorted_trades[-3:]
    
    return {
        'total': len(trades),
        'wins': len(wins),
        'losses': len(losses),
        'winrate': winrate,
        'total_pnl': total_pnl,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'rr': rr,
        'expectancy': expectancy,
        'be_wr': be_wr,
        'symbol_stats': symbol_stats,
        'best_trades': best_trades,
        'worst_trades': worst_trades
    }

def generate_recommendations(stats, positions, balance, margin):
    recs = []
    issues = []
    
    # Winrate check
    if stats['winrate'] < 50:
        issues.append(f"⚠️ Winrate {stats['winrate']:.1f}% < 50%")
        recs.append("• Tambah filter entry - kurang selective")
        recs.append("• Cek RSI filter - reject overbought/oversold")
    
    # R:R check
    if stats['rr'] < 1:
        issues.append(f"⚠️ R:R = 1:{stats['rr']:.2f} < 1:1 (loss > win)")
        recs.append("• Perlebar TP atau persempit SL")
        recs.append("• Current: TP = 5x ATR, SL = 2.5x ATR")
        recs.append("• Rekomendasi: TP = 6x ATR, SL = 2x ATR")
    
    # Overtrading check
    if stats['total'] > 50:
        issues.append(f"⚠️ {stats['total']} trades - possible overtrading")
        recs.append("• Kurangi sinyal - lebih selective")
    
    # Symbol blacklist check
    bad_symbols = []
    for sym, s in stats['symbol_stats'].items():
        if s['pnl'] < -2:  # Lost more than $2
            bad_symbols.append(sym)
            recs.append(f"• Blacklist {sym} - {s['trades']} trades, ${s['pnl']:.2f} loss")
    
    # Best performer
    best_sym = max(stats['symbol_stats'].items(), key=lambda x: x[1]['pnl'])
    if best_sym[1]['pnl'] > 0:
        recs.append(f"• Fokus ke {best_sym[0]} pattern - +${best_sym[1]['pnl']:.2f}")
    
    # Margin check
    margin_pct = (margin / balance * 100) if balance > 0 else 0
    if margin_pct > 25:
        issues.append(f"⚠️ Margin {margin_pct:.1f}% > 25%")
        recs.append("• Kurangi posisi atau close yang loss dulu")
    
    # Current positions analysis
    if positions:
        open_pnl = sum(float(p.get('unRealizedProfit', 0)) for p in positions)
        recs.append(f"• {len(positions)} posisi open, PnL: ${open_pnl:+.2f}")
        
        for p in positions:
            pnl = float(p.get('unRealizedProfit', 0))
            if pnl < -1:
                recs.append(f"  - {p['symbol']}: ${pnl:.2f} - consider cut")
    
    return issues, recs

def send_telegram(text):
    try:
        bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
        channel = os.environ.get('TELEGRAM_CHANNEL')
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        requests.post(url, json={"chat_id": channel, "text": text, "parse_mode": "Markdown"}, timeout=10)
    except Exception as e:
        print(f"Telegram error: {e}")

def main():
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    print(f"\n{'='*60}")
    print(f"📊 COMPREHENSIVE DAILY EVALUATION - {now}")
    print(f"{'='*60}")
    
    # Get data
    positions = get_positions()
    balance, margin = get_balance()
    trades = get_trade_history(90)
    
    print(f"\n💰 Balance: ${balance:.2f}")
    print(f"📊 Open Positions: {len(positions)}")
    
    # Calculate open PnL
    open_pnl = sum(float(p.get('unRealizedProfit', 0)) for p in positions)
    print(f"📈 Open PnL: ${open_pnl:+.2f}")
    print(f"📏 Margin Used: ${margin:.2f} ({margin/balance*100:.1f}%)")
    
    # Analyze trades
    stats = analyze_trades(trades)
    
    print(f"\n{'='*60}")
    print(f"📜 TRADE HISTORY ANALYSIS (90 Days)")
    print(f"{'='*60}")
    print(f"Total Trades: {stats['total']}")
    print(f"Wins: {stats['wins']} 🟢 | Losses: {stats['losses']} 🔴")
    print(f"Winrate: {stats['winrate']:.1f}%")
    print(f"Closed PnL: ${stats['total_pnl']:+.2f}")
    print(f"")
    print(f"Average Win: ${stats['avg_win']:.2f}")
    print(f"Average Loss: ${stats['avg_loss']:.2f}")
    print(f"R:R Ratio: 1:{stats['rr']:.2f}")
    print(f"Expectancy/trade: ${stats['expectancy']:.2f}")
    print(f"Break-even Winrate: {stats['be_wr']:.1f}%")
    
    # Per symbol
    print(f"\n📊 PER SYMBOL (Top 5 by PnL):")
    sorted_sym = sorted(stats['symbol_stats'].items(), key=lambda x: x[1]['pnl'], reverse=True)
    for sym, s in sorted_sym[:5]:
        wr = s['winrate']
        wr_emoji = "🟢" if wr >= 50 else "🔴"
        print(f"  {sym}: {s['trades']} trades, ${s['pnl']:+.2f} ({wr_emoji}{wr:.0f}%)")
    
    # Worst symbols
    print(f"\n⚠️ WORST PERFORMERS:")
    for sym, s in sorted_sym[-3:]:
        if s['pnl'] < 0:
            print(f"  {sym}: {s['trades']} trades, ${s['pnl']:.2f} (W:{s['wins']} L:{s['losses']})")
    
    # Recommendations
    issues, recs = generate_recommendations(stats, positions, balance, margin)
    
    print(f"\n{'='*60}")
    print(f"🎯 ISSUES & RECOMMENDATIONS")
    print(f"{'='*60}")
    for issue in issues:
        print(issue)
    print("")
    for rec in recs:
        print(rec)
    
    # Grade
    grade = "🟢 EXCELLENT" if stats['winrate'] >= 60 and stats['rr'] >= 1.5 else \
             "🟡 GOOD" if stats['winrate'] >= 50 and stats['rr'] >= 1 else \
             "🔴 NEEDS WORK"
    
    print(f"\n📊 Grade: {grade}")
    
    # Build Telegram message
    msg = f"""📊 *Daily Trading Eval* - {now}

💰 *Balance:* ${balance:.2f}
📊 *Open:* {len(positions)} positions (${open_pnl:+.2f})
📏 *Margin:* ${margin:.2f} ({margin/balance*100:.1f}%)

*═══════════════════════════*
📜 *90 DAY HISTORY*
*═══════════════════════════*
Trades: {stats['total']} (W:{stats['wins']} L:{stats['losses']})
Winrate: {stats['winrate']:.1f}%
Closed PnL: ${stats['total_pnl']:+.2f}

Avg Win: ${stats['avg_win']:.2f} | Avg Loss: ${stats['avg_loss']:.2f}
R:R: 1:{stats['rr']:.2f} | Expectancy: ${stats['expectancy']:.2f}/trade
Break-even WR: {stats['be_wr']:.1f}%

*═══════════════════════════*
🏆 TOP PERFORMERS
*═══════════════════════════*"""
    
    for sym, s in sorted_sym[:3]:
        if s['pnl'] > 0:
            msg += f"\n{sym}: +${s['pnl']:.2f} ({s['winrate']:.0f}% WR)"
    
    msg += f"""

*═══════════════════════════*
⚠️ ISSUES
*═══════════════════════════*"""
    
    for issue in issues:
        msg += f"\n{issue}"
    
    msg += f"""

*═══════════════════════════*
🎯 RECOMMENDATIONS
*═══════════════════════════*"""
    
    for rec in recs:
        msg += f"\n{rec}"
    
    msg += f"""

*═══════════════════════════*
📊 GRADE: {grade}
*═══════════════════════════*"""
    
    send_telegram(msg)
    print(f"\n✅ Telegram sent")
    
    return stats

if __name__ == "__main__":
    main()
