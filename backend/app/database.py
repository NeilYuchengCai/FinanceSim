"""
FinanceSim 数据库连接
"""
import logging

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text
from app.config import settings

logger = logging.getLogger(__name__)


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


async def _migrate_numeric_columns() -> None:
    """铁律②：把既有 SQLite 表中核心金融金额/价格列从 FLOAT 迁移为 NUMERIC。

    SQLite 不支持 ALTER COLUMN 直接改列类型，采用标准做法：
    「改名 -> 按 ORM 新 schema 建表 -> 拷贝数据 -> 删旧表」。
    既有数据原样拷贝（历史数据若已含 float 截断误差属可接受，新写入将精确）。
    一次性迁移：检测列为 FLOAT 才执行，迁移后再次启动直接跳过（幂等）。

    边界处理：
    - SQLite 给表改名时，显式索引**不会**跟着改名（仍占用 ix_trades_* 名字），
      新表重建同名索引会冲突；因此改名后用 PRAGMA index_list 逐个 DROP。
    - sqlite_autoindex_* 是主键/唯一约束的隐式索引，SQLite 会随表改名自动
      重命名为 sqlite_autoindex_<old>_*，且不允许手工 DROP，必须跳过。
    - 没有其它表通过外键引用 trades / user_economy，改名不产生悬挂引用。
    - 全部 DDL 在同一个 engine.begin() 事务内，中途失败整体回滚。
    """
    from app.models.order import Trade
    from app.models.economy import UserEconomy
    from sqlalchemy import inspect as sa_inspect, text

    # 需要迁移的 (表名, ORM 表对象, 需改为 NUMERIC 的列)
    targets = {
        "trades": (Trade.__table__, ["price", "quantity"]),
        "user_economy": (UserEconomy.__table__, ["cash"]),
    }

    # 反射必须在同步连接上下文内完成，否则会触发 MissingGreenlet
    def _reflect(sync_conn):
        insp = sa_inspect(sync_conn)
        info = {}
        for table_name in targets:
            if table_name in insp.get_table_names():
                info[table_name] = {
                    c["name"]: str(c["type"]).upper()
                    for c in insp.get_columns(table_name)
                }
        return info

    async with engine.begin() as conn:
        info = await conn.run_sync(_reflect)

        for table_name, (table_obj, cols_to_fix) in targets.items():
            col_types = info.get(table_name)
            if col_types is None:
                continue
            needs_migration = any(
                "FLOAT" in col_types.get(col, "") for col in cols_to_fix
            )
            if not needs_migration:
                continue

            logger.warning(
                "Migrating %s columns %s from FLOAT to NUMERIC (preserving data)",
                table_name, cols_to_fix,
            )
            col_names = [c.name for c in table_obj.columns]
            # 1) 旧表改名
            await conn.execute(text(f'ALTER TABLE "{table_name}" RENAME TO "{table_name}_old"'))
            # 2) 释放旧表占用的显式索引名（隐式 autoindex 不可删、且已自动改名）
            idx_rows = (await conn.execute(
                text(f'PRAGMA index_list("{table_name}_old")')
            )).fetchall()
            for idx_row in idx_rows:
                idx = idx_row[1]
                if idx and not idx.startswith("sqlite_autoindex"):
                    await conn.execute(text(f'DROP INDEX IF EXISTS "{idx}"'))
            # 3) 按 ORM 新 schema（NUMERIC）建新表（会重建同名索引）
            await conn.run_sync(lambda sync_conn, t=table_obj: t.create(sync_conn, checkfirst=False))
            # 4) 拷贝数据（列名与顺序均取自 ORM，旧表已由 _ensure_columns 补齐）
            await conn.execute(text(
                f'INSERT INTO "{table_name}" ({", ".join(col_names)}) '
                f'SELECT {", ".join(col_names)} FROM "{table_name}_old"'
            ))
            # 5) 删旧表
            await conn.execute(text(f'DROP TABLE "{table_name}_old"'))


async def init_db():
    """初始化数据库"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    if settings.DATABASE_URL.startswith("sqlite"):
        await _ensure_columns()
        # 铁律②：核心金融金额/价格列 FLOAT -> NUMERIC 一次性迁移
        await _migrate_numeric_columns()


async def get_session() -> AsyncSession:
    """获取数据库会话"""
    async with async_session_factory() as session:
        yield session


async def close_db():
    """关闭数据库连接"""
    await engine.dispose()
