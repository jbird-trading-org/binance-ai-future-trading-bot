#!/usr/bin/env python3
"""
Dashboard API server - threaded with 25-second Binance cache.
Each HTTP request runs in its own thread so slow Binance API calls don't block.

Enhanced with:
- Winrate & closed PnL from income history
- Average win/loss calculation
- Algo orders status
"""
import os, json, time, hmac, hashlib, requests, socketserver, mimetypes
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Lock

# ── Load env ──────────────────────────────────────────────────────────────────
ENV_PATH = '/root/.openclaw/workspace/neko-futures-trader/.env'
with open(ENV_PATH) as f:
    for line in f:
        line = line.strip()
        if '=' in line:
            k, v = line.split('=', 1)
            os.environ[k] = v

API_KEY  = os.environ['BINANCE_API_KEY']
SECRET   = os.environ['BINANCE_SECRET']

# ── Cache ─────────────────────────────────────────────────────────────────────
_CACHE_TTL   = 25           # seconds
_CACHE       = {'data': None, 'timestamp': 0}
_CACHE_LOCK  = Lock()
_INCOME_CACHE = {'data': None, 'timestamp': 0}


def get_signature(params):
    return hmac.new(SECRET.encode(), params.encode(), hashlib.sha256).hexdigest()


def get_income_history(days=7):
    """Fetch income history for winrate and closed PnL"""
    global _INCOME_CACHE
    now = time.time()
    
    # Use cache if fresh
    if _INCOME_CACHE['data'] is not None and (now - _INCOME_CACHE['timestamp']) < 300:
        return _INCOME_CACHE['data']
    
    try:
        ts = int(now * 1000)
        start_time = int((now - days * 24 * 60 * 60) * 1000)
        params = f'timestamp={ts}&startTime={start_time}&limit=100'
        sig = get_signature(params)
        url = f'https://fapi.binance.com/fapi/v1/income?{params}&signature={sig}'
        r = requests.get(url, headers={'X-MBX-APIKEY': API_KEY}, timeout=10)
        
        if r.status_code != 200:
            return None
            
        data = r.json()
        realized_trades = [t for t in data if t.get('incomeType') == 'REALIZED_PNL']
        
        wins = [t for t in realized_trades if float(t.get('income', 0)) > 0]
        losses = [t for t in realized_trades if float(t.get('income', 0)) < 0]
        
        closed_pnl = sum(float(t.get('income', 0)) for t in realized_trades)
        total_wins = sum(float(t.get('income', 0)) for t in wins)
        total_losses = abs(sum(float(t.get('income', 0)) for t in losses))
        
        avg_win = total_wins / len(wins) if wins else 0
        avg_loss = total_losses / len(losses) if losses else 0
        
        result = {
            'closed_pnl': closed_pnl,
            'total_trades': len(realized_trades),
            'wins': len(wins),
            'losses': len(losses),
            'winrate': (len(wins) / len(realized_trades) * 100) if realized_trades else 0,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'expectancy': (avg_win * len(wins) + (-avg_loss) * len(losses)) / len(realized_trades) if realized_trades else 0
        }
        
        _INCOME_CACHE['data'] = result
        _INCOME_CACHE['timestamp'] = now
        return result
    except Exception as e:
        print(f'[dashboard_api] Income API error: {e}')
        return None


def get_algo_orders():
    """Check algo orders via SAPI endpoint"""
    try:
        ts = int(time.time() * 1000)
        params = f'timestamp={ts}'
        sig = get_signature(params)
        url = f'https://api.binance.com/sapi/v1/algo/futures/openOrders?{params}&signature={sig}'
        r = requests.get(url, headers={'X-MBX-APIKEY': API_KEY}, timeout=10)
        
        if r.status_code == 200:
            orders = r.json().get('orders', [])
            return {
                'count': len(orders),
                'has_algo': len(orders) > 0
            }
    except Exception as e:
        print(f'[dashboard_api] Algo orders error: {e}')
    return {'count': 0, 'has_algo': False}


