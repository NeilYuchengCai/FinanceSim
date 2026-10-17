"""
FinanceSim 数据库连接
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text
from app.config import settings


class Base(DeclarativeBase):
    """基础模型类"""
    pass


# 创建异步引擎
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    future=True
)

# 创建会话工厂
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)


async def _ensure_columns() -> None:
    """为既有 SQLite 表补齐模型新增的列（幂等，仅 ADD COLUMN，不动数据）。

    create_all 只会建缺失的表，不会给已存在的表加列；模型演进时靠这里
    以 "PRAGMA table_info + ALTER TABLE ADD COLUMN" 的方式安全补齐。
    """
    from app.models import Base  # 延迟导入，确保所有模型已注册

    for table in Base.metadata.sorted_tables:
        async with engine.begin() as conn:
            rows = (await conn.execute(
                text(f"PRAGMA table_info({table.name})")
            )).fetchall()
            if not rows:
                continue  # 表不存在，交给 create_all 创建
            existing = {r[1] for r in rows}
            missing = [c for c in table.columns
                       if c.name not in existing and not c.primary_key]
            if not missing:
                continue
            for column in missing:
                col_type = column.type.compile(engine.dialect)
                default_sql = ""
                if column.default is not None and not callable(column.default.arg):
                    arg = column.default.arg
                    if isinstance(arg, str):
                        default_sql = f" DEFAULT '{arg}'"
                    else:
                        default_sql = f" DEFAULT {arg}"
                await conn.execute(
                    text(f"ALTER TABLE {table.name} "
                         f"ADD COLUMN {column.name} {col_type}{default_sql}")
                )


async def init_db():
    """初始化数据库"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    if settings.DATABASE_URL.startswith("sqlite"):
        await _ensure_columns()


async def get_session() -> AsyncSession:
    """获取数据库会话"""
    async with async_session_factory() as session:
        yield session


async def close_db():
    """关闭数据库连接"""
    await engine.dispose()
