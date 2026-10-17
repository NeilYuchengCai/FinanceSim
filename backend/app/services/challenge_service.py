"""
FinanceSim 挑战自动评估服务

每日模拟推进时，按挑战的 constraints 逐项评估真实组合/行情数据，
写入 ChallengeProgress（按 challenge_id + day 幂等），并在到达目标天数
或约束被破坏时更新 Challenge.status。

评估口径（全部来自真实数据，缺失的指标不假装达标）：
- total_return              组合总收益率（相对 World.starting_capital）
- return_over_benchmark     组合收益率 - 基准标的收益率（price_history 首末收盘）
- max_drawdown              组合净值历史最大回撤（由逐日进度序列计算）
- avg_pe                    持仓市值加权平均 PE（Asset.fundamentals.pe_ratio）
- holdings_count            持仓数量
- dividend_yield            持仓市值加权平均股息率（fundamentals.dividend_yield）
- sharpe_ratio              逐日收益序列年化夏普（需 >= 2 个收益点）
"""
import logging
import math
from typing import Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Asset, Challenge, ChallengeProgress, PriceHistory, World

logger = logging.getLogger(__name__)

TRADING_DAYS_PER_YEAR = 252

# 约束键 -> (指标键, 比较方向)。比较方向 ">=" 表示指标需不低于阈值，
# "<=" 表示指标需不高于阈值（如最大回撤）。
CONSTRAINT_SPECS: Dict[str, tuple] = {
    "target_return": ("total_return", ">="),
    "min_return_over_benchmark": ("return_over_benchmark", ">="),
    "max_drawdown": ("max_drawdown", "<="),
    "avg_pe_threshold": ("avg_pe", "<="),
    "min_holdings": ("holdings_count", ">="),
    "min_dividend_yield": ("dividend_yield", ">="),
    "min_sharpe_ratio": ("sharpe_ratio", ">="),
}


async def evaluate_world_challenges(world_id: int, day: int, session: AsyncSession) -> None:
    """评估指定世界全部 active 挑战并落一条当日进度。

    任何单个挑战的评估失败只记录日志，不影响其他挑战与模拟主流程。
    """
    result = await session.execute(
        select(Challenge).where(
            Challenge.world_id == world_id,
            Challenge.status == "active",
        )
    )
    challenges = result.scalars().all()
    if not challenges:
        return

    world = await session.get(World, world_id)
    starting_capital = float(getattr(world, "starting_capital", None) or 100000.0)

    for challenge in challenges:
        try:
            await _evaluate_one(challenge, world_id, day, starting_capital, session)
        except Exception as e:  # noqa: BLE001 - 单挑战失败不拖垮每日模拟
            logger.warning(
                "Challenge %s evaluation failed on day %s: %s", challenge.id, day, e
            )


async def _evaluate_one(
    challenge: Challenge,
    world_id: int,
    day: int,
    starting_capital: float,
    session: AsyncSession,
) -> None:
    """评估单个挑战：计算指标 -> 判定约束 -> 写进度 -> 更新状态。"""
    constraints = challenge.constraints or {}
    if not isinstance(constraints, dict):
        constraints = {}

    metrics = await _collect_metrics(
        world_id, day, starting_capital, constraints, challenge.id, session
    )

    passed_keys: List[str] = []
    failed_keys: List[str] = []
    unevaluable_keys: List[str] = []
    for c_key, (m_key, direction) in CONSTRAINT_SPECS.items():
        if c_key not in constraints:
            continue
        threshold = constraints[c_key]
        value = metrics.get(m_key)
        if value is None:
            unevaluable_keys.append(c_key)
            continue
        ok = value >= threshold if direction == ">=" else value <= threshold
        (passed_keys if ok else failed_keys).append(c_key)

    # 未知约束键同样记为不可评估（不假装达标，也不误判失败）
    for c_key in constraints:
        if c_key not in CONSTRAINT_SPECS:
            unevaluable_keys.append(c_key)

    # 状态判定：
    # 1) 硬失败约束（最大回撤被击穿）立即判负——回撤无法"恢复"；
    # 2) 到达目标天数：全部可评估约束通过 -> completed，否则 -> failed。
    new_status: Optional[str] = None
    notes = _build_notes(day, passed_keys, failed_keys, unevaluable_keys, metrics)
    if "max_drawdown" in failed_keys:
        new_status = "failed"
        notes = f"day {day}: FAILED early - max_drawdown constraint breached; {notes}"
    elif day >= challenge.target_days:
        new_status = "completed" if (passed_keys and not failed_keys) else "failed"

    # 幂等：先删同日旧进度再写新行（restore/快进会重复经过同一天）
    from sqlalchemy import delete as sql_delete

    await session.execute(
        sql_delete(ChallengeProgress).where(
            ChallengeProgress.challenge_id == challenge.id,
            ChallengeProgress.day == day,
        )
    )
    session.add(ChallengeProgress(
        challenge_id=challenge.id,
        day=day,
        metrics={k: v for k, v in metrics.items() if v is not None},
        notes=notes,
    ))

    if new_status and challenge.status == "active":
        challenge.status = new_status
        if new_status == "completed":
            from datetime import datetime

            challenge.completed_at = datetime.now()
        logger.info(
            "Challenge %s (%s) -> %s on day %s",
            challenge.id, challenge.name, new_status, day,
        )

    await session.commit()


