#!/bin/bash
# TradingAgents-Chinese 服务重启脚本
# 用法: ./restart.sh [backend|frontend|all]

set -e

PROJECT_DIR="/Users/qm/TradingAgents-Chinese"
BACKEND_DIR="$PROJECT_DIR/web-app/backend"
FRONTEND_DIR="$PROJECT_DIR/web-app/frontend"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
echo_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
echo_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 清理 Python 缓存
clean_cache() {
    echo_info "清理 Python 缓存..."
    find "$PROJECT_DIR" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find "$PROJECT_DIR" -name "*.pyc" -delete 2>/dev/null || true
    echo_info "缓存清理完成"
}

# 停止后端
stop_backend() {
    echo_info "停止后端服务..."
    pkill -f "uvicorn.*app.main" 2>/dev/null || true
    # 等待进程完全退出
    sleep 2
    # 检查端口是否释放
    if lsof -i :8000 > /dev/null 2>&1; then
        echo_warn "端口 8000 仍被占用，强制释放..."
        kill -9 $(lsof -t -i:8000) 2>/dev/null || true
        sleep 1
    fi
    echo_info "后端已停止"
}

# 启动后端
start_backend() {
    echo_info "启动后端服务..."
    cd "$BACKEND_DIR"

    # 使用 conda 环境的 Python 和 --reload 实现热更新
    PYTHONPATH="$PROJECT_DIR" nohup /opt/anaconda3/envs/tradingagents/bin/uvicorn app.main:app \
        --host 0.0.0.0 \
        --port 8000 \
        --reload \
        --reload-dir "$PROJECT_DIR/tradingagents" \
        --reload-dir "$BACKEND_DIR/app" \
        > "$PROJECT_DIR/logs/backend.log" 2>&1 &

    echo_info "后端已启动 (PID: $!)"
    echo_info "日志: $PROJECT_DIR/logs/backend.log"
}

# 停止前端
stop_frontend() {
    echo_info "停止前端服务..."
    pkill -f "vite" 2>/dev/null || true
    pkill -f "npm.*dev" 2>/dev/null || true
    sleep 1
    if lsof -i :5173 > /dev/null 2>&1; then
        kill -9 $(lsof -t -i:5173) 2>/dev/null || true
    fi
    echo_info "前端已停止"
}

# 启动前端
start_frontend() {
    echo_info "启动前端服务..."
    cd "$FRONTEND_DIR"
    nohup npm run dev > "$PROJECT_DIR/logs/frontend.log" 2>&1 &
    echo_info "前端已启动 (PID: $!)"
    echo_info "日志: $PROJECT_DIR/logs/frontend.log"
}

# 查看状态
show_status() {
    echo ""
    echo "========== 服务状态 =========="

    # 后端状态
    if pgrep -f "uvicorn.*app.main" > /dev/null; then
        echo -e "后端 (8000): ${GREEN}运行中${NC}"
    else
        echo -e "后端 (8000): ${RED}已停止${NC}"
    fi

    # 前端状态
    if pgrep -f "vite" > /dev/null; then
        echo -e "前端 (5173): ${GREEN}运行中${NC}"
    else
        echo -e "前端 (5173): ${RED}已停止${NC}"
    fi

    echo ""
    echo "========== 端口占用 =========="
    lsof -i :8000 2>/dev/null | head -3 || echo "端口 8000: 空闲"
    lsof -i :5173 2>/dev/null | head -3 || echo "端口 5173: 空闲"
    echo "=============================="
}

# 重启后端
restart_backend() {
    stop_backend
    clean_cache
    start_backend
}

# 重启前端
restart_frontend() {
    stop_frontend
    start_frontend
}

# 重启全部
restart_all() {
    stop_backend
    stop_frontend
    clean_cache
    start_backend
    start_frontend
}

# 创建日志目录
mkdir -p "$PROJECT_DIR/logs"

# 主逻辑
case "${1:-all}" in
    backend|b)
        restart_backend
        ;;
    frontend|f)
        restart_frontend
        ;;
    all|a)
        restart_all
        ;;
    stop)
        stop_backend
        stop_frontend
        ;;
    status|s)
        show_status
        exit 0
        ;;
    clean|c)
        clean_cache
        exit 0
        ;;
    *)
        echo "用法: $0 [backend|frontend|all|stop|status|clean]"
        echo ""
        echo "  backend, b  - 重启后端"
        echo "  frontend, f - 重启前端"
        echo "  all, a      - 重启全部 (默认)"
        echo "  stop        - 停止所有服务"
        echo "  status, s   - 查看服务状态"
        echo "  clean, c    - 仅清理缓存"
        exit 1
        ;;
esac

sleep 2
show_status

echo ""
echo_info "完成! 使用以下命令查看日志:"
echo "  tail -f $PROJECT_DIR/logs/backend.log"
echo "  tail -f $PROJECT_DIR/logs/frontend.log"
