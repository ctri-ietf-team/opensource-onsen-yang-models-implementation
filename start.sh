#!/usr/bin/env bash
# ============================================================
#  L3VPN 无损映射应用 - 一键启动 (Linux / macOS)
#  双击运行，或终端执行:  ./start.sh
#  可用环境变量: PORT(默认8000) HOST(默认127.0.0.1)
# ============================================================
set -e
cd "$(dirname "$0")"          # 路径无关：无论包放在哪里都能运行

PORT="${PORT:-8000}"
HOST="${HOST:-127.0.0.1}"

command -v python3 >/dev/null 2>&1 || {
  echo "[错误] 未找到 python3，请先安装 Python 3.10+ (https://www.python.org)"
  exit 1
}

# 依赖检查：缺失时自动安装（需要网络，仅首次）
python3 - <<'PY' >/dev/null 2>&1 && HAVE_DEPS=1 || HAVE_DEPS=0
import fastapi, uvicorn, yangson, pyang
PY
if [ "$HAVE_DEPS" != "1" ]; then
  echo "[提示] 首次运行，正在安装依赖 (fastapi uvicorn yangson pyang)..."
  python3 -m pip install --user fastapi uvicorn yangson pyang || {
    echo "[错误] 依赖安装失败，请手动执行:"
    echo "       python3 -m pip install --user fastapi uvicorn yangson pyang"
    exit 1
  }
fi

echo "=============================================="
echo "  L3VPN 无损映射应用"
echo "  地址: http://$HOST:$PORT"
echo "  按 Ctrl+C 停止服务"
echo "=============================================="

# 延迟 2 秒自动打开浏览器（服务起来后）
( sleep 2; python3 -m webbrowser "http://$HOST:$PORT" >/dev/null 2>&1 || true ) &

exec python3 -m uvicorn app:app --host "$HOST" --port "$PORT"