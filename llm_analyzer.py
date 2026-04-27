#!/usr/bin/env python3
"""
LLM Analyzer — Second opinion layer for Neko Scanner
Cheap, fast LLM check before trade execution.
Uses OpenRouter API (default: openai/gpt-4o-mini)
"""

import os
import json
import re
import time
import requests

# === CONFIG (override from config.py if available) ===
try:
    from config import (LLM_ENABLED, LLM_MODEL, LLM_BASE_URL, LLM_MIN_SCORE,
                        LLM_TEMPERATURE, LLM_FALLBACK1_ENABLED,
                        LLM_FALLBACK1_BASE_URL, LLM_FALLBACK1_MODEL,
                        LLM_FALLBACK2_ENABLED,
                        LLM_FALLBACK2_BASE_URL, LLM_FALLBACK2_MODEL)
except ImportError:
    LLM_ENABLED = True
    LLM_MODEL = "xiaomi/mimo-v2-pro"
    LLM_BASE_URL = "https://inference-api.nousresearch.com/v1/chat/completions"
    LLM_MIN_SCORE = 4
    LLM_TEMPERATURE = 0.1
    LLM_FALLBACK1_ENABLED = True
    LLM_FALLBACK1_BASE_URL = "https://openrouter.ai/api/v1/chat/completions"
    LLM_FALLBACK1_MODEL = "nousresearch/hermes-4-70b"
    LLM_FALLBACK2_ENABLED = True
    LLM_FALLBACK2_BASE_URL = "https://api.minimaxi.chat/v1/chat/completions"
    LLM_FALLBACK2_MODEL = "MiniMax-M2.5"

# Load API keys from env
LLM_API_KEY = os.environ.get("NOUS_API_KEY", "")
LLM_FALLBACK1_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
LLM_FALLBACK2_API_KEY = os.environ.get("MINIMAX_API_KEY", "")

# === CACHE ===
_analysis_cache = {}
CACHE_TTL = 300  # 5 min cache


def _get_cache_key(symbol, direction, score):
    return f"{symbol}:{direction}:{score}"


def _is_cache_valid(key):
    if key in _analysis_cache:
        entry = _analysis_cache[key]
        return (time.time() - entry['ts']) < CACHE_TTL
    return False


def format_analysis_prompt(analysis):
    """Build a concise prompt from analysis dict."""

    sym = analysis.get('symbol', 'UNKNOWN')
    direction = analysis.get('direction', 'LONG')
    score = analysis.get('runner_score', 0)

    prompt = f"""Analyze this crypto futures {direction} signal for {sym}.

TECHNICAL DATA:
- Price: ${analysis.get('current', 0):.6f}
- 24h Change: {analysis.get('price_change', 0):+.2f}%
- 1h Momentum: {analysis.get('change_1h', 0):+.2f}%
- RSI(14): {analysis.get('rsi', 50):.1f}
- MACD Histogram: {analysis.get('macd_histogram', 0):+.4f}
- EMA21: {analysis.get('ema_21', 0):.6f} | EMA50: {analysis.get('ema_50', 0):.6f}
- ATR%: {analysis.get('atr_pct', 0):.2f}%
- Volume Ratio: {analysis.get('vol_ratio', 1):.1f}x avg
- Open Interest Change: {analysis.get('oi_change', 0):+.1f}%
- Funding Rate: {analysis.get('funding_rate', 0):.4f}%
- Trend: {analysis.get('trend', 'N/A')} | Structure: {analysis.get('structure', 'N/A')}
- Breakout: {'Yes' if analysis.get('breakout') else 'No'}
- Weekly Change: {analysis.get('weekly_change', 0):+.1f}%
- Score: {score}/19
- SL: ${analysis.get('sl', 0):.6f} | TP: ${analysis.get('tp1', 0):.6f}
- SL Method: {analysis.get('sl_method', 'PRICE')}

|RULES:
1. Is this a good {direction} entry RIGHT NOW?
2. Is momentum aligned? (1h and 24h should agree with direction)
3. For LONG: RSI 30-60 ideal, >65 risky. For SHORT: RSI 40-70 is VALID (dropping from high), only reject if RSI < 30
4. Is the SL reasonable (not too tight, not too wide)?
5. Any red flags? (funding extreme, divergence, exhaustion)
6. For SHORT: If price_change < -3%, momentum drop is real — approve if other indicators align

Reply in JSON ONLY:
{{"decision": "YES" or "NO", "confidence": 0.0-1.0, "reason": "one line reason"}}
"""
    return prompt


