#!/usr/bin/env python3
"""
LLM Analyzer — Second opinion layer for Neko Scanner
Cheap, fast LLM check before trade execution.

2026-05-22 OVERHAUL:
- Tier 1: claude-haiku-4.5 (Nous) — fast, reliable, content-based JSON
- Tier 2: xiaomi/mimo-v2.5-pro (Nous) — reasoning model, uses tool_calls
- Tier 3: rule_based_backup — 7 technical gates when LLM down
"""

import os
import json
import re

# Load .env at import time so API keys are populated regardless of import order.
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
except Exception:
    _env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.isfile(_env_path):
        try:
            with open(_env_path) as _f:
                for _line in _f:
                    _line = _line.strip()
                    if not _line or _line.startswith("#") or "=" not in _line:
                        continue
                    _k, _v = _line.split("=", 1)
                    _k = _k.strip()
                    _v = _v.strip().strip('"').strip("'")
                    if _k and _k not in os.environ:
                        os.environ[_k] = _v
        except Exception:
            pass
import time
import requests

# === CONFIG (override from config.py if available) ===
try:
    from config import (LLM_ENABLED, LLM_MODEL, LLM_BASE_URL, LLM_MIN_SCORE,
                        LLM_TEMPERATURE, LLM_FALLBACK1_ENABLED,
                        LLM_FALLBACK1_BASE_URL, LLM_FALLBACK1_MODEL,
                        LLM_FALLBACK2_ENABLED,
                        LLM_FALLBACK2_BASE_URL, LLM_FALLBACK2_MODEL,
                        LLM_BACKUP_MODE, LLM_BACKUP_MIN_SCORE,
                        LLM_BACKUP_MAX_CHASE, LLM_BACKUP_MAX_RSI_LONG,
                        LLM_BACKUP_MIN_RSI_LONG, LLM_BACKUP_MAX_RSI_SHORT,
                        LLM_BACKUP_MIN_RSI_SHORT, LLM_BACKUP_MIN_VOL_RATIO,
                        LLM_BACKUP_MAX_FUNDING_LONG, LLM_BACKUP_MAX_FUNDING_SHORT)
except ImportError:
    LLM_ENABLED = True
    LLM_MODEL = "anthropic/claude-haiku-4.5"
    LLM_BASE_URL = "https://inference-api.nousresearch.com/v1/chat/completions"
    LLM_MIN_SCORE = 6
    LLM_TEMPERATURE = 0.1
    LLM_FALLBACK1_ENABLED = True
    LLM_FALLBACK1_BASE_URL = "https://inference-api.nousresearch.com/v1/chat/completions"
    LLM_FALLBACK1_MODEL = "xiaomi/mimo-v2.5-pro"
    LLM_FALLBACK2_ENABLED = False
    LLM_FALLBACK2_BASE_URL = ""
    LLM_FALLBACK2_MODEL = ""
    LLM_BACKUP_MODE = "rule_based"
    LLM_BACKUP_MIN_SCORE = 9
    LLM_BACKUP_MAX_CHASE = 4.0
    LLM_BACKUP_MAX_RSI_LONG = 65.0
    LLM_BACKUP_MIN_RSI_LONG = 32.0
    LLM_BACKUP_MAX_RSI_SHORT = 75.0
    LLM_BACKUP_MIN_RSI_SHORT = 35.0
    LLM_BACKUP_MIN_VOL_RATIO = 2.0
    LLM_BACKUP_MAX_FUNDING_LONG = 0.06
    LLM_BACKUP_MAX_FUNDING_SHORT = -0.06

# Load API keys from env — both tiers use Nous
LLM_API_KEY = os.environ.get("NOUS_API_KEY", "")
LLM_FALLBACK1_API_KEY = os.environ.get("NOUS_API_KEY", "")

# === CACHE ===
_analysis_cache = {}
CACHE_TTL = 300  # 5 min cache

# === TOOL CALLS SCHEMA (for reasoning models) ===
_ANALYZE_SIGNAL_TOOL = {
    "type": "function",
    "function": {
        "name": "analyze_signal",
        "description": "Submit your trading signal analysis. Call this with your decision.",
        "parameters": {
            "type": "object",
            "properties": {
                "decision": {
                    "type": "string",
                    "enum": ["YES", "NO"],
                    "description": "YES = approve trade, NO = reject"
                },
                "confidence": {
                    "type": "number",
                    "minimum": 0.0,
                    "maximum": 1.0,
                    "description": "How confident in this decision (0.0-1.0)"
                },
                "reason": {
                    "type": "string",
                    "description": "Brief one-line reason for the decision"
                }
            },
            "required": ["decision", "confidence", "reason"]
        }
    }
}


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

