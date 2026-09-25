#!/bin/bash
# FinanceSim 部署脚本

set -e

echo "=== FinanceSim 部署 ==="

# 1. 后端启动
echo "启动后端服务..."
cd "$(dirname "$0")/backend"
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!
echo "后端 PID: $BACKEND_PID"

# 2. 前端构建并启动
echo "构建前端..."
cd "$(dirname "$0")/frontend"
npm run build

echo "启动前端预览..."
npm run preview -- --host 0.0.0.0 --port 5173 &
FRONTEND_PID=$!
echo "前端 PID: $FRONTEND_PID"

echo ""
echo "=========================================="
echo "FinanceSim 已启动!"
echo "前端: http://localhost:5173"
echo "后端 API: http://localhost:8000"
echo "API 文档: http://localhost:8000/docs"
echo "=========================================="

# 等待进程
wait
