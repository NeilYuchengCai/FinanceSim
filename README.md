# FinanceSim - 金融市场模拟平台

## 项目概述

FinanceSim 是一个本地运行的离线优先金融市场模拟平台，从零开始构建一个具有真实金融数据初始状态、能够自主演化的多市场金融世界模拟系统。

## 技术栈

### 后端
- Python 3.12+
- FastAPI (异步Web框架)
- SQLAlchemy 2.0 (ORM)
- SQLite (本地数据库)
- Pydantic (数据验证)
- pytest (测试框架)

### 前端
- React 18 + TypeScript
- Vite (构建工具)
- Zustand (状态管理)
- React Router (路由)
- Recharts (图表库)
- Lightweight Charts (专业金融图表)

## 项目结构

```
FinSim/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                  # FastAPI 应用入口
│   │   ├── config.py                # 配置管理
│   │   ├── database.py              # 数据库连接
│   │   ├── engines/
│   │   │   ├── market_engine.py      # 市场状态引擎
│   │   │   ├── matching_engine.py    # 订单撮合引擎
│   │   │   ├── trading_engine.py     # 交易引擎
│   │   │   ├── portfolio_engine.py   # 持仓引擎
│   │   │   ├── simulation_engine.py  # 模拟时钟
│   │   │   ├── event_engine.py       # 事件引擎
│   │   │   └── analytics_engine.py   # 分析引擎
│   │   ├── models/
│   │   │   ├── base.py               # 基础模型
│   │   │   ├── world.py              # 世界模型
│   │   │   ├── asset.py              # 资产模型
│   │   │   ├── order.py              # 订单/持仓模型
│   │   │   ├── economy.py            # 经济模型
│   │   │   └── event.py              # 事件/新闻模型
│   │   ├── schemas/
│   │   │   └── __init__.py           # Pydantic Schema
│   │   ├── routers/
│   │   │   ├── worlds.py             # 世界管理 API
│   │   │   ├── assets.py             # 资产管理 API
│   │   │   ├── trading.py            # 交易 API
│   │   │   ├── simulation.py         # 模拟控制 API
│   │   │   ├── analytics.py          # 分析 API
│   │   │   ├── events.py             # 事件/新闻 API
│   │   │   └── search.py             # 搜索 API
│   │   └── data/
│   │       └── fallback_data.py      # 内置数据
│   ├── tests/
│   │   └── test_engines.py           # 核心引擎测试
│   └── scripts/
│       └── init_db.py                # 数据库初始化脚本
├── frontend/
│   ├── src/
│   │   ├── App.tsx                   # 主应用组件
│   │   ├── main.tsx                  # 入口文件
│   │   ├── index.css                 # 全局样式
│   │   ├── pages/
│   │   │   ├── Overview.tsx          # 首页概览
│   │   │   ├── Markets.tsx           # 市场页面
│   │   │   ├── Equities.tsx          # 股票页面
│   │   │   ├── FX.tsx                # 外汇页面
│   │   │   ├── Bonds.tsx             # 债券页面
│   │   │   ├── Portfolio.tsx         # 投资组合页面
│   │   │   ├── Orders.tsx            # 订单管理页面
│   │   │   ├── News.tsx              # 新闻页面
│   │   │   ├── Search.tsx            # 搜索页面
│   │   │   ├── Analytics.tsx         # 分析页面
│   │   │   ├── Economy.tsx           # 宏观经济页面
│   │   │   ├── Simulation.tsx        # 模拟控制页面
│   │   │   ├── Challenges.tsx        # 挑战任务页面
│   │   │   ├── Settings.tsx          # 设置页面
│   │   │   └── WorldCreator.tsx      # 世界创建页面
│   │   └── hooks/                    # 自定义 hooks
│   └── package.json
│   └── tsconfig.json
│   └── vite.config.ts
│   └── index.html
├── ARCHITECTURE.md                   # 架构设计文档
├── DATABASE.md                       # 数据库设计
├── API_SPEC.md                       # API 规范
├── SIMULATION.md                     # 模拟引擎设计
├── ANALYTICS.md                      # 分析引擎设计
├── DATA_SOURCES.md                   # 数据源设计
├── TESTING.md                        # 测试策略
├── ROADMAP.md                        # 开发路线图
└── README.md                         # 本文件
```

## 核心架构

### 引擎系统

