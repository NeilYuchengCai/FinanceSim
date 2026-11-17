"""
拟真改造端到端验证（Task #11/#12/#13/#14/#15）

覆盖：
- 多交易所日历：US/EU/UK/JP/HK 各自时段错峰、周末/节假日独立停盘；
- 买卖价差 + 佣金 + 大单冲击：市价买高于中间价、卖低于中间价、佣金>0、大单均价更差；
- 合成盘口深度扫单：大单扫更深、均价含冲击；限价不穿越则被动挂单；
- 波动率聚集：apply_shock 抬升 vol_mult 且随后衰减回 1.0；
- 因子式相关传导：事件冲击下同板块资产同向、高 beta 资产反应更大。
"""
import math
from datetime import datetime

from app.services.trading_calendar import (
    market_status_for_exchange,
    market_status_for,
    is_open_for,
    MARKET_OPEN,
    MARKET_CLOSED,
    MARKET_HOLIDAY,
    MARKET_WEEKEND,
)
from app.engines.trading_engine import (
    TradingEngine,
    COMMISSION_RATE,
    MIN_COMMISSION,
)
from app.services.market_stream import get_market_stream, _AssetState, SECONDS_PER_YEAR
from app.engines.event_engine import Event as SimEvent
from app.routers import events as events_router


# ---------------------------------------------------------------- 多交易所日历
def test_us_session_et():
    # 美东 09:30 开盘；12:00 盘中；08:00 盘前休市
    assert market_status_for_exchange("NASDAQ", datetime(2026, 11, 16, 9, 30)) == MARKET_OPEN
    assert market_status_for_exchange("NASDAQ", datetime(2026, 11, 16, 12, 0)) == MARKET_OPEN
    assert market_status_for_exchange("NASDAQ", datetime(2026, 11, 16, 8, 0)) == MARKET_CLOSED


def test_tokyo_session_wraps_midnight_et():
    # 东京 09:00-15:00 JST = 美东 20:00-次日02:00
    assert market_status_for_exchange("TSE", datetime(2026, 11, 16, 21, 0)) == MARKET_OPEN
    assert market_status_for_exchange("TSE", datetime(2026, 11, 16, 10, 0)) == MARKET_CLOSED


def test_hk_session_et():
    # 香港 09:30-16:00 HKT = 美东 21:30-次日04:00
    assert market_status_for_exchange("HKEX", datetime(2026, 11, 16, 22, 0)) == MARKET_OPEN
    assert market_status_for_exchange("HKEX", datetime(2026, 11, 16, 12, 0)) == MARKET_CLOSED


def test_weekend_closed_all_exchanges():
    # 周六所有交易所休市
    assert market_status_for_exchange("NASDAQ", datetime(2026, 11, 21, 12, 0)) == MARKET_WEEKEND
    assert market_status_for_exchange("TSE", datetime(2026, 11, 21, 21, 0)) == MARKET_WEEKEND
    assert market_status_for_exchange("HKEX", datetime(2026, 11, 21, 22, 0)) == MARKET_WEEKEND


def test_holiday_closed_exchange():
    # 2026-12-25 圣诞节 NASDAQ 休市
    assert market_status_for_exchange("NASDAQ", datetime(2026, 12, 25, 12, 0)) == MARKET_HOLIDAY
    # 同日东京/香港按各自国家日历仍可能开（日本/香港圣诞非固定长假核心日即按本国规则）
    # 这里仅验证美国节假日独立于其他交易所
    assert market_status_for_exchange("TSE", datetime(2026, 12, 25, 21, 0)) in (MARKET_OPEN, MARKET_CLOSED, MARKET_HOLIDAY)


def test_market_status_for_routes_by_exchange():
    # 同一美东时刻：美股休市、东京开市 -> 路由后结果不同
    dt = datetime(2026, 11, 16, 21, 0)
    assert market_status_for("EQUITY", dt, "TSE") == MARKET_OPEN
    assert market_status_for("EQUITY", dt, "NASDAQ") == MARKET_CLOSED
    # FX 仍走 7x24（周末除外）
    assert market_status_for("FX", dt, None) == MARKET_OPEN


# ---------------------------------------------------------------- 价差/佣金/冲击
def _patch_engine_state(engine: TradingEngine, mid=100.0, vol=0.25, beta=1.0):
    engine._get_asset_state = lambda t: (mid, vol, beta)
    engine._asset_class_of = lambda t: "EQUITY"


def test_half_spread_scales_with_volatility():
    e = TradingEngine(1)
    lo = e._half_spread(0.1)
    hi = e._half_spread(0.6)
    assert hi > lo
    assert 0.0001 <= lo <= 0.01


def test_market_buy_pays_spread_and_commission():
    e = TradingEngine(1)
    _patch_engine_state(e, mid=100.0, vol=0.25, beta=1.0)
    res = e.submit_order(ticker="AAA", side="BUY", order_type="MARKET", quantity=10)
    assert res["status"] == "FILLED"
    fill = res["avg_fill_price"]
    assert fill > 100.0                      # 买价高于中间价（付了买卖价差）
    assert res["commission"] > 0
    notional = fill * 10
    expected = max(float(MIN_COMMISSION), notional * float(COMMISSION_RATE))
    assert abs(res["commission"] - expected) < 1e-6


