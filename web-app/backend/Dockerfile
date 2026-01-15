# TradingAgents Backend Dockerfile
FROM python:3.12-slim

WORKDIR /app

# 换阿里云镜像源加速（适用于国内服务器）
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources && \
    sed -i 's/security.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# pip 换阿里云源
RUN pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/ && \
    pip config set install.trusted-host mirrors.aliyun.com

# 复制主项目依赖文件（TradingAgents 核心依赖）
# 构建上下文是项目根目录
COPY requirements.txt ./requirements-main.txt

# 复制 Web 依赖文件
COPY web-app/backend/requirements.txt ./requirements-web.txt

# 安装所有 Python 依赖
RUN pip install --no-cache-dir -r requirements-main.txt && \
    pip install --no-cache-dir -r requirements-web.txt

# 复制应用代码
COPY web-app/backend/app/ ./app/

# 环境变量
ENV PYTHONPATH=/app:/app/tradingagents
ENV PYTHONUNBUFFERED=1

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
