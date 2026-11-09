"""
FinanceSim Trading Calendar
美国市场交易日历：周末休市 + 主要节假日休市。

节假日一律按年份动态计算（不写死固定日期），跨年自动正确。
不引入任何第三方依赖，仅使用标准库 datetime。
"""
import logging
from datetime import date, datetime, timedelta
from functools import lru_cache
from typing import Union

logger = logging.getLogger(__name__)

DateLike = Union[datetime, date]

# 市场状态取值
MARKET_OPEN = "OPEN"
MARKET_CLOSED = "CLOSED"
MARKET_WEEKEND = "WEEKEND"
MARKET_HOLIDAY = "HOLIDAY"

# 常规交易时段（美东），用于区分 OPEN / CLOSED
MARKET_OPEN_TIME = (9, 30)    # 09:30
MARKET_CLOSE_TIME = (16, 0)   # 16:00

_WEEKDAY_NAMES = [
    "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday",
]


def _to_date(dt: DateLike) -> date:
    """同时接受 datetime 与 date，统一转成 date。"""
    if isinstance(dt, datetime):
        return dt.date()
    if isinstance(dt, date):
        return dt
    raise TypeError(f"Unsupported type for trading calendar: {type(dt)!r}")


def _observed(d: date) -> date:
    """
    固定日期假日的顺延规则：
    落在周六 -> 提前到前一个周五；落在周日 -> 顺延到下一个周一。
    """
    if d.weekday() == 5:      # Saturday
        return d - timedelta(days=1)
    if d.weekday() == 6:      # Sunday
        return d + timedelta(days=1)
    return d


def _nth_weekday(year: int, month: int, weekday: int, n: int) -> date:
    """某年某月第 n 个星期 weekday（weekday: 0=周一 ... 6=周日，n 从 1 开始）。"""
    first = date(year, month, 1)
    offset = (weekday - first.weekday()) % 7
    return first + timedelta(days=offset + (n - 1) * 7)


def _last_weekday(year: int, month: int, weekday: int) -> date:
    """某年某月最后一个星期 weekday。"""
    if month == 12:
        last = date(year, 12, 31)
    else:
        last = date(year, month + 1, 1) - timedelta(days=1)
    offset = (last.weekday() - weekday) % 7
    return last - timedelta(days=offset)


def _easter(year: int) -> date:
    """复活节（Anonymous Gregorian algorithm），用于推算耶稣受难日。"""
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    return date(year, month, day)


@lru_cache(maxsize=None)
def holidays_for_year(year: int) -> frozenset:
    """
    返回某一年的美国市场休市节假日集合（已含顺延后的观测日）。
    覆盖：元旦、马丁路德金日、总统日、耶稣受难日、阵亡将士纪念日、
          六月节、独立日、劳动节、感恩节、圣诞节。
    """
    items = [
        ("New Year's Day", _observed(date(year, 1, 1))),
        ("Martin Luther King Jr. Day", _nth_weekday(year, 1, 0, 3)),      # 1月第3个周一
        ("Washington's Birthday", _nth_weekday(year, 2, 0, 3)),           # 2月第3个周一
        ("Good Friday", _easter(year) - timedelta(days=2)),                # 复活节前2天（周五）
        ("Memorial Day", _last_weekday(year, 5, 0)),                       # 5月最后一个周一
        ("Juneteenth", _observed(date(year, 6, 19))),
        ("Independence Day", _observed(date(year, 7, 4))),
        ("Labor Day", _nth_weekday(year, 9, 0, 1)),                        # 9月第1个周一
        ("Thanksgiving Day", _nth_weekday(year, 11, 3, 4)),                # 11月第4个周四
        ("Christmas Day", _observed(date(year, 12, 25))),
    ]

    # 固定日期假日：顺延日之外，原始日期也计入（原日期若为周末已被 WEEKEND 覆盖，此处仅为语义完整）
    result = set()
    for _name, d in items:
        result.add(d)
    for name in ("New Year's Day", "Juneteenth", "Independence Day", "Christmas Day"):
        if name == "New Year's Day":
            result.add(date(year, 1, 1))
        elif name == "Juneteenth":
            result.add(date(year, 6, 19))
        elif name == "Independence Day":
            result.add(date(year, 7, 4))
        else:
            result.add(date(year, 12, 25))
    return frozenset(result)


