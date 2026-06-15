#!/bin/bash
# Neko Futures Trader — TypeScript command helper
# Usage: ./neko.sh <command>

WORKDIR="$(cd "$(dirname "$0")" && pwd)"
cd "$WORKDIR" || exit 1

run_npm() {
  npm "$@"
}

case "$1" in
  pos|position)
    run_npm run positions
    ;;
  balance|bal)
    run_npm run balance
    ;;
  status)
    echo "🐱 Neko Futures Trader - Service Status"
    echo "========================================="
    systemctl status neko-scanner neko-monitor neko-dashboard --no-pager 2>/dev/null || \
      echo "systemd units not installed — use: npm run start:scanner|monitor|dashboard"
    ;;
  restart)
    systemctl restart neko-scanner neko-monitor neko-dashboard
    ;;
  restart-scanner) systemctl restart neko-scanner ;;
  restart-monitor) systemctl restart neko-monitor ;;
  restart-dashboard) systemctl restart neko-dashboard ;;
  stop) systemctl stop neko-scanner neko-monitor neko-dashboard ;;
  start) systemctl start neko-scanner neko-monitor neko-dashboard ;;
  sleep-on)
    export SLEEP_MODE=true
    grep -q '^SLEEP_MODE=' .env 2>/dev/null && sed -i 's/^SLEEP_MODE=.*/SLEEP_MODE=true/' .env || echo 'SLEEP_MODE=true' >> .env
    systemctl restart neko-scanner 2>/dev/null || true
    echo "✅ Sleep Mode ON (SLEEP_MODE=true in .env)"
    ;;
  sleep-off)
    export SLEEP_MODE=false
    grep -q '^SLEEP_MODE=' .env 2>/dev/null && sed -i 's/^SLEEP_MODE=.*/SLEEP_MODE=false/' .env || echo 'SLEEP_MODE=false' >> .env
    systemctl restart neko-scanner 2>/dev/null || true
    echo "✅ Sleep Mode OFF"
    ;;
  sleep-status)
    grep '^SLEEP_MODE=' .env 2>/dev/null || echo "SLEEP_MODE not set (default: false)"
    ;;
  logs-scanner) journalctl -u neko-scanner -f ;;
  logs-monitor) journalctl -u neko-monitor -f ;;
  logs-dashboard) journalctl -u neko-dashboard -f ;;
  test) run_npm test ;;
  pipeline) run_npm run test:pipeline ;;
  build) run_npm run build ;;
  help|*)
    echo "🐱 Neko Futures Trader (TypeScript)"
    echo "  pos / balance     — npm run positions / balance"
    echo "  test / pipeline   — npm test / npm run test:pipeline"
    echo "  build             — npm run build"
    echo "  sleep-on/off      — toggle SLEEP_MODE in .env"
    echo "  start:scanner     — npm run start:scanner"
    echo "  start:monitor     — npm run start:monitor"
    echo "  start:dashboard   — npm run start:dashboard"
    ;;
esac
