FROM node:20-alpine AS frontend-build

WORKDIR /app/frontend

# 复制package文件
COPY frontend/package*.json ./

# 安装依赖
RUN npm ci --no-audit --no-fund

# 复制源码
COPY frontend/ ./

# 构建前端
RUN npm run build

# 生产环境
FROM python:3.13-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 复制Python依赖
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY backend/ ./app/

# 复制前端构建产物
COPY --from=frontend-build /app/frontend/dist ./static

# 创建数据目录
RUN mkdir -p /app/data

# 环境变量
ENV PYTHONUNBUFFERED=1
ENV APP_ENV=production
ENV DATABASE_URL=sqlite:///./finance_sim.db

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# 启动命令
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--log-level", "info"]