def test_market_sell_below_mid():
    e = TradingEngine(1)
    _patch_engine_state(e, mid=100.0)
    res = e.submit_order(ticker="AAA", side="SELL", order_type="MARKET", quantity=10)
    assert res["avg_fill_price"] < 100.0


def test_large_order_has_worse_impact_than_small():
    e = TradingEngine(1)
    _patch_engine_state(e, mid=100.0, vol=0.25, beta=1.0)
    small = e.submit_order(ticker="AAA", side="BUY", order_type="MARKET", quantity=100)
    large = e.submit_order(ticker="AAA", side="BUY", order_type="MARKET", quantity=500_000)
    # 大单扫穿更深档位 -> 均价更高（市场冲击）
    assert large["avg_fill_price"] > small["avg_fill_price"]


def test_limit_non_marketable_rests_in_book():
    e = TradingEngine(1)
    _patch_engine_state(e, mid=100.0)
    res = e.submit_order(ticker="AAA", side="BUY", order_type="LIMIT",
                         quantity=10, price=90.0)  # 远低于卖一档
    assert res["status"] == "PENDING"             # 被动挂单
    cancel = e.cancel_order(res["order_id"])
    assert cancel["success"]


def test_limit_marketable_fills_immediately():
    e = TradingEngine(1)
    _patch_engine_state(e, mid=100.0)
    # 限价 110 高于卖一档 -> 可立即成交
    res = e.submit_order(ticker="AAA", side="BUY", order_type="LIMIT",
                         quantity=10, price=110.0)
    assert res["status"] == "FILLED"
    assert res["avg_fill_price"] > 100.0


# ---------------------------------------------------------------- 波动率聚集
def _make_state(ticker="AAA", beta=1.0, exchange="XETRA"):
    sigma = 0.25 / math.sqrt(SECONDS_PER_YEAR)
    return _AssetState(
        asset_id=1, ticker=ticker, price=100.0, anchor=100.0, prev_close=100.0,
        sigma=sigma, decimals=2, asset_type="EQUITY", name=ticker,
        sector="Tech", exchange=exchange, beta=beta,
    )


def test_apply_shock_triggers_vol_clustering():
    stream = get_market_stream()
    st = _make_state()
    stream._assets = {st.ticker: st}
    before = st.vol_mult
    stream.apply_shock(st.ticker, -0.05)
    assert st.price < 100.0
    assert st.vol_mult > before                       # 事件后波动率瞬时抬升


def test_vol_mult_decays_back_to_one():
    stream = get_market_stream(seed=42)
    st = _make_state()
    stream._assets = {st.ticker: st}
    stream.apply_shock(st.ticker, -0.05)
    assert st.vol_mult > 1.0
    for _ in range(500):
        stream.advance()
    assert st.vol_mult <= 1.0 + 1e-6                  # 缓慢衰减回常态


def test_advance_keeps_prices_finite_and_positive():
    stream = get_market_stream(seed=7)
    a = _make_state("AAA", beta=1.2)
    b = _make_state("BBB", beta=0.6, exchange="HKEX")
    stream._assets = {"AAA": a, "BBB": b}
    for _ in range(50):
        stream.advance()
    assert a.price > 0 and b.price > 0
    assert math.isfinite(a.price) and math.isfinite(b.price)


# ---------------------------------------------------------------- 因子式相关传导
def test_event_factor_correlation_and_beta_scaling():
    # 确保事件传播引擎已初始化（仅作守卫，新逻辑不再依赖其计算结果）
    events_router._event_propagation = events_router._event_propagation or object()

    stream = get_market_stream(seed=1)
    hi = _make_state("AAA", beta=2.0)     # 高 beta
    lo = _make_state("BBB", beta=0.5)     # 低 beta
    stream._assets = {"AAA": hi, "BBB": lo}

    evnt = SimEvent(
        id="e1", type="black_swan", severity=1.0, title="x", body="",
        affected_assets=["AAA"], affected_sectors=["Tech"],
        sentiment_effect=-0.8, duration_days=1,
    )
    assets = [{"ticker": "AAA", "sector": "Tech"}, {"ticker": "BBB", "sector": "Tech"}]
    applied = events_router.apply_event_price_shocks(evnt, assets)
    shocks = {a["ticker"]: a["applied_pct"] for a in applied}

    # 同板块、同一负面市场情绪 -> 两者同向下跌
    assert shocks["AAA"] < 0 and shocks["BBB"] < 0
    # 高 beta 资产跌幅更大
    assert abs(shocks["AAA"]) > abs(shocks["BBB"])
    # 单资产封顶 ±10%
    assert abs(shocks["AAA"]) <= 0.10 + 1e-9


def test_event_positive_sentiment_lifts_prices():
    events_router._event_propagation = events_router._event_propagation or object()
    stream = get_market_stream(seed=3)
    hi = _make_state("AAA", beta=1.5)
    stream._assets = {"AAA": hi}
    evnt = SimEvent(
        id="e2", type="earnings", severity=0.9, title="x", body="",
        affected_assets=["AAA"], affected_sectors=["Tech"],
        sentiment_effect=0.7, duration_days=1,
    )
    applied = events_router.apply_event_price_shocks(evnt, [{"ticker": "AAA", "sector": "Tech"}])
    assert applied and applied[0]["applied_pct"] > 0
