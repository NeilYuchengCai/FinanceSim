"""
FinanceSim 数据库初始化脚本
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import engine
from app.models import Base


async def init_database():
    """初始化数据库"""
    async with engine.begin() as conn:
        # 创建所有表
        await conn.run_sync(Base.metadata.create_all)
        print("Database tables created successfully!")


if __name__ == "__main__":
    asyncio.run(init_database())