def _fetch_fresh():
    """Use fapi/v2/positionRisk — has entryPrice, markPrice, unRealizedProfit."""
    ts  = int(time.time() * 1000)
    sig = hmac.new(SECRET.encode(), f'timestamp={ts}'.encode(), hashlib.sha256).hexdigest()
    r   = requests.get(
        f'https://fapi.binance.com/fapi/v2/positionRisk?timestamp={ts}&signature={sig}',
        headers={'X-MBX-APIKEY': API_KEY}, timeout=8
    )
    raw = r.json()
    if isinstance(raw, dict) and raw.get('code'):
        raise Exception(raw.get('msg', 'positionRisk error'))

    pnl = 0.0
    pos = []
    for p in raw:
        amt = float(p.get('positionAmt', 0))
        if amt == 0:
            continue
        entry = float(p.get('entryPrice', 0))
        mark  = float(p.get('markPrice', 0))
        unreal = float(p.get('unRealizedProfit', 0))
        pnl   += unreal
        pos.append({
            's': p['symbol'].replace('USDT', ''),
            'd': 'LONG' if amt > 0 else 'SHORT',
            'e': entry,
            'm': mark,
            'u': unreal,
            'a': abs(amt),
        })

    # Balance from account snapshot
    sig2 = hmac.new(SECRET.encode(), f'timestamp={ts}'.encode(), hashlib.sha256).hexdigest()
    r2   = requests.get(
        f'https://fapi.binance.com/fapi/v3/account?timestamp={ts}&signature={sig2}',
        headers={'X-MBX-APIKEY': API_KEY}, timeout=8
    )
    bal = float(r2.json().get('totalMarginBalance', 0))
    
    # Get income data for closed PnL & winrate
    income = get_income_history(7)
    
    # Get algo orders status
    algo = get_algo_orders()
    
    # Calculate margin usage as percentage of balance
    account_data = r2.json()
    total_initial_margin = float(account_data.get('totalInitialMargin', 0))
    margin_balance = float(account_data.get('totalMarginBalance', bal))
    margin_used_pct = (total_initial_margin / margin_balance * 100) if margin_balance > 0 else 0
    
    return {
        'bal': bal, 
        'pnl': pnl, 
        'pos': pos,
        'margin': margin_used_pct,
        'stats': income if income else {
            'closed_pnl': 0, 'total_trades': 0, 'wins': 0, 'losses': 0,
            'winrate': 0, 'avg_win': 0, 'avg_loss': 0, 'expectancy': 0
        },
        'algo': algo
    }


def get_account_data():
    """
    Return cached data if fresh (< CACHE_TTL seconds old),
    otherwise fetch fresh from Binance.
    """
    global _CACHE
    now = time.time()

    if _CACHE['data'] is not None and (now - _CACHE['timestamp']) < _CACHE_TTL:
        return {**_CACHE['data'], 'cached': True}

    try:
        fresh = _fetch_fresh()
        with _CACHE_LOCK:
            _CACHE['data']      = fresh
            _CACHE['timestamp']  = now
        return {**fresh, 'cached': False}
    except Exception as exc:
        print(f'[dashboard_api] Binance API error: {exc}')
        with _CACHE_LOCK:
            if _CACHE['data'] is not None:
                return {**_CACHE['data'], 'cached': True, 'err': str(exc)}
        return {'err': str(exc), 'bal': 0.0, 'pnl': 0.0, 'pos': [], 'stats': {}, 'algo': {}}


# ── Request handler ───────────────────────────────────────────────────────────
class H(BaseHTTPRequestHandler):

    def do_GET(self):
        if self.path.startswith('/api'):
            self._handle_api()
        else:
            self._serve_static()

    def _handle_api(self):
        try:
            data = get_account_data()
        except Exception as e:
            data = {'err': str(e), 'bal': 0.0, 'pnl': 0.0, 'pos': [], 'stats': {}, 'algo': {}}
        body = json.dumps(data).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(body)

    def _serve_static(self):
        if '..' in self.path:
            self.send_error(403, 'Forbidden')
            return

        if self.path == '/':
            file_path = '/root/.openclaw/workspace/index.html'
        else:
            file_path = '/root/.openclaw/workspace' + self.path

        if not os.path.isfile(file_path):
            self.send_error(404, 'Not Found')
            return

        mime = mimetypes.guess_type(file_path)[0] or 'application/octet-stream'
        try:
            with open(file_path, 'rb') as f:
                body = f.read()
        except Exception:
            self.send_error(500, 'Internal Server Error')
            return

        self.send_response(200)
        self.send_header('Content-Type', mime)
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        print(f'[dashboard_api] {fmt % args}')


# ── Threaded HTTP server ───────────────────────────────────────────────────────
class ThreadedHTTPServer(HTTPServer):
    daemon_threads   = True
    allow_reuse_address = True


if __name__ == '__main__':
    server = ThreadedHTTPServer(('0.0.0.0', 8080), H)
    print('[dashboard_api] Listening on 0.0.0.0:8080')
    server.serve_forever()
