# FinanceSim - 金融市场模拟器

一个功能完整的离线优先金融市场模拟平台，支持多市场、多资产类别的实时模拟交易。

## 🎯 项目特点

- **多市场支持**：股票、外汇、债券、商品、宏观经济
- **真实金融逻辑**：使用 Decimal 保证货币精度，确定性随机引擎
- **离线优先**：内置 fallback 数据，无需网络即可运行
- **专业级图表**：TradingView lightweight-charts + Recharts
- **高性能架构**：代码分割、路由懒加载、多阶段 Docker 构建

## 🚀 快速启动

### Windows (推荐)
```bash
双击 scripts/run.bat
```

### 手动启动
```bash
# 后端
cd backend
python -m uvicorn app.main:app --reload --port 8000

# 前端
cd frontend
npm run dev
```

### Docker
```bash
docker-compose up
```

访问 http://localhost:5173

## 📊 功能特性

### 市场引擎
- **股票市场**：OHLC 定价、订单撮合、组合管理
- **外汇市场**：8个货币对，支持冲击事件
- **债券市场**：收益率曲线、久期/凸性分析
- **商品市场**：10种商品，5种冲击类型
- **宏观经济**：GDP、CPI、利率、失业率模拟

### 高级功能
- **事件传播**：多级衰减（直接→行业→市场→宏观）
- **市场状态机**：CALM/BULL/BEAR/EUPHORIA/PANIC 等10种状态
- **AI 交易员**：4种策略（价值、成长、宏观、配对）
- **挑战模式**：6个预定义模板
- **世界快照**：保存/恢复/分支时间线

### 技术分析
- **指标引擎**：SMA、EMA、RSI、MACD
- **风险度量**：VaR、CVaR、Sharpe Ratio
- **可视化**：K线图、成交量、技术指标叠加

## 🏗️ 技术栈

### 后端
- Python 3.13+ / FastAPI
- SQLAlchemy + SQLite (async)
- Pytest 测试框架

### 前端
- React 18 + TypeScript
- Vite 5 构建工具
- Zustand 状态管理
- Recharts + lightweight-charts

## 📈 当前进度

- ✅ Phase 1-7：核心框架、交易市场、分析引擎
- ✅ Phase 8：高级参与者（AI 交易员）
- ✅ Phase 9：全球资产（商品市场）
- ✅ Phase 10：性能优化 + QA
- ✅ 后端测试：27/27 通过
- ✅ 前端构建：成功
- ✅ 离线模式：完整支持

## 🔧 开发指南

### 添加新市场
1. 在 `backend/app/engines/` 创建新引擎
2. 在 `backend/app/routers/` 添加 API 路由
3. 在 `frontend/src/pages/` 创建页面组件
4. 在 `frontend/src/routes.ts` 注册路由
5. 在 `frontend/src/App.tsx` 添加导航项

### 运行测试
```bash
# 后端测试
python -m pytest backend/tests/ -v

# 前端测试
cd frontend && npm test
```

## 📄 许可证

MIT License