async def _collect_metrics(
    world_id: int,
    day: int,
    starting_capital: float,
    constraints: Dict,
    challenge_id: int,
    session: AsyncSession,
) -> Dict[str, Optional[float]]:
    """收集当日真实指标；取不到的数据返回 None（不编造）。"""
    from app.routers.trading import get_portfolio_engine

    metrics: Dict[str, Optional[float]] = {
        "portfolio_value": None,
        "total_return": None,
        "return_over_benchmark": None,
        "max_drawdown": None,
        "avg_pe": None,
        "holdings_count": None,
        "dividend_yield": None,
        "sharpe_ratio": None,
        "benchmark_return": None,
    }

    portfolio = await get_portfolio_engine(world_id, session)
    perf = portfolio.get_performance()
    total_value = float(perf.get("total_value") or 0.0)
    metrics["portfolio_value"] = total_value
    if starting_capital > 0:
        metrics["total_return"] = (total_value - starting_capital) / starting_capital

    positions = portfolio.get_all_positions()
    metrics["holdings_count"] = float(len(positions)) if positions else 0.0

    # 持仓市值加权的 PE / 股息率（fundamentals 缺失的标的不计入加权）
    pe_value = 0.0
    pe_weight = 0.0
    dy_value = 0.0
    dy_weight = 0.0
    if positions:
        rows = (await session.execute(
            select(Asset.ticker, Asset.fundamentals).where(Asset.world_id == world_id)
        )).all()
        fundamentals = {t: (f or {}) for t, f in rows}
        for pos in positions:
            tk = pos.get("ticker")
            mv = float(pos.get("market_value") or 0.0)
            if not tk or mv <= 0:
                continue
            f = fundamentals.get(tk) or {}
            pe = f.get("pe_ratio")
            if isinstance(pe, (int, float)) and pe > 0:
                pe_value += float(pe) * mv
                pe_weight += mv
            dy = f.get("dividend_yield")
            if isinstance(dy, (int, float)) and dy >= 0:
                dy_value += float(dy) * mv
                dy_weight += mv
    if pe_weight > 0:
        metrics["avg_pe"] = pe_value / pe_weight
    if dy_weight > 0:
        metrics["dividend_yield"] = dy_value / dy_weight

    # 基准收益率：price_history 首末收盘（仅当约束里指定了 benchmark）
    benchmark = constraints.get("benchmark")
    if benchmark:
        bench_return = await _benchmark_return(world_id, str(benchmark), session)
        metrics["benchmark_return"] = bench_return
        if bench_return is not None and metrics["total_return"] is not None:
            metrics["return_over_benchmark"] = metrics["total_return"] - bench_return

    # 回撤 / 夏普：基于历史进度里的组合净值序列（含当日）
    history = await _portfolio_value_history(challenge_id, session)
    series = history + [total_value] if total_value else history
    if len(series) >= 2:
        peak = series[0]
        max_dd = 0.0
        for v in series:
            peak = max(peak, v)
            if peak > 0:
                max_dd = max(max_dd, (peak - v) / peak)
        metrics["max_drawdown"] = max_dd

        returns = [
            (series[i] - series[i - 1]) / series[i - 1]
            for i in range(1, len(series))
            if series[i - 1] > 0
        ]
        if len(returns) >= 2:
            mean_r = sum(returns) / len(returns)
            var_r = sum((r - mean_r) ** 2 for r in returns) / (len(returns) - 1)
            std_r = math.sqrt(var_r)
            if std_r > 0:
                metrics["sharpe_ratio"] = mean_r / std_r * math.sqrt(TRADING_DAYS_PER_YEAR)

    return metrics


async def _benchmark_return(
    world_id: int, benchmark: str, session: AsyncSession
) -> Optional[float]:
    """基准标的区间收益率：首根与末根 price_history 收盘价计算。"""
    rows = (await session.execute(
        select(PriceHistory.close, PriceHistory.timestamp)
        .join(Asset, Asset.id == PriceHistory.asset_id)
        .where(Asset.world_id == world_id, Asset.ticker == benchmark)
        .order_by(PriceHistory.timestamp.asc())
    )).all()
    if len(rows) < 2:
        return None
    first = rows[0][0]
    last = rows[-1][0]
    if not first or first <= 0 or last is None:
        return None
    return (float(last) - float(first)) / float(first)


async def _portfolio_value_history(
    challenge_id: int, session: AsyncSession
) -> List[float]:
    """该挑战已有进度里的组合净值序列（按 day 升序）。"""
    rows = (await session.execute(
        select(ChallengeProgress.metrics, ChallengeProgress.day)
        .where(ChallengeProgress.challenge_id == challenge_id)
        .order_by(ChallengeProgress.day.asc())
    )).all()
    out: List[float] = []
    for metrics, _day in rows:
        if isinstance(metrics, dict):
            v = metrics.get("portfolio_value")
            if isinstance(v, (int, float)):
                out.append(float(v))
    return out


def _build_notes(
    day: int,
    passed: List[str],
    failed: List[str],
    unevaluable: List[str],
    metrics: Dict[str, Optional[float]],
) -> str:
    """生成人类可读的当日评估摘要（写入 ChallengeProgress.notes）。"""

    def _fmt(value: Optional[float]) -> str:
        return "n/a" if value is None else f"{value:.4f}"

    parts = [
        f"day {day}: passed={len(passed)} failed={len(failed)} "
        f"unevaluable={len(unevaluable)}",
        f"total_return={_fmt(metrics.get('total_return'))}",
        f"portfolio_value={_fmt(metrics.get('portfolio_value'))}",
        f"max_drawdown={_fmt(metrics.get('max_drawdown'))}",
        f"holdings={_fmt(metrics.get('holdings_count'))}",
    ]
    if failed:
        parts.append(f"failed_keys={','.join(sorted(failed))}")
    if unevaluable:
        parts.append(f"unevaluable_keys={','.join(sorted(unevaluable))}")
    return "; ".join(parts)