RULES:
1. Is this a good {direction} entry RIGHT NOW?
2. Is momentum aligned? (1h and 24h should agree with direction)
3. For LONG: RSI 30-65 is ACCEPTABLE. For SHORT: RSI 40-70 is VALID, reject if RSI < 30
4. Is the SL reasonable (not too tight, not too wide)?
5. Any red flags? (funding extreme, divergence, exhaustion)
6. ANTI-CHASING: If price_change > 5% (LONG) or < -5% (SHORT), the move is already extended — REJECT
"""
    return prompt


def _do_api_call(url, api_key, model, payload, timeout, max_retries=2):
    """Make API call. Supports both content-based and tool_calls-based models."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    for attempt in range(max_retries + 1):
        try:
            r = requests.post(url, headers=headers, json=payload, timeout=timeout)
            if r.status_code == 200:
                data = r.json()
                msg = data.get('choices', [{}])[0].get('message', {})
                usage = data.get('usage', {})

                # ── Check tool_calls first (reasoning models use this) ──
                tool_calls = msg.get('tool_calls', [])
                if tool_calls:
                    for tc in tool_calls:
                        fn = tc.get('function', {})
                        if fn.get('name') == 'analyze_signal':
                            try:
                                args = json.loads(fn.get('arguments', '{}'))
                                # Return as structured result directly
                                return {
                                    'content': None,
                                    'tool_call_result': args,
                                    'tokens_in': usage.get('prompt_tokens', 0),
                                    'tokens_out': usage.get('completion_tokens', 0),
                                }
                            except json.JSONDecodeError:
                                continue

                # ── Fall back to content field ──
                content = msg.get('content')
                if not content:
                    # Reasoning model — try reasoning field
                    reasoning = msg.get('reasoning', '')
                    if reasoning:
                        content = reasoning
                    else:
                        return None

                # Strip thinking tags
                content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()
                return {
                    'content': content,
                    'tokens_in': usage.get('prompt_tokens', 0),
                    'tokens_out': usage.get('completion_tokens', 0),
                }
            elif r.status_code == 429:
                retry_after = int(r.headers.get('Retry-After', 3 * (attempt + 1)))
                if attempt < max_retries:
                    print(f"  ⏳ Rate limited ({url.split('/')[2]}), retry in {retry_after}s...")
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
                print(f"  ⏳ LLM timeout ({url.split('/')[2]}), retrying...")
                time.sleep(2 * (attempt + 1))
                continue
            print(f"  ⚠️ LLM timeout ({url.split('/')[2]})")
            return None
        except Exception as e:
            print(f"  ⚠️ LLM error ({url.split('/')[2]}): {e}")
            return None
    return None


def _build_content_payload(model, messages, temperature, max_tokens):
    """Standard content-based payload (for non-reasoning models)."""
    return {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }


def _build_toolcall_payload(model, messages, temperature, max_tokens):
    """Tool-call payload (for reasoning models that return content=None)."""
    return {
        "model": model,
        "messages": messages,
        "tools": [_ANALYZE_SIGNAL_TOOL],
        "tool_choice": {"type": "function", "function": {"name": "analyze_signal"}},
        "temperature": temperature,
        "max_tokens": max_tokens,
    }