@lru_cache(maxsize=None)
def holiday_names_for_year(year: int) -> dict:
    """返回 {date: 节假日名称}，便于前端/日志展示。"""
    names = {
        date(year, 1, 1): "New Year's Day",
        _nth_weekday(year, 1, 0, 3): "Martin Luther King Jr. Day",
        _nth_weekday(year, 2, 0, 3): "Washington's Birthday",
        _easter(year) - timedelta(days=2): "Good Friday",
        _last_weekday(year, 5, 0): "Memorial Day",
        date(year, 6, 19): "Juneteenth",
        date(year, 7, 4): "Independence Day",
        _nth_weekday(year, 9, 0, 1): "Labor Day",
        _nth_weekday(year, 11, 3, 4): "Thanksgiving Day",
        date(year, 12, 25): "Christmas Day",
    }
    # 顺延后的观测日同样带上名称
    for d, name in list(names.items()):
        obs = _observed(d)
        if obs != d:
            names.setdefault(obs, name)
    return names


def holiday_name(dt: DateLike) -> str:
    """该日期若为单位节假日，返回节假日名称；否则返回空字符串。"""
    d = _to_date(dt)
    if d.weekday() >= 5:
        return ""
    return holiday_names_for_year(d.year).get(d, "")


def is_weekend(dt: DateLike) -> bool:
    """是否周末（周六/周日）。"""
    return _to_date(dt).weekday() >= 5


def is_holiday(dt: DateLike) -> bool:
    """是否内置节假日休市日。"""
    d = _to_date(dt)
    return d in holidays_for_year(d.year)


def is_trading_day(dt: DateLike) -> bool:
    """是否交易日：非周末且非节假日。"""
    d = _to_date(dt)
    return not is_weekend(d) and not is_holiday(d)


def market_status(dt: DateLike) -> str:
    """
    市场状态：OPEN / CLOSED / WEEKEND / HOLIDAY。
    - 周六周日 -> WEEKEND
    - 节假日   -> HOLIDAY
    - 交易日且落在 09:30~16:00 -> OPEN
    - 交易日但处于盘前/盘后   -> CLOSED
    传入纯 date（无时分）时视为该交易日盘中，返回 OPEN。
    """
    d = _to_date(dt)
    if is_weekend(d):
        return MARKET_WEEKEND
    if is_holiday(d):
        return MARKET_HOLIDAY

    if isinstance(dt, datetime):
        minutes = dt.hour * 60 + dt.minute
        if minutes < MARKET_OPEN_TIME[0] * 60 + MARKET_OPEN_TIME[1]:
            return MARKET_CLOSED
        if minutes >= MARKET_CLOSE_TIME[0] * 60 + MARKET_CLOSE_TIME[1]:
            return MARKET_CLOSED
    return MARKET_OPEN


def weekday_name(dt: DateLike) -> str:
    """星期几（英文，如 'Monday'）。"""
    return _WEEKDAY_NAMES[_to_date(dt).weekday()]


def next_trading_day(dt: DateLike) -> date:
    """严格晚于给定日期的下一个交易日。"""
    d = _to_date(dt)
    candidate = d + timedelta(days=1)
    # 安全阀：极端情况下（日历被清空）也不会死循环
    for _ in range(365):
        if is_trading_day(candidate):
            return candidate
        candidate += timedelta(days=1)
    return candidate


def previous_trading_day(dt: DateLike) -> date:
    """严格早于给定日期的上一个交易日。"""
    d = _to_date(dt)
    candidate = d - timedelta(days=1)
    for _ in range(365):
        if is_trading_day(candidate):
            return candidate
        candidate -= timedelta(days=1)
    return candidate


# ---------------------------------------------------------------- 资产类别路由
# 不同资产类别遵循不同的交易时段规则：
# - 股票类（EQUITY/ETF/INDEX/BOND）走美式交易日历（周末/节假日休市，盘前盘后收市）；
# - 外汇/商品类（FX/COMMODITY）近似 7×24 交易，仅在周末整体休市。
EQUITY_LIKE_CLASSES = {"EQUITY", "ETF", "INDEX", "BOND"}
FX_LIKE_CLASSES = {"FX", "COMMODITY"}


def market_status_for(asset_class: str, dt: DateLike) -> str:
    """按资产类别返回市场状态（严格停盘的核心判定）。

    - 外汇/商品类：周末 -> WEEKEND，其余一律 OPEN（近似 7×24）。
    - 股票类：完全委托既有 ``market_status(dt)``（含 09:30~16:00 盘中判定、
      周末、节假日）。
    """
    if (asset_class or "").upper() in FX_LIKE_CLASSES:
        return MARKET_WEEKEND if is_weekend(_to_date(dt)) else MARKET_OPEN
    return market_status(dt)


def is_open_for(asset_class: str, dt: DateLike) -> bool:
    """某资产类别在给定时刻是否处于可交易（开市）状态。"""
    return market_status_for(asset_class, dt) == MARKET_OPEN
