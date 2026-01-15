# TradingAgents Frontend Dockerfile
# Stage 1: Build
FROM node:20-alpine AS builder

WORKDIR /app

# 复制依赖文件
COPY package*.json ./

# npm 换淘宝镜像源加速
RUN npm config set registry https://registry.npmmirror.com

# 安装依赖
RUN npm ci

# 复制源代码
COPY . .

# 构建参数（可在 docker-compose 中覆盖）
ARG VITE_API_URL=
ENV VITE_API_URL=$VITE_API_URL

# 构建
RUN npm run build

# Stage 2: Serve
FROM nginx:alpine

# 复制构建产物
COPY --from=builder /app/dist /usr/share/nginx/html

# 复制 nginx 配置
COPY nginx.conf /etc/nginx/conf.d/default.conf

# 暴露端口
EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
