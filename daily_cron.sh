#!/bin/bash
cd /root/.openclaw/workspace/neko-futures-trader
source .env
python3 /root/.openclaw/workspace/neko-futures-trader/scripts/daily_eval.py