def _do_api_call(url, api_key, model, payload, timeout, max_retries=2):
    """Make a single API call with retry on rate limit (429). Returns response dict or None."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    for attempt in range(max_retries + 1):
        try:
            r = requests.post(url, headers=headers, json=payload, timeout=timeout)
            if r.status_code == 200:
                data = r.json()
                content = data.get('choices', [{}])[0].get('message', {}).get('content')
                if not content:
                    # Model used reasoning field instead of content (e.g. xiaomi/mimo)
                    reasoning = data.get('choices', [{}])[0].get('message', {}).get('reasoning', '')
                    if reasoning:
                        # Try to extract JSON from reasoning
                        content = reasoning
                    else:
                        return None
                usage = data.get('usage', {})
                # Strip MiniMax/other thinking tags
                content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()
                return {
                    'content': content,
                    'tokens_in': usage.get('prompt_tokens', 0),
                    'tokens_out': usage.get('completion_tokens', 0),
                }
            elif r.status_code == 429:
                # Rate limited — parse retry-after if available
                retry_after = int(r.headers.get('Retry-After', 3 * (attempt + 1)))
                if attempt < max_retries:
                    print(f"  ⏳ Rate limited ({url.split('/')[2]}), retry in {retry_after}s... (attempt {attempt+1}/{max_retries})")
                    time.sleep(retry_after)
                    continue
                else:
                    print(f"  ⚠️ Rate limited ({url.split('/')[2]}), max retries exceeded")
                    return None
            else:
                print(f"  ⚠️ LLM API error ({url.split('/')[2]}): {r.status_code} — {r.text[:100]}")
                return None
        except requests.Timeout:
            if attempt < max_retries:
                print(f"  ⏳ LLM timeout ({url.split('/')[2]}), retrying... (attempt {attempt+1}/{max_retries})")
                time.sleep(2 * (attempt + 1))
                continue
            print(f"  ⚠️ LLM timeout ({url.split('/')[2]})")
            return None
        except Exception as e:
            print(f"  ⚠️ LLM error ({url.split('/')[2]}): {e}")
            return None
    return None


def call_llm(prompt, model=None, timeout=15):
    """Call LLM with 3-tier fallback: Nous → OpenRouter → MiniMax."""

    model = model or LLM_MODEL
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a crypto futures trading analyst. "
                    "For LONG entries: RSI 30-60 is ideal, >65 is risky. "
                    "For SHORT entries: RSI 40-70 is NORMAL (coin dropping from high), "
                    "do NOT reject SHORT just because RSI > 60 — that's where short setups happen. "
                    "Only reject SHORT if RSI < 30 (oversold, too late). "
                    "Be balanced — approve setups with clear momentum alignment. "
                    "During market-wide drops (price_change < -3%), SHORT signals are VALID even with higher RSI. "
                    "Respond ONLY with valid JSON, no markdown."
                )
            },
            {"role": "user", "content": prompt}
        ],
        "temperature": LLM_TEMPERATURE,
        "max_tokens": 300,
    }

    # ── Tier 1: Nous Research (Primary) ──────────────────────────────────
    if LLM_API_KEY:
        print(f"  🧠 LLM → Nous ({model})...")
        result = _do_api_call(LLM_BASE_URL, LLM_API_KEY, model, payload, timeout)
        if result:
            result['provider'] = 'nous'
            return result
        print("  ⚠️ Nous failed, trying OpenRouter...")
    else:
        print("  ⚠️ No Nous API key, skipping primary...")

    # ── Tier 2: OpenRouter (Fallback 1) ──────────────────────────────────
    if LLM_FALLBACK1_ENABLED and LLM_FALLBACK1_API_KEY:
        fb1_model = LLM_FALLBACK1_MODEL
        payload_fb1 = {**payload, "model": fb1_model}
        print(f"  🧠 LLM → OpenRouter ({fb1_model})...")
        result = _do_api_call(LLM_FALLBACK1_BASE_URL, LLM_FALLBACK1_API_KEY,
                              fb1_model, payload_fb1, timeout)
        if result:
            result['provider'] = 'openrouter'
            return result
        print("  ⚠️ OpenRouter failed, trying MiniMax...")
    else:
        print("  ⚠️ OpenRouter disabled or no key, skipping...")

    # ── Tier 3: MiniMax (Fallback 2) ─────────────────────────────────────
    if LLM_FALLBACK2_ENABLED and LLM_FALLBACK2_API_KEY:
        fb2_model = LLM_FALLBACK2_MODEL
        payload_fb2 = {**payload, "model": fb2_model}
        print(f"  🧠 LLM → MiniMax ({fb2_model})...")
        result = _do_api_call(LLM_FALLBACK2_BASE_URL, LLM_FALLBACK2_API_KEY,
                              fb2_model, payload_fb2, timeout)
        if result:
            result['provider'] = 'minimax'
            return result
        print("  ⚠️ MiniMax also failed")
    else:
        print("  ⚠️ MiniMax disabled or no key")

    return None


def parse_llm_response(content):
    """Parse JSON from LLM response. Returns dict or None."""

    if not content:
        return None

    # Clean up — remove markdown code blocks if present
    text = content.strip()
    if text.startswith('```'):
        lines = text.split('\n')
        text = '\n'.join(lines[1:-1]) if len(lines) > 2 else text
        text = text.replace('```json', '').replace('```', '').strip()

    try:
        result = json.loads(text)
        if 'decision' in result and 'reason' in result:
            return result
    except json.JSONDecodeError:
        pass

    # Fallback: try to find YES/NO in text
    if 'YES' in text.upper() and 'NO' not in text.upper().replace('YES', ''):
        return {'decision': 'YES', 'confidence': 0.5, 'reason': text[:100]}
    elif 'NO' in text.upper():
        return {'decision': 'NO', 'confidence': 0.5, 'reason': text[:100]}

    return None


def analyze_signal(analysis, force=False):
    """
    Main entry point — analyze a signal with LLM.

    Args:
        analysis: dict from analyze_symbol() with all indicators
        force: bypass cache and minimum score check

    Returns:
        dict with keys: approved (bool), reason (str), model (str),
                         tokens_in (int), tokens_out (int), latency_ms (int)
    """

    symbol = analysis.get('symbol', '')
    direction = analysis.get('direction', '')
    score = analysis.get('runner_score', 0)

    # Check if enabled
    if not LLM_ENABLED and not force:
        return {
            'approved': True,
            'reason': 'LLM disabled',
            'model': None,
            'tokens_in': 0,
            'tokens_out': 0,
            'latency_ms': 0,
        }

    # Check minimum score
    if score < LLM_MIN_SCORE and not force:
        return {
            'approved': True,
            'reason': f'Score {score} < {LLM_MIN_SCORE}, skipped LLM',
            'model': 'skipped',
            'confidence': 0,
            'tokens_in': 0,
            'tokens_out': 0,
            'latency_ms': 0,
        }

    # Check cache
    cache_key = _get_cache_key(symbol, direction, score)
    if _is_cache_valid(cache_key):
        cached = _analysis_cache[cache_key]
        print(f"  🧠 LLM cache hit: {symbol}")
        return cached['result']

    # Build prompt and call
    prompt = format_analysis_prompt(analysis)
    print(f"  🧠 LLM analyzing {symbol} {direction} (score:{score})...")

    start = time.time()
    response = call_llm(prompt)
    latency_ms = int((time.time() - start) * 1000)

    if not response:
        # On failure, allow trade (fail-open)
        result = {
            'approved': True,
            'reason': 'LLM call failed, fail-open',
            'model': LLM_MODEL,
            'provider': None,
            'tokens_in': 0,
            'tokens_out': 0,
            'latency_ms': latency_ms,
        }
        _analysis_cache[cache_key] = {'result': result, 'ts': time.time()}
        return result

    # Parse response
    parsed = parse_llm_response(response['content'])

    if not parsed:
        # Parse failed, fail-open
        result = {
            'approved': True,
            'reason': f'Parse failed: {response["content"][:80]}',
            'model': LLM_MODEL,
            'provider': response.get('provider', 'unknown'),
            'tokens_in': response['tokens_in'],
            'tokens_out': response['tokens_out'],
            'latency_ms': latency_ms,
        }
        _analysis_cache[cache_key] = {'result': result, 'ts': time.time()}
        return result

    # Build result
    decision = parsed.get('decision', 'YES').upper()
    approved = decision == 'YES'
    reason = parsed.get('reason', 'No reason given')
    confidence = parsed.get('confidence', 0.5)

    result = {
        'approved': approved,
        'reason': reason,
        'confidence': confidence,
        'model': LLM_MODEL,
        'provider': response.get('provider', 'unknown'),
        'tokens_in': response['tokens_in'],
        'tokens_out': response['tokens_out'],
        'latency_ms': latency_ms,
    }

    # Cache result
    _analysis_cache[cache_key] = {'result': result, 'ts': time.time()}

    status = "✅ APPROVED" if approved else "❌ REJECTED"
    print(f"  🧠 LLM: {status} — {reason} ({latency_ms}ms)")

    return result


def batch_analyze(signals, max_concurrent=3):
    """
    Analyze multiple signals sequentially.
    (Kept simple — no async needed for 3-5 candidates)

    Args:
        signals: list of analysis dicts from analyze_symbol()

    Returns:
        list of (analysis, llm_result) tuples
    """
    results = []
    for analysis in signals:
        result = analyze_signal(analysis)
        results.append((analysis, result))
    return results


# === CLI test ===
if __name__ == "__main__":
    # Quick test with fake data
    test_analysis = {
        'symbol': 'SOLUSDT',
        'direction': 'LONG',
        'current': 142.50,
        'price_change': 5.2,
        'change_1h': 1.8,
        'rsi': 45.3,
        'macd_histogram': 0.0045,
        'ema_21': 140.2,
        'ema_50': 138.0,
        'atr': 3.5,
        'atr_pct': 2.45,
        'vol_ratio': 3.2,
        'oi_change': 12.5,
        'funding_rate': 0.03,
        'trend': 'BULLISH',
        'structure': 'BREAKOUT',
        'breakout': True,
        'weekly_change': 8.5,
        'runner_score': 8,
        'sl': 136.5,
        'tp1': 155.0,
        'sl_method': 'PRICE',
    }

    print("=== LLM Analyzer Test ===")
    result = analyze_signal(test_analysis, force=True)
    print(json.dumps(result, indent=2))
