# FinanceSim · 金融市场模拟器

一个在浏览器里运行的金融市场模拟项目。它把股票、债券、外汇、商品和宏观经济放进同一个可演化的世界里，用模拟时钟推进价格、成交和事件，主要用作学习和实验。

## 关于这个项目

这个项目由个人开发者在 **AI 辅助下完成**。我负责需求、设计与验收，大量编码工作借助 AI 工具完成。作为一个练习性质的作品，它在金融逻辑、系统设计和工程质量上都还有不少可以改进的地方，欢迎指点和贡献。

需要说明的是：这是一个**模拟器**，不是真实的交易系统。内置价格绝大多数是程序合成的；外部真实数据只是可选的能力，且失败会自动回退。**请不要把它用于任何真实的投资决策。**

## 它能做什么

- **多资产模拟**：股票、债券、外汇、商品、宏观经济指标在同一世界中演化。
- **交易与撮合**：限价单挂簿、市价单成交，计算买卖价差、手续费和大单冲击。
- **组合与风控**：持仓、盈亏、VaR、CVaR、夏普比率等基础分析。
- **事件传导**：新闻与事件按市场、行业、个股的相关性影响价格。
- **AI 交易员**：几种简单策略的模拟参与者，让市场有交互对象。
- **世界与快照**：保存、恢复、分支不同的模拟时间线。

## 技术栈

后端：Python 3.13+、FastAPI、SQLAlchemy（async）+ SQLite、pytest。
前端：React 18、TypeScript、Vite 5、Zustand、Recharts + lightweight-charts。

数据来源做了区分标注：`REAL`（外部实盘）、`HISTORICAL`（历史）、`SIMULATED`（合成）、`FALLBACK`（离线兜底）。默认离线优先，无网络也能运行。

## 快速开始

**Windows**：双击 `scripts/run.bat`。

**手动启动**：
```bash
# 后端（端口 8000）
cd backend
python -m uvicorn app.main:app --reload --port 8000

# 前端（端口 5174）
cd frontend
npm run dev
```
浏览器打开 http://localhost:5174 。

**Docker**：`docker-compose up` 。

依赖见 `backend/requirements.txt` 和 `frontend/package.json`。Python 建议 3.13+，Node 建议 22+。

## 测试

```bash
# 后端
cd backend && python -m pytest tests -q
# 前端
cd frontend && npm run build
```

编写时后端测试为 53 项通过、前端构建通过。环境不同可能需要先安装依赖。

## 已知不足

- 合成价格只追求"看起来合理"，不保证符合真实市场的统计规律。
- 外部数据源（CNBC / Frankfurter / FRED CSV / RSS）为免 key 的公开接口，稳定性取决于对方，随时可能失效。
- 项目仍在迭代，接口和行为可能变化。

## 许可证

本项目采用 **Apache License 2.0**，详见 [LICENSE](LICENSE)。
