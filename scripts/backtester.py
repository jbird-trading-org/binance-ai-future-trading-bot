#!/usr/bin/env python3
"""
Neko Futures Trader - Backtester v2
Monte Carlo Simulation + Real Metrics from Binance API

Auto-updated: Fetches real trade data from Binance on each run.
"""

import os
import math
import random
import json
import time
from datetime import datetime, timedelta
from typing import List, Dict, Tuple

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    import urllib.request
    import urllib.parse
    HAS_REQUESTS = False
    import json

# ============ CONFIG ============
BINANCE_API_KEY = os.getenv('BINANCE_API_KEY', '')
BINANCE_SECRET = os.getenv('BINANCE_SECRET', '')

# Trading params
MAX_POSITIONS = 5
CURRENT_RR = 3.0  # 1:3 R:R ratio
INITIAL_BALANCE = 300.0

# Monte Carlo params
N_SIMULATIONS = 5000
TRADES_PER_SIM = 100

# ============ BINANCE SIGNED API ============
def create_signature(query_string: str) -> str:
    """Create HMAC SHA256 signature."""
    import hmac
    import hashlib
    return hmac.new(
        BINANCE_SECRET.encode('utf-8'),
        query_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

def binance_signed_get(endpoint: str, params: dict = None) -> dict:
    """Make signed GET request to Binance."""
    if not BINANCE_API_KEY or not BINANCE_SECRET:
        print("⚠️ API keys not configured")
        return None
    
    ts = int(time.time() * 1000)
    params = params or {}
    params['timestamp'] = ts
    
    query = '&'.join([f"{k}={v}" for k, v in params.items()])
    signature = create_signature(query)
    query += f"&signature={signature}"
    
    url = f"https://fapi.binance.com{endpoint}?{query}"
    headers = {'X-MBX-APIKEY': BINANCE_API_KEY}
    
    try:
        if HAS_REQUESTS:
            r = requests.get(url, headers=headers, timeout=10)
        else:
            req = urllib.request.Request(url, headers=headers)
            r = urllib.request.urlopen(req, timeout=10)
            r = type('Response', (), {'json': lambda: json.loads(r.read()), 'status_code': 200})()
        
        if r.status_code == 200:
            return r.json()
        else:
            print(f"⚠️ API error: {r.status_code}")
            return None
    except Exception as e:
        print(f"⚠️ Request failed: {e}")
        return None

def get_income_history(days: int = 90) -> List[Dict]:
    """Fetch REALIZED_PNL from Binance for given days."""
    end_time = int(time.time() * 1000)
    start_time = int((time.time() - days * 24 * 60 * 60) * 1000)
    
    all_trades = []
    
    # Fetch in batches (Binance limit is 100 per request)
    params = {
        'startTime': start_time,
        'endTime': end_time,
        'limit': 100
    }
    
    while True:
        data = binance_signed_get('/fapi/v1/income', params)
        if not data or not isinstance(data, list):
            break
        
        realized = [t for t in data if t.get('incomeType') == 'REALIZED_PNL']
        all_trades.extend(realized)
        
        if len(data) < 100:
            break
        
        # Next batch: use last trade's time + 1ms
        params['startTime'] = int(data[-1].get('time', 0)) + 1
    
    return all_trades

def calculate_real_stats(trades: List[Dict]) -> dict:
    """Calculate real winrate and stats from trades."""
    if not trades:
        return {
            'winrate': 0.42,
            'avg_win': 2.0,
            'avg_loss': 3.0,
            'total_pnl': 0,
            'wins': 0,
            'losses': 0,
            'total_trades': 0
        }
    
    wins = [t for t in trades if float(t.get('income', 0)) > 0]
    losses = [t for t in trades if float(t.get('income', 0)) <= 0]
    
    win_amt = [float(t.get('income', 0)) for t in wins]
    loss_amt = [abs(float(t.get('income', 0))) for t in losses]
    
    return {
        'winrate': len(wins) / len(trades) if trades else 0,
        'avg_win': sum(win_amt) / len(win_amt) if win_amt else 0,
        'avg_loss': sum(loss_amt) / len(loss_amt) if loss_amt else 0,
        'total_pnl': sum([float(t.get('income', 0)) for t in trades]),
        'wins': len(wins),
        'losses': len(losses),
        'total_trades': len(trades)
    }

# ============ MONTE CARLO ============
def monte_carlo_simulation(winrate: float, avg_win: float, avg_loss: float, 
                           n_sim: int = N_SIMULATIONS, 
                           trades_per_sim: int = TRADES_PER_SIM,
                           initial_balance: float = INITIAL_BALANCE) -> dict:
    """Run Monte Carlo simulation."""
    outcomes = []
    max_drawdowns = []
    
    for _ in range(n_sim):
        balance = initial_balance
        peak = balance
        max_dd = 0
        
        for _ in range(trades_per_sim):
            if random.random() < winrate:
                balance += avg_win
            else:
                balance -= avg_loss
            
            if balance > peak:
                peak = balance
            dd = (peak - balance) / peak if peak > 0 else 0
            max_dd = max(max_dd, dd)
        
        outcomes.append(balance)
        max_drawdowns.append(max_dd)
    
    outcomes.sort()
    max_drawdowns.sort()
    
    return {
        'final_balance_p10': outcomes[int(len(outcomes) * 0.10)],
        'final_balance_p50': outcomes[int(len(outcomes) * 0.50)],
        'final_balance_p90': outcomes[int(len(outcomes) * 0.90)],
        'max_drawdown_p10': max_drawdowns[int(len(max_drawdowns) * 0.10)] * 100,
        'max_drawdown_p50': max_drawdowns[int(len(max_drawdowns) * 0.50)] * 100,
        'max_drawdown_p90': max_drawdowns[int(len(max_drawdowns) * 0.90)] * 100,
        'probability_of_ruin': sum(1 for o in outcomes if o < initial_balance * 0.5) / len(outcomes) * 100
    }

def print_results(real_stats: dict, monte: dict, trades: List[Dict]):
    """Print formatted results."""
    print("\n" + "="*50)
    print("📊 NEKO BACKTESTER v2 - REAL DATA")
    print("="*50)
    
    print("\n📈 REAL TRADE STATS (from Binance):")
    print(f"   Total Trades: {real_stats['total_trades']}")
    print(f"   Wins: {real_stats['wins']} | Losses: {real_stats['losses']}")
    print(f"   Win Rate: {real_stats['winrate']*100:.1f}%")
    print(f"   Avg Win: ${real_stats['avg_win']:.2f}")
    print(f"   Avg Loss: ${real_stats['avg_loss']:.2f}")
    print(f"   Total PnL: ${real_stats['total_pnl']:.2f}")
    
    print("\n🎲 MONTE CARLO (5000 simulations):")
    print(f"   Balance after 100 trades:")
    print(f"     10th percentile: ${monte['final_balance_p10']:.2f}")
    print(f"     50th percentile: ${monte['final_balance_p50']:.2f}")
    print(f"     90th percentile: ${monte['final_balance_p90']:.2f}")
    
    print(f"   Max Drawdown:")
    print(f"     10th percentile: {monte['max_drawdown_p10']:.1f}%")
    print(f"     50th percentile: {monte['max_drawdown_p50']:.1f}%")
    print(f"     90th percentile: {monte['max_drawdown_p90']:.1f}%")
    
    print(f"   Probability of 50% loss: {monte['probability_of_ruin']:.1f}%")
    
    # Risk assessment
    print("\n⚠️ RISK ASSESSMENT:")
    if monte['probability_of_ruin'] > 20:
        print("   🔴 HIGH RISK - Probability of significant loss > 20%")
    elif monte['probability_of_ruin'] > 5:
        print("   🟡 MEDIUM RISK - Probability of significant loss > 5%")
    else:
        print("   🟢 LOW RISK - Strategy appears stable")
    
    if monte['max_drawdown_p90'] > 50:
        print("   🔴 Extreme drawdown possible (90th percentile > 50%)")
    elif monte['max_drawdown_p90'] > 30:
        print("   🟡 High drawdown possible (90th percentile > 30%)")
    else:
        print("   🟢 Acceptable drawdown risk")
    
    print("\n" + "="*50)
    
    # Show sample recent trades
    if trades:
        print("\n📋 SAMPLE RECENT TRADES:")
        for t in trades[:5]:
            pnl = float(t.get('income', 0))
            date = datetime.fromtimestamp(int(t.get('time', 0))/1000).strftime('%Y-%m-%d')
            symbol = t.get('symbol', 'UNKNOWN')
            sign = '🟢' if pnl > 0 else '🔴'
            print(f"   {sign} {symbol}: {'+' if pnl > 0 else ''}${pnl:.2f} ({date})")

# ============ MAIN ============
def main():
    print("🔄 Fetching real trade data from Binance...")
    
    # Get real trades
    trades = get_income_history(days=90)
    
    # Calculate real stats
    real_stats = calculate_real_stats(trades)
    
    # Run Monte Carlo with REAL stats
    print(f"📊 Running Monte Carlo with winrate={real_stats['winrate']*100:.1f}%...")
    monte = monte_carlo_simulation(
        winrate=real_stats['winrate'],
        avg_win=real_stats['avg_win'] or 2.0,
        avg_loss=real_stats['avg_loss'] or 3.0
    )
    
    # Print results
    print_results(real_stats, monte, trades)

if __name__ == "__main__":
    main()
