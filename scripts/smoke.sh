#!/usr/bin/env bash
# Smoke test local (requer serviços no ar)
set -euo pipefail
BASE="${BACKEND_URL:-http://localhost:8000}"
echo "Health..."
curl -sf "$BASE/health" | head -c 200
echo
echo "OK"
