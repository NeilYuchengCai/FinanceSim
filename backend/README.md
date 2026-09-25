# FinanceSim Backend

## 启动后端

```bash
# 激活虚拟环境
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # macOS/Linux

# 安装依赖
pip install -r requirements.txt

# 初始化数据库
python scripts/init_db.py

# 启动服务
uvicorn app.main:app --reload --port 8000
```

## API 端点

- `GET /api/v1/health` - 健康检查
- `GET /api/v1/worlds` - 世界列表
- `POST /api/v1/worlds` - 创建世界
- `GET /api/v1/assets` - 资产列表
- `POST /api/v1/assets` - 创建资产
- `GET /api/v1/trading/portfolio` - 投资组合
- `POST /api/v1/trading/orders` - 下单
- `GET /api/v1/simulation/{world_id}/status` - 模拟状态
- `POST /api/v1/simulation/{world_id}/start` - 开始模拟
- `GET /api/v1/analytics/returns/{ticker}` - 收益率
- `POST /api/v1/search` - 搜索

详细文档访问: http://localhost:8000/docs
