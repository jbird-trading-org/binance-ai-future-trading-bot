#!/bin/bash
# Daily cron — TypeScript entry (extend scripts/daily-eval.ts when needed)
cd "$(dirname "$0")" && npm run test:pipeline >> logs/daily_cron.log 2>&1
