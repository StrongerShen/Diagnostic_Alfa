#!/usr/bin/env bash
# ==============================================================================
# Diagnostic_Alfa - ALFA AWUS036AXML 無線診斷工作台啟動腳本
# ==============================================================================

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

PORT=8080
VENV_DIR="$PROJECT_DIR/.venv"

echo "================================================================================"
echo "  🚀 正在啟動 Diagnostic_Alfa 無線診斷 Web 工作台..."
echo "================================================================================"

# 1. 檢查並初始化 Python 虛擬環境
if [ ! -d "$VENV_DIR" ]; then
    echo "📦 正在建立 Python 虛擬環境 (.venv)..."
    python3 -m venv "$VENV_DIR"
fi

PYTHON_BIN="$VENV_DIR/bin/python"
PIP_BIN="$VENV_DIR/bin/pip"

# 2. 檢查並安裝依賴
if [ -f "$PROJECT_DIR/requirements.txt" ]; then
    echo "🔍 檢查 Python 套件依賴..."
    "$PIP_BIN" install -q -r "$PROJECT_DIR/requirements.txt"
fi

# 3. 檢查 Port 8080 是否被佔用
OLD_PID=$(lsof -ti :$PORT 2>/dev/null || true)
if [ -n "$OLD_PID" ]; then
    echo "⚠️  偵測到連接埠 $PORT 已被背景行程 PID $OLD_PID 佔用，正在釋放..."
    kill -9 $OLD_PID 2>/dev/null || true
    sleep 1
fi

# 4. 偵測可用存取 IP
LOCAL_IP="127.0.0.1"

# 動態偵測 ALFA 網卡與主力連線介面
ALFA_DEV=$(ip -o link 2>/dev/null | awk -F': ' '/00:c0:ca:bb:0b:45/ {print $2}')
if [ -z "$ALFA_DEV" ]; then
    if ip link show wlx00c0cabb0b45 >/dev/null 2>&1; then
        ALFA_DEV="wlx00c0cabb0b45"
    else
        ALFA_DEV="wlan1"
    fi
fi

PRI_DEV=$(ip route show default 2>/dev/null | awk '{for(i=1;i<=NF;i++) if ($i=="dev") print $(i+1); exit}')
if [ -z "$PRI_DEV" ] || [ "$PRI_DEV" = "$ALFA_DEV" ]; then
    PRI_DEV="wlan0"
fi

AP_IP=$(ip -4 addr show dev "$ALFA_DEV" 2>/dev/null | awk '/inet / {print $2}' | cut -d/ -f1)
PRIMARY_IP=$(ip -4 addr show dev "$PRI_DEV" 2>/dev/null | awk '/inet / {print $2}' | cut -d/ -f1)

echo ""
echo "✅ Web 伺服器即將在背景啟動，可透過以下網址存取操作儀表板："
echo ""
echo "  ▸ 本機瀏覽器存取    : http://localhost:$PORT"
if [ -n "$AP_IP" ]; then
echo "  ▸ 手機/用戶端裝置存取 : http://$AP_IP:$PORT  (連線至 DiagnosticAP 後直接開啟)"
fi
if [ -n "$PRIMARY_IP" ]; then
echo "  ▸ 區網裝置存取      : http://$PRIMARY_IP:$PORT"
fi
echo ""
echo "按 Ctrl+C 可停止 Web 伺服器。"
echo "================================================================================"
echo ""

# 5. 啟動 Uvicorn 伺服器 (綁定 0.0.0.0 確保所有介面與手機均可連線，關閉重複的 HTTP 存取日誌)
exec "$PYTHON_BIN" -m uvicorn main:app --host 0.0.0.0 --port $PORT --no-access-log