1. **Market Engine** - 市场状态管理，支持10种市场状态（CALM, BULL, BEAR, EUPHORIA, CORRECTION, PANIC, CRISIS, RECOVERY, RISK_ON, RISK_OFF）
2. **Matching Engine** - 订单簿和撮合引擎，支持市价单、限价单、止损单
3. **Trading Engine** - 交易规则管理
4. **Portfolio Engine** - 持仓和资金管理
5. **Simulation Engine** - 模拟时钟，支持暂停、播放、变速
6. **Event Engine** - 事件生成和传播系统
7. **Analytics Engine** - 金融分析（收益率、波动率、VaR、Sharpe比率等）

### 数据模型

- World (世界)
- Asset (资产：股票、ETF、指数、外汇、债券)
- PriceHistory (价格历史)
- Order (订单)
- Trade (成交)
- Position (持仓)
- UserEconomy (用户经济)
- Event (事件)
- News (新闻)
- MacroSnapshot (宏观快照)

## 启动方式

### 后端启动

```bash
cd backend
python -m venv venv
venv/Scripts/activate  # Windows
source venv/bin/activate  # macOS/Linux
pip install -r requirements.txt
python scripts/init_db.py
uvicorn app.main:app --reload --port 8000
```

### 前端启动

```bash
cd frontend
npm install
npm run dev
```

### 访问应用

打开浏览器访问 http://localhost:5173

## API 文档

后端启动后访问 http://localhost:8000/docs 查看 Swagger UI

## 关键 API 端点

- `POST /api/v1/worlds` - 创建世界
- `GET /api/v1/worlds` - 世界列表
- `POST /api/v1/assets` - 创建资产
- `GET /api/v1/assets` - 资产列表
- `POST /api/v1/trading/orders` - 下单
- `GET /api/v1/trading/portfolio` - 获取投资组合
- `GET /api/v1/simulation/{world_id}/status` - 获取模拟状态
- `POST /api/v1/simulation/{world_id}/start` - 开始模拟
- `GET /api/v1/analytics/returns/{ticker}` - 获取收益率
- `POST /api/v1/search` - 全局搜索

## 测试

```bash
# 运行测试
cd backend
python -m pytest tests/ -v

# 带覆盖率
pytest tests/ --cov=app --cov-report=html
```

## 项目状态

### Phase 1: 基础框架 ✅ (已完成)
- [x] FastAPI 项目初始化
- [x] SQLAlchemy + SQLite 配置
- [x] World/Asset/Order/Trade/Position 模型
- [x] Market Engine (市场状态机)
- [x] Matching Engine (订单撮合)
- [x] Trading Engine (交易引擎)
- [x] Portfolio Engine (持仓引擎)
- [x] Simulation Clock (模拟时钟)
- [x] Event Engine (事件引擎)
- [x] Analytics Engine (分析引擎)
- [x] REST API 路由
- [x] 基础前端页面
- [x] 单元测试

### Phase 2-10: 待实现

## 新增功能 (Phase 6-10)

### Phase 6: 新闻引擎增强
- [x] Daily Summary API — 按日期生成新闻摘要
- [x] Impact Summary API — 市场影响摘要
- [x] Breaking News 标识

### Phase 7: 事件传播引擎
- [x] 多级传播：direct → sector → market → macro
- [x] Event Timeline 页面
- [x] 时间线页面集成 OHLC 图表

### Phase 8: 高级 Bot 策略
- [x] 价值投资 (value)
- [x] 成长投资 (growth)
- [x] 宏观策略 (macro)
- [x] 配对交易 (pairs)

### Phase 9: 全局搜索
- [x] Command Palette (⌘/Ctrl+K)
- [x] 快捷键导航

### Phase 10: UX 优化
- [x] Dark/Light 主题切换
- [x] 数据源标签 (REAL/HISTORICAL/SIMULATED/FALLBACK)
- [x] 键盘快捷键提示

### Phase 11: World Snapshot/Load/Branch
- [x] 快照创建 API
- [x] 快照恢复 API
- [x] 快照分支 API
- [x] World 管理页面

### Phase 12: Challenge 模式
- [x] 6种预置挑战模板
- [x] 挑战进度记录
- [x] Challenges 页面

## 注意事项

- **SIMULATION ≠ FORECAST**: 模拟器产生的是合理但不可预测的市场，不是真实预测
- **数据标注**: UI 中会明确标注数据来源（REAL/HISTORICAL/SIMULATED/FALLBACK）
- **Offline-First**: 系统使用内置 fallback 数据，无网络也能运行

## 许可证

MIT License
