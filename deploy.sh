#!/bin/bash
# TradingAgents-Chinese 一键部署脚本
# 服务器: 阿里云轻量 2核2G Docker

set -e

echo "=========================================="
echo "  TradingAgents-Chinese 一键部署"
echo "=========================================="

# 颜色
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 配置
APP_DIR="/opt/tradingagents"
REPO_URL="https://github.com/yourusername/TradingAgents-Chinese.git"

# 1. 系统准备
echo -e "${YELLOW}[1/6] 系统准备...${NC}"
apt-get update -qq || yum update -y -q
apt-get install -y -qq git curl || yum install -y -q git curl

# 2. 创建目录
echo -e "${YELLOW}[2/6] 创建应用目录...${NC}"
mkdir -p $APP_DIR
cd $APP_DIR

# 3. 创建 docker-compose.yml
echo -e "${YELLOW}[3/6] 创建 Docker 配置...${NC}"
cat > docker-compose.yml << 'DOCKER_EOF'
version: '3.8'

services:
  # 后端服务
  backend:
    build:
      context: .
      dockerfile: Dockerfile.backend
    container_name: ta-backend
    restart: unless-stopped
    ports:
      - "8000:8000"
    environment:
      - PYTHONUNBUFFERED=1
    env_file:
      - .env
    volumes:
      - ./data:/app/data
      - ./results:/app/results
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    deploy:
      resources:
        limits:
          memory: 1500M

  # 前端服务 (Nginx)
  frontend:
    build:
      context: .
      dockerfile: Dockerfile.frontend
    container_name: ta-frontend
    restart: unless-stopped
    ports:
      - "80:80"
    depends_on:
      - backend
    deploy:
      resources:
        limits:
          memory: 128M

networks:
  default:
    name: tradingagents-network
DOCKER_EOF

# 4. 创建后端 Dockerfile
echo -e "${YELLOW}[4/6] 创建 Dockerfile...${NC}"
cat > Dockerfile.backend << 'BACKEND_EOF'
FROM python:3.11-slim

WORKDIR /app

# 系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ curl && \
    rm -rf /var/lib/apt/lists/*

# Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制代码
COPY . .

# 健康检查端点
RUN echo 'from fastapi import FastAPI; app = FastAPI()' > /app/health_check.py

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "web-app.backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
BACKEND_EOF

# 前端 Dockerfile
cat > Dockerfile.frontend << 'FRONTEND_EOF'
FROM node:18-alpine AS builder
WORKDIR /app
COPY web-app/frontend/package*.json ./
RUN npm ci --silent
COPY web-app/frontend/ .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
FRONTEND_EOF

# Nginx 配置
cat > nginx.conf << 'NGINX_EOF'
server {
    listen 80;
    server_name _;

    root /usr/share/nginx/html;
    index index.html;

    # 前端路由
    location / {
        try_files $uri $uri/ /index.html;
    }

    # API 代理
    location /api/ {
        proxy_pass http://backend:8000/api/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_cache_bypass $http_upgrade;
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }

    # WebSocket 代理
    location /ws/ {
        proxy_pass http://backend:8000/ws/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 86400;
    }

    # Gzip
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml;
}
NGINX_EOF

# 5. 创建环境变量模板
echo -e "${YELLOW}[5/6] 创建环境变量...${NC}"
if [ ! -f .env ]; then
cat > .env << 'ENV_EOF'
# ===== LLM API =====
OPENAI_API_KEY=your_deepseek_api_key_here
OPENAI_BASE_URL=https://api.deepseek.com
DEFAULT_LLM_MODEL=deepseek-chat
DEEP_LLM_MODEL=deepseek-reasoner

# ===== 数据源 =====
TUSHARE_TOKEN=your_tushare_token_here

# ===== JWT =====
JWT_SECRET=change_this_to_random_string_in_production

# ===== 可选: Memory =====
ENABLE_MEMORY=false
ENV_EOF
echo -e "${RED}请编辑 .env 文件填入你的 API Key！${NC}"
echo -e "  nano $APP_DIR/.env"
fi

# 6. 添加 Swap (2G内存优化)
echo -e "${YELLOW}[6/6] 配置 Swap...${NC}"
if [ ! -f /swapfile ]; then
    fallocate -l 2G /swapfile
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    echo '/swapfile none swap sw 0 0' >> /etc/fstab
    echo -e "${GREEN}已添加 2G Swap${NC}"
fi

echo ""
echo "=========================================="
echo -e "${GREEN}部署准备完成！${NC}"
echo "=========================================="
echo ""
echo "下一步操作："
echo ""
echo "1. 上传代码到服务器："
echo "   scp -r /path/to/TradingAgents-Chinese/* root@120.77.57.92:$APP_DIR/"
echo ""
echo "2. 编辑环境变量："
echo "   nano $APP_DIR/.env"
echo ""
echo "3. 启动服务："
echo "   cd $APP_DIR && docker-compose up -d --build"
echo ""
echo "4. 查看日志："
echo "   docker-compose logs -f"
echo ""
echo "访问地址: http://120.77.57.92"
echo ""
