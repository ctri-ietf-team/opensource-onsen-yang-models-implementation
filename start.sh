#!/usr/bin/env bash
# ============================================================
#  L3VPN YANG Models Mapping and Validation - one-click launcher (Linux / macOS)
#  Run:  ./start.sh
#  Optional env vars: PORT (default 8000), HOST (default 127.0.0.1)
# ============================================================
set -e
cd "$(dirname "$0")"          # 路径无关：无论包放在哪里都能运行

PORT="${PORT:-8000}"
HOST="${HOST:-127.0.0.1}"

command -v python3 >/dev/null 2>&1 || {
  echo "[ERROR] python3 not found. Please install Python 3.10+ first (https://www.python.org)"
  exit 1
}

# Dependency check: auto-install when missing (needs network, first run only)
python3 - <<'PY' >/dev/null 2>&1 && HAVE_DEPS=1 || HAVE_DEPS=0
import fastapi, uvicorn, yangson, pyang, python_multipart, wsproto
PY
if [ "$HAVE_DEPS" != "1" ]; then
  echo "[INFO] First run: installing dependencies from requirements.txt ..."
  python3 -m pip install --user -r requirements.txt || {
    echo "[ERROR] Dependency installation failed. Please run manually:"
    echo "       python3 -m pip install --user -r requirements.txt"
    exit 1
  }
fi

echo "=============================================="
echo "  L3VPN YANG Models Mapping and Validation"
echo "  URL: http://$HOST:$PORT"
echo "  Press Ctrl+C to stop the service"
echo "=============================================="

# 延迟 2 秒自动打开浏览器（服务起来后）
( sleep 2; python3 -m webbrowser "http://$HOST:$PORT" >/dev/null 2>&1 || true ) &

exec python3 -m uvicorn app:app --host "$HOST" --port "$PORT"