#!/usr/bin/env node
/**
 * Neko Dashboard API - Node.js v2
 * Fix: Proper position data with entry/mark price
 */

const http = require('http');
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const PORT = 8080;
const ENV_PATH = '/root/.openclaw/workspace/neko-futures-trader/.env';
const HTML_PATH = '/root/.openclaw/workspace/neko-futures-trader/neko-light.html';
const CACHE_TTL = 25000;
const INCOME_CACHE_TTL = 300000;

// Load env
const env = {};
if (fs.existsSync(ENV_PATH)) {
    fs.readFileSync(ENV_PATH, 'utf8').split('\n').forEach(line => {
        const [k, ...v] = line.split('=');
        if (k && v.length) env[k.trim()] = v.join('=').trim();
    });
}

const API_KEY = env.BINANCE_API_KEY || '';
const SECRET = env.BINANCE_SECRET || '';
const BASE_URL = 'https://fapi.binance.com';

let cache = { data: null, timestamp: 0 };
let incomeCache = { data: null, timestamp: 0 };

function sign(params) {
    return crypto.createHmac('sha256', SECRET).update(params).digest('hex');
}

async function binanceGET(endpoint, params = '') {
    const ts = Date.now();
    const queryBase = params ? `${params}&timestamp=${ts}` : `timestamp=${ts}`;
    const signature = sign(queryBase);
    const query = `${queryBase}&signature=${signature}`;
    const url = `${BASE_URL}${endpoint}?${query}`;
    
    try {
        const res = await fetch(url, { headers: { 'X-MBX-APIKEY': API_KEY } });
        const text = await res.text();
        try { return JSON.parse(text); } 
        catch { console.error('JSON error:', text.substring(0, 80)); return null; }
    } catch (e) { console.error('Fetch error:', e.message); return null; }
}

async function getMarkPrice(symbol) {
    try {
        const url = `${BASE_URL}/fapi/v1/ticker/price?symbol=${symbol}`;
        const res = await fetch(url);
        const data = await res.json();
        return parseFloat(data.price || 0);
    } catch { return 0; }
}

async function getIncomeHistory(days = 7) {
    const now = Date.now();
    if (incomeCache.data && (now - incomeCache.timestamp) < INCOME_CACHE_TTL) {
        return incomeCache.data;
    }
    
    try {
        const startTime = now - (days * 24 * 60 * 60 * 1000);
        const data = await binanceGET('/fapi/v1/income', `startTime=${startTime}&limit=100`);
        
        if (!Array.isArray(data)) return null;
        
        const realized = data.filter(t => t.incomeType === 'REALIZED_PNL');
        const wins = realized.filter(t => parseFloat(t.income) > 0);
        const losses = realized.filter(t => parseFloat(t.income) < 0);
        
        const closedPnl = realized.reduce((sum, t) => sum + parseFloat(t.income), 0);
        const totalWins = wins.reduce((sum, t) => sum + parseFloat(t.income), 0);
        const totalLosses = Math.abs(losses.reduce((sum, t) => sum + parseFloat(t.income), 0));
        
        incomeCache = {
            data: {
                closed_pnl: closedPnl,
                total_trades: realized.length,
                wins: wins.length,
                losses: losses.length,
                winrate: realized.length ? (wins.length / realized.length * 100) : 0,
                avg_win: wins.length ? totalWins / wins.length : 0,
                avg_loss: losses.length ? totalLosses / losses.length : 0
            },
            timestamp: now
        };
        return incomeCache.data;
    } catch (e) { console.error('Income error:', e.message); return null; }
}

async function getAlgoOrders() {
    try {
        const data = await binanceGET('/fapi/v1/allOpenOrders');
        return Array.isArray(data) ? data : [];
    } catch { return []; }
}


async function getClosedTrades() {
    try {
        // Get recent income from Binance - last 24 hours
        const now = Date.now();
        const startTime = now - (24 * 60 * 60 * 1000); // 24 hours ago
        const data = await binanceGET('/fapi/v1/income', `startTime=${startTime}&limit=100`);
        
        if (!Array.isArray(data)) return [];
        
        // Get realized PnL only
        const realized = data.filter(t => t.incomeType === 'REALIZED_PNL');
        
        // Binance returns oldest first with startTime, so take last 5 (most recent)
        return realized.slice(-5).map(t => ({
            symbol: t.symbol,
            side: parseFloat(t.income) > 0 ? 'WIN' : 'LOSS',
            pnl: parseFloat(t.income),
            time: parseInt(t.time)
        }));
    } catch (e) {
        console.error('Closed trades error:', e.message);
        return [];
    }
}