def call_llm(prompt, model=None, timeout=15):
    """Call LLM with 2-tier fallback: claude-haiku-4.5 → mimo-v2.5-pro → backup."""

    model = model or LLM_MODEL
    messages = [
        {
            "role": "system",
            "content": (
                "You are a crypto futures trading analyst. "
                "For LONG entries: RSI 30-65 is ACCEPTABLE (not suboptimal), >70 is risky. "
                "RSI 40-60 is optimal for LONG, RSI 30-40 and 60-65 are still valid. "
                "For SHORT entries: RSI 40-70 is NORMAL (coin dropping from high), "
                "do NOT reject SHORT just because RSI > 60 — that's where short setups happen. "
                "Only reject SHORT if RSI < 30 (oversold, too late). "
                "Be balanced — approve setups with clear momentum alignment. "
                "During market-wide drops (price_change < -3%), SHORT signals are VALID even with higher RSI. "
                "CRITICAL: Reject if price has already moved >3% in the signal direction (chasing extended moves). "
                "Respond ONLY with valid JSON, no markdown."
            )
        },
        {"role": "user", "content": prompt}
    ]

    # ── Tier 1: claude-haiku-4.5 (content-based, fast, reliable) ────────
    if LLM_API_KEY:
        payload = _build_content_payload(model, messages, LLM_TEMPERATURE, 300)
        print(f"  🧠 LLM → {model}...")
        result = _do_api_call(LLM_BASE_URL, LLM_API_KEY, model, payload, timeout)
        if result:
            result['provider'] = 'nous'
            return result
        print(f"  ⚠️ {model} failed, trying fallback...")
    else:
        print("  ⚠️ No Nous API key, skipping...")

    # ── Tier 2: xiaomi/mimo-v2.5-pro (reasoning model, uses tool_calls) ─
    if LLM_FALLBACK1_ENABLED and LLM_FALLBACK1_API_KEY:
        fb1_model = LLM_FALLBACK1_MODEL
        # Reasoning models need tool_calls for structured output
        payload_fb1 = _build_toolcall_payload(fb1_model, messages, LLM_TEMPERATURE, 500)
        print(f"  🧠 LLM → {fb1_model} (reasoning + tool_calls)...")
        result = _do_api_call(LLM_FALLBACK1_BASE_URL, LLM_FALLBACK1_API_KEY,
                              fb1_model, payload_fb1, timeout)
        if result:
            result['provider'] = 'nous'
            return result
        print(f"  ⚠️ {fb1_model} also failed")

    return None


