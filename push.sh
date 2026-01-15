#!/bin/bash
# 一键推送到服务器
# 用法: ./push.sh [frontend|backend|all]

set -e

SERVER="root@120.77.57.92"
REMOTE_DIR="/opt/tradingagents"
LOCAL_DIR="$(cd "$(dirname "$0")" && pwd)"

# 颜色
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 默认推送全部
TARGET=${1:-all}

echo -e "${YELLOW}🚀 推送到服务器: $TARGET${NC}"

case $TARGET in
  frontend)
    echo "📦 打包前端（排除 node_modules）..."
    tar -czf /tmp/frontend.tar.gz --exclude='node_modules' --exclude='__pycache__' -C "$LOCAL_DIR" web-app/frontend
    echo "📤 上传中..."
    scp /tmp/frontend.tar.gz "$SERVER:$REMOTE_DIR/"
    ssh "$SERVER" "cd $REMOTE_DIR && tar -xzf frontend.tar.gz && rm frontend.tar.gz && cd web-app && docker compose build frontend && docker compose up -d frontend"
    ;;
  backend)
    echo "📦 打包后端..."
    tar -czf /tmp/backend.tar.gz --exclude='__pycache__' --exclude='data_cache' -C "$LOCAL_DIR" web-app/backend tradingagents requirements.txt
    echo "📤 上传中..."
    scp /tmp/backend.tar.gz "$SERVER:$REMOTE_DIR/"
    ssh "$SERVER" "cd $REMOTE_DIR && tar -xzf backend.tar.gz && rm backend.tar.gz && cd web-app && docker compose build backend && docker compose up -d backend"
    ;;
  all)
    echo "📦 打包全部（排除 node_modules）..."
    tar -czf /tmp/app.tar.gz --exclude='node_modules' --exclude='__pycache__' --exclude='data_cache' -C "$LOCAL_DIR" web-app tradingagents requirements.txt cli
    echo "📤 上传中..."
    scp /tmp/app.tar.gz "$SERVER:$REMOTE_DIR/"
    ssh "$SERVER" "cd $REMOTE_DIR && tar -xzf app.tar.gz && rm app.tar.gz && cd web-app && docker compose build && docker compose up -d"
    ;;
  *)
    echo "用法: ./push.sh [frontend|backend|all]"
    exit 1
    ;;
esac

echo -e "${GREEN}✅ 部署完成！${NC}"
echo "🌐 访问: http://120.77.57.92"
