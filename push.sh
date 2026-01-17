#!/bin/bash
# 一键推送到服务器
# 用法: ./push.sh [frontend|backend|all]

set -e

SERVER="root@120.77.57.92"
REMOTE_DIR="/opt/tradingagents"
LOCAL_DIR="$(cd "$(dirname "$0")" && pwd)"
CHANGELOG_FILE="$LOCAL_DIR/web-app/frontend/public/changelog.json"

# 颜色
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 更新日志函数
update_changelog() {
    echo ""
    echo -e "${BLUE}📋 当前更新日志:${NC}"
    if [ -f "$CHANGELOG_FILE" ]; then
        # 显示最近3条更新
        python3 -c "
import json
with open('$CHANGELOG_FILE', 'r') as f:
    data = json.load(f)
for item in data.get('updates', [])[:3]:
    print(f\"  [{item['type']}] {item['version']} - {item['title']}\")
"
    fi
    echo ""
    read -p "是否添加新的更新记录? (y/N): " add_changelog

    if [[ "$add_changelog" =~ ^[Yy]$ ]]; then
        echo ""
        read -p "版本号 (如 v0.1.3): " version
        echo "类型选择: 1=feature(新功能) 2=improve(优化) 3=fix(修复) 4=breaking(重大变更)"
        read -p "选择类型 (1-4): " type_choice

        case $type_choice in
            1) type="feature" ;;
            2) type="improve" ;;
            3) type="fix" ;;
            4) type="breaking" ;;
            *) type="feature" ;;
        esac

        read -p "标题 (简短描述): " title
        read -p "详细说明: " description

        # 更新 changelog.json
        python3 << PYTHON_EOF
import json
from datetime import datetime

with open('$CHANGELOG_FILE', 'r') as f:
    data = json.load(f)

new_entry = {
    "version": "$version",
    "date": datetime.now().strftime("%Y-%m-%d"),
    "type": "$type",
    "title": "$title",
    "description": "$description"
}

data['updates'].insert(0, new_entry)

with open('$CHANGELOG_FILE', 'w') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("✅ 更新日志已添加!")
PYTHON_EOF
        echo ""
    fi
}

# 默认推送全部
TARGET=${1:-all}

echo -e "${YELLOW}🚀 推送到服务器: $TARGET${NC}"

# 如果推送包含前端，提示更新日志
if [[ "$TARGET" == "frontend" || "$TARGET" == "all" ]]; then
    update_changelog
fi

# 同步 changelog.json 到后端 app 目录（确保被 Docker 复制）
cp -f "$CHANGELOG_FILE" "$LOCAL_DIR/web-app/backend/app/changelog.json"

case $TARGET in
  frontend)
    echo "📦 打包前端（排除 node_modules）..."
    tar -czf /tmp/frontend.tar.gz --exclude='node_modules' --exclude='__pycache__' -C "$LOCAL_DIR" web-app/frontend
    echo "📤 上传中..."
    scp /tmp/frontend.tar.gz "$SERVER:$REMOTE_DIR/"
    ssh "$SERVER" "cd $REMOTE_DIR && tar -xzf frontend.tar.gz && rm frontend.tar.gz && cd web-app && docker compose build --no-cache frontend && docker compose up -d frontend"
    ;;
  backend)
    echo "📦 打包后端..."
    tar -czf /tmp/backend.tar.gz --exclude='__pycache__' --exclude='data_cache' -C "$LOCAL_DIR" web-app/backend tradingagents requirements.txt
    echo "📤 上传中..."
    scp /tmp/backend.tar.gz "$SERVER:$REMOTE_DIR/"
    # 备份运行时配置 -> 解压 -> 恢复配置
    ssh "$SERVER" "cd $REMOTE_DIR && \
      mkdir -p /tmp/config_backup && \
      cp -f web-app/backend/config/admin_logs.json web-app/backend/config/api_stats.json web-app/backend/config/access_codes.json /tmp/config_backup/ 2>/dev/null || true && \
      tar -xzf backend.tar.gz && rm backend.tar.gz && \
      cp -f /tmp/config_backup/*.json web-app/backend/config/ 2>/dev/null || true && \
      cd web-app && docker compose build backend && docker compose up -d backend"
    ;;
  all)
    echo "📦 打包全部（排除 node_modules）..."
    tar -czf /tmp/app.tar.gz --exclude='node_modules' --exclude='__pycache__' --exclude='data_cache' -C "$LOCAL_DIR" web-app tradingagents requirements.txt cli
    echo "📤 上传中..."
    scp /tmp/app.tar.gz "$SERVER:$REMOTE_DIR/"
    # 备份运行时配置 -> 解压 -> 恢复配置
    ssh "$SERVER" "cd $REMOTE_DIR && \
      mkdir -p /tmp/config_backup && \
      cp -f web-app/backend/config/admin_logs.json web-app/backend/config/api_stats.json web-app/backend/config/access_codes.json /tmp/config_backup/ 2>/dev/null || true && \
      tar -xzf app.tar.gz && rm app.tar.gz && \
      cp -f /tmp/config_backup/*.json web-app/backend/config/ 2>/dev/null || true && \
      cd web-app && docker compose build --no-cache frontend && docker compose build backend && docker compose up -d"
    ;;
  *)
    echo "用法: ./push.sh [frontend|backend|all]"
    exit 1
    ;;
esac

echo -e "${GREEN}✅ 部署完成！${NC}"
echo "🌐 访问: http://120.77.57.92"
