#!/usr/bin/env node
/**
 * Neko Dashboard API - Node.js
 * Port 8080 - Static files + API
 */

const http = require('http');
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

// ── Config ─────────────────────────────────────────────────────────────────────
const PORT = 8080;
const ENV_PATH = '/root/.openclaw/workspace/neko-futures-trader/.env';
const HTML_PATH = '/root/.openclaw/workspace/neko-futures-trader/neko-light.html';

const CACHE_TTL = 25000; // 25 seconds
const INCOME_CACHE_TTL = 300000; // 5 minutes

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

// ── Cache ─────────────────────────────────────────────────────────────────────
let cache = { data: null, timestamp: 0 };
let incomeCache = { data: null, timestamp: 0 };

// ── Helpers ──────────────────────────────────────────────────────────────────
function sign(params) {
    return crypto.createHmac('sha256', SECRET).update(params).digest('hex');
}

async function binanceGET(endpoint, params = '') {
    const ts = Date.now();
    // Build query WITHOUT signature first
    const queryBase = params ? `${params}&timestamp=${ts}` : `timestamp=${ts}`;
    const signature = sign(queryBase);
    const query = `${queryBase}&signature=${signature}`;
    const url = `${BASE_URL}${endpoint}?${query}`;
    
    try {
        const res = await fetch(url, {
            headers: { 'X-MBX-APIKEY': API_KEY }
        });
        const text = await res.text();
        try {
            return JSON.parse(text);
        } catch {
            console.error('JSON parse error:', text.substring(0, 100));
            return null;
        }
    } catch (e) {
        console.error('Fetch error:', e.message);
        return null;
    }
}

async function getIncomeHistory(days = 7) {
    const now = Date.now();
    if (incomeCache.data && (now - incomeCache.timestamp) < INCOME_CACHE_TTL) {
        return incomeCache.data;
    }
    
    try {
        const startTime = now - (days * 24 * 60 * 60 * 1000);
        const data = await binanceGET('/fapi/v1/income', `startTime=${startTime}&limit=100`);
        
        if (!Array.isArray(data)) {
            incomeCache = { data: null, timestamp: now };
            return null;
        }
        
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
    } catch (e) {
        console.error('Income fetch error:', e.message);
        return null;
    }
}

async function getAlgoOrders() {
    try {
        const data = await binanceGET('/fapi/v1/allOpenOrders');
        return Array.isArray(data) ? data : [];
    } catch (e) {
        return [];
    }
}

async function fetchAccountData() {
    const now = Date.now();
    if (cache.data && (now - cache.timestamp) < CACHE_TTL) {
        return cache.data;
    }
    
    try {
        // Account data
        const account = await binanceGET('/fapi/v3/account');
        
        if (!account || !account.totalMarginBalance) {
            console.error('Invalid account response');
            return cache.data || { bal: 0, margin: 0, pos: [], algos: [], stats: null };
        }
        
        const balance = parseFloat(account.totalMarginBalance || 0);
        const marginUsed = parseFloat(account.totalInitialMargin || 0);
        const marginPct = balance ? (marginUsed / balance * 100) : 0;
        
        // Positions
        const positions = (account.positions || [])
            .filter(p => parseFloat(p.positionAmt) !== 0)
            .map(p => ({
                s: p.symbol,
                d: parseFloat(p.positionAmt) > 0 ? 'LONG' : 'SHORT',
                a: parseFloat(p.positionAmt),
                u: parseFloat(p.unrealizedProfit),
                m: parseFloat(p.markPrice),
                e: parseFloat(p.entryPrice)
            }));
        
        // Income history
        const income = await getIncomeHistory(7);
        
        // Algo orders
        const algos = await getAlgoOrders();
        
        const result = {
            bal: balance,
            margin: marginPct,
            pos: positions,
            algos: Array.isArray(algos) ? algos.map(o => ({
                s: o.symbol,
                side: o.side,
                type: o.type,
                qty: o.origQty,
                price: o.price
            })) : [],
            stats: income
        };
        
        cache = { data: result, timestamp: now };
        return result;
    } catch (e) {
        console.error('Account fetch error:', e.message);
        return cache.data || { bal: 0, margin: 0, pos: [], algos: [], stats: null };
    }
}

// ── Static File Handler ──────────────────────────────────────────────────────
async function serveStatic(req, res) {
    const filePath = req.url === '/' ? HTML_PATH : 
        path.join('/root/.openclaw/workspace/neko-futures-trader', req.url);
    
    const ext = path.extname(filePath);
    const mimeTypes = {
        '.html': 'text/html',
        '.js': 'application/javascript',
        '.css': 'text/css',
        '.json': 'application/json',
        '.png': 'image/png',
        '.ico': 'image/x-icon'
    };
    
    try {
        const data = fs.readFileSync(filePath);
        res.writeHead(200, { 'Content-Type': mimeTypes[ext] || 'text/plain' });
        res.end(data);
    } catch (e) {
        res.writeHead(404);
        res.end('Not found');
    }
}

// ── API Handler ───────────────────────────────────────────────────────────────
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

// ── Server ────────────────────────────────────────────────────────────────────
const server = http.createServer(async (req, res) => {
    // CORS
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
    
    if (req.method === 'OPTIONS') {
        res.writeHead(200);
        res.end();
        return;
    }
    
    // Remove query string
    const url = req.url.split('?')[0];
    
    if (url === '/api') {
        await handleAPI(req, res);
    } else {
        await serveStatic(req, res);
    }
});

server.listen(PORT, () => {
    console.log(`🚀 Neko Dashboard running on http://localhost:${PORT}`);
});

module.exports = server;
