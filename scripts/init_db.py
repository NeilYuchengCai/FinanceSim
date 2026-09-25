"""
FinanceSim 初始化脚本
创建默认世界和数据
"""
import asyncio
import sys
from pathlib import Path

# 添加 backend 到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.database import async_session_factory
from app.models import World, Asset
from sqlalchemy import select


async def init_database():
    """初始化数据库"""
    print("正在初始化 FinanceSim 数据库...")
    
    async with async_session_factory() as session:
        # 检查是否已有数据
        result = await session.execute(select(World))
        existing = result.scalars().first()
        if existing:
            print("✓ 数据库已初始化，跳过创建")
            return
        
        # 创建默认世界
        default_world = World(
            name="默认世界",
            description="FinanceSim 默认世界 - 适合新手入门",
            mode="demo",
            seed="demo123"
        )
        session.add(default_world)
        await session.flush()
        
        # 创建资产
        assets_data = [
            # A股
            {"ticker": "000001.SZ", "name": "平安银行", "sector": "金融", "exchange": "SZSE"},
            {"ticker": "000858.SZ", "name": "五粮液", "sector": "消费", "exchange": "SZSE"},
            {"ticker": "600519.SH", "name": "贵州茅台", "sector": "消费", "exchange": "SHSE"},
            {"ticker": "600036.SH", "name": "招商银行", "sector": "金融", "exchange": "SHSE"},
            {"ticker": "000333.SZ", "name": "美的集团", "sector": "制造业", "exchange": "SZSE"},
            {"ticker": "600276.SH", "name": "恒瑞医药", "sector": "医疗", "exchange": "SHSE"},
            {"ticker": "002415.SZ", "name": "海康威视", "sector": "科技", "exchange": "SZSE"},
            # 美股
            {"ticker": "AAPL", "name": "Apple", "sector": "科技", "exchange": "NASDAQ"},
            {"ticker": "MSFT", "name": "Microsoft", "sector": "科技", "exchange": "NASDAQ"},
            {"ticker": "GOOGL", "name": "Alphabet", "sector": "科技", "exchange": "NASDAQ"},
            {"ticker": "AMZN", "name": "Amazon", "sector": "科技", "exchange": "NASDAQ"},
            {"ticker": "TSLA", "name": "Tesla", "sector": "汽车", "exchange": "NASDAQ"},
            {"ticker": "NVDA", "name": "NVIDIA", "sector": "科技", "exchange": "NASDAQ"},
            # 外汇
            {"ticker": "EUR/USD", "name": "欧元/美元", "sector": "外汇", "exchange": "FX"},
            {"ticker": "GBP/USD", "name": "英镑/美元", "sector": "外汇", "exchange": "FX"},
            {"ticker": "USD/JPY", "name": "美元/日元", "sector": "外汇", "exchange": "FX"},
            {"ticker": "USD/CNY", "name": "美元/人民币", "sector": "外汇", "exchange": "FX"},
            # 债券
            {"ticker": "US10Y", "name": "美国10年国债", "sector": "债券", "exchange": "BOND"},
            {"ticker": "CN10Y", "name": "中国10年国债", "sector": "债券", "exchange": "BOND"},
        ]
        
        for asset_data in assets_data:
            asset = Asset(
                world_id=default_world.id,
                ticker=asset_data["ticker"],
                name=asset_data["name"],
                sector=asset_data["sector"],
                exchange=asset_data["exchange"],
                asset_type="equity" if asset_data["exchange"] != "FX" and asset_data["exchange"] != "BOND" else ("fx" if asset_data["exchange"] == "FX" else "bond"),
                initial_price=100.0 if asset_data["exchange"] in ["NASDAQ", "SHSE", "SZSE"] else 7.0 if asset_data["ticker"] == "USD/CNY" else 100.0
            )
            session.add(asset)
        
        await session.commit()
        print(f"✓ 创建默认世界: {default_world.name}")
        print(f"✓ 初始化 {len(assets_data)} 个资产")
        print()
        print("=" * 50)
        print("  FinanceSim 数据库初始化完成！")
        print("=" * 50)
        print()
        print("现在可以启动应用:")
        print("  双击 scripts/start.py")
        print()


if __name__ == "__main__":
    asyncio.run(init_database())