async function fetchAccountData() {
    const now = Date.now();
    if (cache.data && (now - cache.timestamp) < CACHE_TTL) {
        return cache.data;
    }
    
    try {
        // Use fapi/v2/positionRisk for detailed position data
        const positionRisk = await binanceGET('/fapi/v2/positionRisk');
        const account = await binanceGET('/fapi/v3/account');
        
        if (!account || !account.totalMarginBalance) {
            return cache.data || { bal: 0, margin: 0, pos: [], algos: [], stats: null };
        }
        
        const balance = parseFloat(account.totalMarginBalance || 0);
        const marginUsed = parseFloat(account.totalInitialMargin || 0);
        const marginPct = balance ? (marginUsed / balance * 100) : 0;
        
        // Build position map from positionRisk (has entryPrice, markPrice)
        const posMap = {};
        if (Array.isArray(positionRisk)) {
            for (const p of positionRisk) {
                if (parseFloat(p.positionAmt) !== 0) {
                    posMap[p.symbol] = {
                        e: parseFloat(p.entryPrice) || 0,
                        m: parseFloat(p.markPrice) || 0,
                        u: parseFloat(p.unrealizedProfit) || 0
                    };
                }
            }
        }
        
        // Build positions from account positions
        const positions = (account.positions || [])
            .filter(p => parseFloat(p.positionAmt) !== 0)
            .map(p => {
                const sym = p.symbol;
                const extra = posMap[sym] || {};
                return {
                    s: sym,
                    d: parseFloat(p.positionAmt) > 0 ? 'LONG' : 'SHORT',
                    a: parseFloat(p.positionAmt),
                    u: extra.u || parseFloat(p.unrealizedProfit) || 0,
                    m: extra.m || 0,
                    e: extra.e || 0
                };
            });
        
        const income = await getIncomeHistory(7);
        const algos = await getAlgoOrders();
        
        const pnl = positions.reduce((sum, p) => sum + (p.u || 0), 0);
        
        const result = {
            bal: balance,
            margin: marginPct,
            pnl: pnl,
            pos: positions,
            algos: Array.isArray(algos) ? algos.map(o => ({
                s: o.symbol, side: o.side, type: o.type, 
                qty: o.origQty, price: o.price
            })) : [],
            stats: income,
            closed_trades: await getClosedTrades(7)
        };
        
        cache = { data: result, timestamp: now };
        return result;
    } catch (e) {
        console.error('Account error:', e.message);
        return cache.data || { bal: 0, margin: 0, pos: [], algos: [], stats: null };
    }
}

async function serveStatic(req, res) {
    const filePath = req.url === '/' ? HTML_PATH : 
        path.join('/root/.openclaw/workspace/neko-futures-trader', req.url);
    const ext = path.extname(filePath);
    const mimeTypes = { '.html': 'text/html', '.js': 'application/javascript', '.css': 'text/css', '.json': 'application/json', '.png': 'image/png' };
    
    try {
        const data = fs.readFileSync(filePath);
        res.writeHead(200, { 'Content-Type': mimeTypes[ext] || 'text/plain' });
        res.end(data);
    } catch { res.writeHead(404); res.end('Not found'); }
}

async function handleAPI(req, res) {
    try {
        const data = await fetchAccountData();
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify(data));
    } catch (e) {
        res.writeHead(500);
        res.end(JSON.stringify({ error: e.message }));
    }
}

const server = http.createServer(async (req, res) => {
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
    if (req.method === 'OPTIONS') { res.writeHead(200); res.end(); return; }
    
    const url = req.url.split('?')[0];
    if (url === '/api') await handleAPI(req, res);
    else await serveStatic(req, res);
});

server.listen(PORT, () => console.log(`🚀 Neko Dashboard on http://localhost:${PORT}`));
module.exports = server;