def rule_based_backup(analysis):
    """
    Rule-based backup analyzer — fires when ALL LLM providers are down.
    Uses technical indicators already available in the analysis dict.
    Much more conservative than fail-open: requires alignment across
    multiple indicators to approve a trade.
    """
    symbol = analysis.get('symbol', '?')
    direction = analysis.get('direction', 'LONG')
    score = analysis.get('runner_score', 0)
    price_change = analysis.get('price_change', 0)
    change_1h = analysis.get('change_1h', 0)
    rsi = analysis.get('rsi', 50)
    vol_ratio = analysis.get('vol_ratio', 0)
    funding = analysis.get('funding_rate', 0)
    ema_21 = analysis.get('ema_21', 0)
    ema_50 = analysis.get('ema_50', 0)
    current = analysis.get('current', 0)
    macd_hist = analysis.get('macd_histogram', 0)
    breakout = analysis.get('breakout', False)

    # ── Gate 1: Score threshold ──────────────────────────────────────────
    if score < LLM_BACKUP_MIN_SCORE:
        return _backup_reject(symbol, direction,
            f"Score {score} < backup min {LLM_BACKUP_MIN_SCORE}")

    # ── Gate 2: Anti-chase ───────────────────────────────────────────────
    # Bear market SHORT: relax chase to 6% (dumps are normal)
    # Bull market LONG: relax chase to 6% (rallies are normal)
    _chase = LLM_BACKUP_MAX_CHASE
    if direction == 'SHORT' and price_change < 0:
        # In bear dumps, coins routinely fall 5-10% — 4% is too tight
        _chase = max(_chase, 6.0)
    if direction == 'LONG' and price_change > 0:
        # In bull rallies, coins pump 5-8% — 4% is too tight
        _chase = max(_chase, 6.0)
    if direction == 'LONG' and price_change > _chase:
        return _backup_reject(symbol, direction,
            f"Chase LONG: +{price_change:.1f}% > {_chase}%")
    if direction == 'SHORT' and price_change < -_chase:
        return _backup_reject(symbol, direction,
            f"Chase SHORT: {price_change:.1f}% < -{_chase}%")

    # ── Gate 3: RSI bounds ───────────────────────────────────────────────
    if direction == 'LONG':
        if rsi > LLM_BACKUP_MAX_RSI_LONG:
            return _backup_reject(symbol, direction,
                f"RSI {rsi:.1f} > {LLM_BACKUP_MAX_RSI_LONG} (overbought for LONG)")
        if rsi < LLM_BACKUP_MIN_RSI_LONG:
            return _backup_reject(symbol, direction,
                f"RSI {rsi:.1f} < {LLM_BACKUP_MIN_RSI_LONG} (falling knife)")
    else:
        if rsi < LLM_BACKUP_MIN_RSI_SHORT:
            return _backup_reject(symbol, direction,
                f"RSI {rsi:.1f} < {LLM_BACKUP_MIN_RSI_SHORT} (oversold for SHORT)")
        if rsi > LLM_BACKUP_MAX_RSI_SHORT:
            return _backup_reject(symbol, direction,
                f"RSI {rsi:.1f} > {LLM_BACKUP_MAX_RSI_SHORT} (squeeze risk)")

    # ── Gate 4: Volume ───────────────────────────────────────────────────
    if vol_ratio < LLM_BACKUP_MIN_VOL_RATIO:
        return _backup_reject(symbol, direction,
            f"Volume {vol_ratio:.1f}x < {LLM_BACKUP_MIN_VOL_RATIO}x")

    # ── Gate 5: Funding rate extremes ────────────────────────────────────
    if direction == 'LONG' and funding > LLM_BACKUP_MAX_FUNDING_LONG:
        return _backup_reject(symbol, direction,
            f"Funding {funding:.4f}% > {LLM_BACKUP_MAX_FUNDING_LONG}%")
    if direction == 'SHORT' and funding < LLM_BACKUP_MAX_FUNDING_SHORT:
        return _backup_reject(symbol, direction,
            f"Funding {funding:.4f}% < {LLM_BACKUP_MAX_FUNDING_SHORT}%")

    # ── Gate 6: Momentum alignment ───────────────────────────────────────
    if direction == 'LONG' and change_1h < -1.0:
        return _backup_reject(symbol, direction,
            f"1h momentum {change_1h:+.2f}% bearish vs LONG")
    if direction == 'SHORT' and change_1h > 1.0:
        return _backup_reject(symbol, direction,
            f"1h momentum {change_1h:+.2f}% bullish vs SHORT")

    # ── Gate 7: EMA confirmation ─────────────────────────────────────────
    if direction == 'LONG' and ema_50 > 0 and current < ema_50 * 0.97:
        return _backup_reject(symbol, direction,
            f"Price below EMA50*0.97 (downtrend)")
    if direction == 'SHORT' and ema_50 > 0 and current > ema_50 * 1.03:
        return _backup_reject(symbol, direction,
            f"Price above EMA50*1.03 (uptrend)")

    # ── All gates passed ─────────────────────────────────────────────────
    conf = 0.4
    reason_parts = [f"score={score}", f"RSI={rsi:.0f}", f"vol={vol_ratio:.1f}x", f"1h={change_1h:+.1f}%"]
    if breakout:
        reason_parts.append("breakout")
        conf += 0.1
    if vol_ratio > 2.0:
        conf += 0.1

    reason = f"🛡️ BACKUP OK: {', '.join(reason_parts)}"
    print(f"  🛡️ BACKUP APPROVED {symbol} {direction}: {reason}")

    return {
        'approved': True,
        'reason': reason,
        'confidence': min(conf, 0.6),
        'model': 'rule_based_backup',
        'provider': 'backup',
        'tokens_in': 0,
        'tokens_out': 0,
        'latency_ms': 0,
    }


def _backup_reject(symbol, direction, reason):
    full_reason = f"🛡️ BACKUP REJECT: {reason}"
    print(f"  🛡️ BACKUP REJECTED {symbol} {direction}: {reason}")
    return {
        'approved': False,
        'reason': full_reason,
        'confidence': 0.0,
        'model': 'rule_based_backup',
        'provider': 'backup',
        'tokens_in': 0,
        'tokens_out': 0,
        'latency_ms': 0,
    }


def parse_llm_response(content):
    """Parse JSON from LLM response. Returns dict or None."""
    if not content:
        return None

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

    if 'YES' in text.upper() and 'NO' not in text.upper().replace('YES', ''):
        return {'decision': 'YES', 'confidence': 0.5, 'reason': text[:100]}
    elif 'NO' in text.upper():
        return {'decision': 'NO', 'confidence': 0.5, 'reason': text[:100]}

    return None


