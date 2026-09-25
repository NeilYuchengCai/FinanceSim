"""
FinanceSim World Snapshot Service
快照管理：保存、恢复、分支世界状态
"""
import json
import logging
import uuid
from typing import Dict, List, Optional
from datetime import datetime as dt
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete as sql_delete

from app.models import World, Asset, PriceHistory, Order, Trade, Position, Event, News, MacroSnapshot, WorldSnapshot

logger = logging.getLogger(__name__)


class SnapshotService:
    """世界快照服务"""

    SNAPSHOT_TAG = "snapshotted"

    @staticmethod
    async def create_snapshot(
        session: AsyncSession,
        world_id: int,
        name: str,
        description: Optional[str] = None,
    ) -> Dict:
        """
        保存当前世界状态的完整快照
        只保存核心数据（资产、持仓、事件、新闻），不保存价格历史全部记录
        """
        world = await session.get(World, world_id)
        if not world:
            raise ValueError(f"World {world_id} not found")

        # 查询快照相关数据
        assets_result = await session.execute(
            select(Asset).where(Asset.world_id == world_id)
        )
        assets = assets_result.scalars().all()

        positions_result = await session.execute(
            select(Position).where(Position.world_id == world_id)
        )
        positions = positions_result.scalars().all()

        events_result = await session.execute(
            select(Event).where(Event.world_id == world_id).order_by(Event.created_at.desc()).limit(100)
        )
        events = events_result.scalars().all()

        news_result = await session.execute(
            select(News).where(News.world_id == world_id).order_by(News.created_at.desc()).limit(100)
        )
        news_list = news_result.scalars().all()

        macro_result = await session.execute(
            select(MacroSnapshot).where(MacroSnapshot.world_id == world_id)
            .order_by(MacroSnapshot.day.desc()).limit(10)
        )
        macro_snapshots = macro_result.scalars().all()

        # 构建摘要
        summary = {
            "day": world.current_day,
            "seed": world.seed,
            "asset_count": len(assets),
            "position_count": len(positions),
            "event_count": len(events),
            "news_count": len(news_list),
            "macro_days": len(macro_snapshots),
        }

        # 构建资产摘要（不含价格历史）
        asset_summaries = []
        for asset in assets:
            summary_data = {
                "id": asset.id,
                "ticker": asset.ticker,
                "type": asset.type,
                "name": asset.name,
                "sector": asset.sector,
                "currency": asset.currency,
                "market_cap": asset.market_cap,
                "beta": asset.beta,
                "volatility": asset.volatility,
                "fundamentals": asset.fundamentals,
            }
            # 获取最新价格
            ph_result = await session.execute(
                select(PriceHistory)
                .where(PriceHistory.asset_id == asset.id)
                .order_by(PriceHistory.timestamp.desc())
                .limit(1)
            )
            latest_ph = ph_result.scalar_one_or_none()
            if latest_ph:
                summary_data["latest_price"] = latest_ph.close
                summary_data["last_update"] = latest_ph.timestamp.isoformat()

            asset_summaries.append(summary_data)

        # 构建持仓摘要
        position_summaries = []
        for pos in positions:
            position_summaries.append({
                "asset_id": pos.asset_id,
                "quantity": pos.quantity,
                "avg_price": pos.avg_price,
                "unrealized_pnl": pos.unrealized_pnl,
            })

        # 构建事件摘要
        event_summaries = []
        for ev in events:
            event_summaries.append({
                "id": ev.id,
                "type": ev.type,
                "severity": ev.severity,
                "title": ev.title,
                "affected_assets": ev.affected_assets,
                "created_at": ev.created_at.isoformat(),
            })

        # 构建新闻摘要
        news_summaries = []
        for n in news_list:
            news_summaries.append({
                "id": n.id,
                "headline": n.headline,
                "importance": n.importance,
                "sentiment": n.sentiment,
                "created_at": n.created_at.isoformat(),
            })

        # 构建宏观快照摘要
        macro_summaries = []
        for ms in macro_snapshots:
            macro_summaries.append({
                "day": ms.day,
                "gdp_growth": ms.gdp_growth,
                "inflation": ms.inflation,
                "unemployment": ms.unemployment,
                "interest_rate": ms.interest_rate,
            })

        full_state = {
            "summary": summary,
            "assets": asset_summaries,
            "positions": position_summaries,
            "events": event_summaries,
            "news": news_summaries,
            "macro": macro_summaries,
        }

        # 保存到数据库
        snapshot = WorldSnapshot(
            world_id=world_id,
            name=name,
            description=description,
            snapshot_day=world.current_day,
            snapshot_seed=world.seed,
            summary_json=summary,
            full_state_json=json.dumps(full_state, default=str),
        )
        session.add(snapshot)
        await session.commit()
        await session.refresh(snapshot)

        logger.info(f"Created snapshot '{name}' for world {world_id} at day {world.current_day}")

        return {
            "id": snapshot.id,
            "world_id": snapshot.world_id,
            "name": snapshot.name,
            "description": snapshot.description,
            "snapshot_day": snapshot.snapshot_day,
            "created_at": snapshot.created_at.isoformat(),
            "summary": summary,
        }

    @staticmethod
    async def list_snapshots(
        session: AsyncSession,
        world_id: int,
    ) -> List[Dict]:
        """列出某个世界的所有快照"""
        result = await session.execute(
            select(WorldSnapshot)
            .where(WorldSnapshot.world_id == world_id)
            .order_by(WorldSnapshot.snapshot_day.desc())
        )
        snapshots = result.scalars().all()

        return [
            {
                "id": s.id,
                "world_id": s.world_id,
                "name": s.name,
                "description": s.description,
                "snapshot_day": s.snapshot_day,
                "created_at": s.created_at.isoformat(),
                "summary": s.summary_json,
            }
            for s in snapshots
        ]

    @staticmethod
    async def restore_snapshot(
        session: AsyncSession,
        world_id: int,
        snapshot_id: int,
    ) -> Dict:
        """
        恢复到指定快照（回滚到某一天）
        策略：
        1. 清除快照之后的所有事件和新闻
        2. 恢复资产价格历史到快照日
        3. 恢复持仓
        """
        snapshot = await session.get(WorldSnapshot, snapshot_id)
        if not snapshot or snapshot.world_id != world_id:
            raise ValueError("Snapshot not found")

        world = await session.get(World, world_id)
        if not world:
            raise ValueError(f"World {world_id} not found")

        state = json.loads(snapshot.full_state_json)

        # 更新世界状态
        world.current_day = snapshot.snapshot_day
        await session.commit()

        # 清除快照后的事件和新闻
        from sqlalchemy import delete as sql_delete
        await session.execute(
            sql_delete(Event).where(
                Event.world_id == world_id,
                Event.created_at > snapshot.created_at
            )
        )
        await session.execute(
            sql_delete(News).where(
                News.world_id == world_id,
                News.created_at > snapshot.created_at
            )
        )

        # 恢复资产最新价格（从快照中取每个资产的 latest_price）
        for asset_data in state.get("assets", []):
            ticker = asset_data.get("ticker")
            latest_price = asset_data.get("latest_price")
            if latest_price and ticker:
                asset_result = await session.execute(
                    select(Asset).where(Asset.world_id == world_id, Asset.ticker == ticker)
                )
                asset = asset_result.scalar_one_or_none()
                if asset:
                    # 删除该资产的所有价格历史，保留快照时的价格
                    await session.execute(
                        sql_delete(PriceHistory).where(PriceHistory.asset_id == asset.id)
                    )

        await session.commit()

        logger.info(f"Restored world {world_id} to snapshot '{snapshot.name}' (day {snapshot.snapshot_day})")

        return {
            "message": f"World restored to snapshot '{snapshot.name}'",
            "day": snapshot.snapshot_day,
            "snapshot_name": snapshot.name,
        }

    @staticmethod
    async def branch_world(
        session: AsyncSession,
        world_id: int,
        snapshot_id: int,
        new_world_name: str,
    ) -> Dict:
        """
        从快照分支创建新世界
        复制快照时的所有资产、持仓、事件、新闻到新世界
        """
        snapshot = await session.get(WorldSnapshot, snapshot_id)
        if not snapshot or snapshot.world_id != world_id:
            raise ValueError("Snapshot not found")

        state = json.loads(snapshot.full_state_json)

        # 创建新世界
        new_world = World(
            name=new_world_name,
            mode="simulation",
            seed=snapshot.snapshot_seed,
            current_day=snapshot.snapshot_day,
        )
        session.add(new_world)
        await session.flush()  # 获取 new_world.id
        new_world_id = new_world.id

        # 复制资产
        for asset_data in state.get("assets", []):
            asset = Asset(
                world_id=new_world_id,
                ticker=asset_data["ticker"],
                type=asset_data["type"],
                name=asset_data.get("name"),
                sector=asset_data.get("sector"),
                currency=asset_data.get("currency", "USD"),
                market_cap=asset_data.get("market_cap"),
                beta=asset_data.get("beta"),
                volatility=asset_data.get("volatility"),
                fundamentals=asset_data.get("fundamentals"),
            )
            session.add(asset)
        await session.flush()

        # 复制价格历史（使用快照中的 latest_price）
        asset_map = {}
        assets_result = await session.execute(
            select(Asset).where(Asset.world_id == new_world_id)
        )
        for a in assets_result.scalars():
            asset_map[a.ticker] = a

        for asset_data in state.get("assets", []):
            asset = asset_map.get(asset_data["ticker"])
            if asset and asset_data.get("latest_price"):
                from datetime import datetime as dt
                ph = PriceHistory(
                    asset_id=asset.id,
                    timestamp=dt.now(),
                    open=asset_data["latest_price"],
                    high=asset_data["latest_price"] * 1.01,
                    low=asset_data["latest_price"] * 0.99,
                    close=asset_data["latest_price"],
                    volume=0,
                    data_source="snapshot",
                    world_day=snapshot.snapshot_day,
                )
                session.add(ph)

        # 复制持仓
        for pos_data in state.get("positions", []):
            asset = asset_map.get(str(pos_data.get("asset_id")))
            if asset:
                position = Position(
                    world_id=new_world_id,
                    asset_id=asset.id,
                    quantity=pos_data.get("quantity", 0),
                    avg_price=pos_data.get("avg_price", 0),
                    last_price=pos_data.get("avg_price", 0),
                    unrealized_pnl=pos_data.get("unrealized_pnl", 0),
                )
                session.add(position)

        # 复制事件
        for ev_data in state.get("events", []):
            import uuid
            event = Event(
                id=str(uuid.uuid4()),
                world_id=new_world_id,
                type=ev_data.get("type", "UNKNOWN"),
                severity=ev_data.get("severity"),
                title=ev_data.get("title"),
                affected_assets=ev_data.get("affected_assets"),
                created_at=dt.now(),
            )
            session.add(event)

        # 复制新闻
        for news_data in state.get("news", []):
            import uuid
            news_item = News(
                id=str(uuid.uuid4()),
                world_id=new_world_id,
                headline=news_data.get("headline", ""),
                importance=news_data.get("importance", "MARKET"),
                sentiment=news_data.get("sentiment"),
                created_at=dt.now(),
            )
            session.add(news_item)

        await session.commit()
        await session.refresh(new_world)

        logger.info(
            f" Branched world {world_id} snapshot '{snapshot.name}' -> new world '{new_world_name}' (id={new_world_id}, day={new_world.current_day})"
        )

        return {
            "id": new_world.id,
            "name": new_world.name,
            "mode": new_world.mode,
            "current_day": new_world.current_day,
            "seed": new_world.seed,
            "branch_source": f"world_{world_id}_snapshot_{snapshot_id}",
        }
