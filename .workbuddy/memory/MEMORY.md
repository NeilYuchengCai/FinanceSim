# FinanceSim 项目长期记忆

## 项目概述
FinanceSim 是一个本地运行的离线优先金融市场模拟平台，从零开始构建一个具有真实金融数据初始状态、能够自主演化的多市场金融世界模拟系统。

## 技术栈
- Backend: Python 3.13+ / FastAPI / SQLAlchemy / SQLite
- Frontend: React 18 + TypeScript / Vite 5
- Testing: pytest

## 核心架构
12+ 核心引擎：Market Engine, Simulation Engine, Trading Engine, Matching Engine, Portfolio Engine, Risk Engine, Analytics Engine, Event Engine, News Engine, Economic Engine, Bond Engine, Data Engine, Search Engine

## 关键设计原则
1. 禁止硬编码假数据冒充真实功能
2. 金融逻辑必须准确 - 使用 decimal.Decimal 保证货币精度
3. Offline-First - 内置 fallback 数据支持离线运行
4. 数据标注明确 - REAL/HISTORICAL/SIMULATED/FALLBACK 必须区分
5. 确定性随机 - 同一 seed + 初始状态可重现相同模拟

## 当前进度 (2026-09-24)
- ✅ 后端测试全部通过 (27/27)
- ✅ Economic Engine 完成
- ✅ Bond Engine 完成
- ✅ Central Bank 货币政策完成
- ✅ News Engine 完成
- ✅ API路由已注册 (/economy, /bonds, /news)
- ✅ 后端导入成功
- ✅ 前端构建成功 (104 modules)
- ✅ Economy/Bonds/News 页面已连接真实 API
- ✅ 15个页面已完成
- 📝 待完成：FX完整数据、高级参与者(Bot)、事件传播引擎增强、全局搜索功能

## 文件位置
- 项目根目录: C://Users//Administrator//Desktop//金融//FinSim//
- 架构文档: C://Users//Administrator//Desktop//金融//.workbuddy//output//