def analyze_signal(analysis, force=False):
    """Main entry point — analyze a signal with LLM."""

    symbol = analysis.get('symbol', '')
    direction = analysis.get('direction', '')
    score = analysis.get('runner_score', 0)

    if not LLM_ENABLED and not force:
        return {
            'approved': True,
            'reason': 'LLM disabled',
            'model': None,
            'tokens_in': 0, 'tokens_out': 0, 'latency_ms': 0,
        }

    if score < LLM_MIN_SCORE and not force:
        return {
            'approved': True,
            'reason': f'Score {score} < {LLM_MIN_SCORE}, skipped LLM',
            'model': 'skipped', 'confidence': 0,
            'tokens_in': 0, 'tokens_out': 0, 'latency_ms': 0,
        }

    cache_key = _get_cache_key(symbol, direction, score)
    if _is_cache_valid(cache_key):
        cached = _analysis_cache[cache_key]
        print(f"  🧠 LLM cache hit: {symbol}")
        return cached['result']

    prompt = format_analysis_prompt(analysis)
    print(f"  🧠 LLM analyzing {symbol} {direction} (score:{score})...")

    start = time.time()
    response = call_llm(prompt)
    latency_ms = int((time.time() - start) * 1000)

    if not response:
        # ── All LLM providers failed — use backup mode ───────────────────
        if LLM_BACKUP_MODE == "fail_closed":
            result = {
                'approved': False,
                'reason': 'LLM unavailable + fail-closed mode',
                'model': LLM_MODEL, 'provider': None,
                'tokens_in': 0, 'tokens_out': 0, 'latency_ms': latency_ms,
            }
            print(f"  🔒 FAIL-CLOSED: rejected {symbol}")
        elif LLM_BACKUP_MODE == "fail_open":
            result = {
                'approved': True,
                'reason': 'LLM call failed, fail-open',
                'model': LLM_MODEL, 'provider': None,
                'tokens_in': 0, 'tokens_out': 0, 'latency_ms': latency_ms,
            }
            print(f"  ⚠️ FAIL-OPEN: approved {symbol}")
        else:
            result = rule_based_backup(analysis)
            result['latency_ms'] = latency_ms

        _analysis_cache[cache_key] = {'result': result, 'ts': time.time()}
        return result

    # ── Handle tool_call result (reasoning models) ───────────────────────
    if response.get('tool_call_result'):
        tc = response['tool_call_result']
        decision = tc.get('decision', 'YES').upper()
        approved = decision == 'YES'
        reason = tc.get('reason', 'No reason')
        confidence = tc.get('confidence', 0.5)

        result = {
            'approved': approved,
            'reason': reason,
            'confidence': confidence,
            'model': LLM_FALLBACK1_MODEL if response.get('provider') == 'fallback' else LLM_MODEL,
            'provider': response.get('provider', 'nous'),
            'tokens_in': response['tokens_in'],
            'tokens_out': response['tokens_out'],
            'latency_ms': latency_ms,
        }
        _analysis_cache[cache_key] = {'result': result, 'ts': time.time()}

        status = "✅ APPROVED" if approved else "❌ REJECTED"
        print(f"  🧠 LLM: {status} — {reason} ({latency_ms}ms)")
        return result

    # ── Handle content result (standard models) ──────────────────────────
    parsed = parse_llm_response(response['content'])

    if not parsed:
        # Parse failed — use backup mode
        if LLM_BACKUP_MODE == "fail_closed":
            result = {
                'approved': False,
                'reason': f'Parse failed: {response["content"][:80]}',
                'model': LLM_MODEL,
                'provider': response.get('provider', 'unknown'),
                'tokens_in': response['tokens_in'],
                'tokens_out': response['tokens_out'],
                'latency_ms': latency_ms,
            }
        elif LLM_BACKUP_MODE == "fail_open":
            result = {
                'approved': True,
                'reason': f'Parse failed: {response["content"][:80]}',
                'model': LLM_MODEL,
                'provider': response.get('provider', 'unknown'),
                'tokens_in': response['tokens_in'],
                'tokens_out': response['tokens_out'],
                'latency_ms': latency_ms,
            }
        else:
            result = rule_based_backup(analysis)
            result['latency_ms'] = latency_ms
            result['tokens_in'] = response['tokens_in']
            result['tokens_out'] = response['tokens_out']

        _analysis_cache[cache_key] = {'result': result, 'ts': time.time()}
        return result

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

    _analysis_cache[cache_key] = {'result': result, 'ts': time.time()}

    status = "✅ APPROVED" if approved else "❌ REJECTED"
    print(f"  🧠 LLM: {status} — {reason} ({latency_ms}ms)")

    return result


def batch_analyze(signals, max_concurrent=3):
    """Analyze multiple signals sequentially."""
    results = []
    for analysis in signals:
        result = analyze_signal(analysis)
        results.append((analysis, result))
    return results


# === CLI test ===
if __name__ == "__main__":
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
