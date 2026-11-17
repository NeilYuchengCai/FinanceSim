"""
FinanceSim Trading Calendar
美国市场交易日历：周末休市 + 主要节假日休市。

节假日一律按年份动态计算（不写死固定日期），跨年自动正确。
不引入任何第三方依赖，仅使用标准库 datetime。
"""
import logging
from datetime import date, datetime, timedelta, time
from functools import lru_cache
from typing import Optional, Union

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


def next_trading_open(dt: DateLike) -> datetime:
    """返回不早于 ``dt`` 的下一个股票类可交易开盘时刻（交易日 09:30）。

    - 若 ``dt`` 当前正处于盘中(OPEN)，原样返回，不打断进行中的会话；
    - 若 ``dt`` 是交易日但盘前(<09:30)，返回今日 09:30；
    - 其余（盘后/周末/节假日）返回下一个交易日的 09:30。

    纯函数、确定性，便于模拟世界按种子复现。用于把每个世界的模拟时钟
    起点对齐到交易时段开盘，使"启动即处于可交易状态"，首用体验不再被
    400「市场休市」劝退；仅修正初始状态，不改变"不自动跑时钟"的既有设计。
    """
    if market_status(dt) == MARKET_OPEN:
        return dt
    d = _to_date(dt)
    if (
        is_trading_day(d)
        and isinstance(dt, datetime)
        and (dt.hour * 60 + dt.minute) < (MARKET_OPEN_TIME[0] * 60 + MARKET_OPEN_TIME[1])
    ):
        return datetime.combine(d, time(*MARKET_OPEN_TIME))
    nd = next_trading_day(d)
    return datetime.combine(nd, time(*MARKET_OPEN_TIME))


# ---------------------------------------------------------------- 多交易所日历
# 平台自称"全球资产"，但此前所有标的都套用单一美式日历。真实市场里
# 东京/香港/伦敦/法兰克福各有不同的开收市时段与节假日，且互相错峰——
# 同一模拟时刻，美股休市时港股可能正开盘。本模块为每个交易所定义独立的
# 时段窗口与所属国家的节假日集合，使"全球市场"在模拟时钟下真正错峰运行。
#
# 关键约定：模拟时钟统一视作**美东时间(ET)**。各交易所的时段用"相对美东的
# 小时窗口"表达（例如港股 09:30~16:00 HKT = 美东 21:30~次日04:00），从而与
# 既有的美式 09:30~16:00 判定保持同一时间基准、互不冲突，也无需引入时区库。
# ----------------------------------------------------------------

# 各交易所常规交易时段（美东时间 ET），(open_h, open_m, close_h, close_m)。
# close < open 表示跨午夜（如东京/香港在美东"前一日晚上"开盘、次日凌晨收）。
EXCHANGE_SESSIONS = {
    # 美国：NYSE / NASDAQ / AMEX 统一 09:30~16:00 ET
    "NYSE":   {"open": (9, 30),  "close": (16, 0),  "country": "US"},
    "NASDAQ": {"open": (9, 30),  "close": (16, 0),  "country": "US"},
    "AMEX":   {"open": (9, 30),  "close": (16, 0),  "country": "US"},
    # 欧洲：法兰克福/泛欧 08:00~16:30 CET ≈ 美东 03:00~11:30
    "XETRA":     {"open": (3, 0),  "close": (11, 30), "country": "EU"},
    "EURONEXT":  {"open": (3, 0),  "close": (11, 30), "country": "EU"},
    # 英国：LSE 08:00~16:30 GMT/BST ≈ 美东 03:00~11:30
    "LSE":    {"open": (3, 0),  "close": (11, 30), "country": "UK"},
    # 日本：TSE 09:00~15:00 JST ≈ 美东 20:00~次日02:00（跨午夜）
    "TSE":    {"open": (20, 0), "close": (2, 0),   "country": "JP"},
    "JPX":    {"open": (20, 0), "close": (2, 0),   "country": "JP"},
    # 香港：HKEX 09:30~16:00 HKT ≈ 美东 21:30~次日04:00（跨午夜）
    "HKEX":   {"open": (21, 30), "close": (4, 0),  "country": "HK"},
}

# 别名归一化：资产表 exchange 字段五花八门，统一映射到上表键。
EXCHANGE_ALIASES = {
    "US": "NYSE", "NASDAQ": "NASDAQ", "NYSE": "NYSE", "AMEX": "AMEX",
    "XETRA": "XETRA", "FWB": "XETRA", "FRA": "XETRA", "EURONEXT": "EURONEXT",
    "EPA": "EURONEXT", "LSE": "LSE", "LON": "LSE",
    "TSE": "TSE", "JPX": "TSE", "TKS": "TSE", "OSE": "TSE",
    "HKEX": "HKEX", "HKG": "HKEX", "SEHK": "HKEX",
}


@lru_cache(maxsize=None)
def _eu_holidays(year: int) -> frozenset:
    """欧洲（德/法泛欧）市场节假日近似集合（已含顺延观测日）。"""
    items = [
        date(year, 1, 1),                                   # 元旦
        _easter(year) - timedelta(days=2),                  # 耶稣受难日
        _easter(year) + timedelta(days=1),                  # 复活节周一
        date(year, 5, 1),                                   # 劳动节
        date(year, 12, 25),                                 # 圣诞节
        date(year, 12, 26),                                 # 节礼日（部分市场）
    ]
    return frozenset(items)


@lru_cache(maxsize=None)
def _uk_holidays(year: int) -> frozenset:
    """英国 LSE 节假日集合（含银行假日）。"""
    items = [
        date(year, 1, 1),                                   # 元旦
        _easter(year) - timedelta(days=2),                  # 耶稣受难日
        _easter(year) + timedelta(days=1),                  # 复活节周一
        _nth_weekday(year, 5, 0, 1),                        # 五月初银行假日
        _last_weekday(year, 5, 0),                          # 春季银行假日
        _last_weekday(year, 8, 0),                          # 夏季银行假日
        date(year, 12, 25),                                 # 圣诞节
        date(year, 12, 26),                                 # 节礼日
    ]
    return frozenset(items)


@lru_cache(maxsize=None)
def _jp_holidays(year: int) -> frozenset:
    """日本 TSE 节假日近似集合（固定节假日，忽略"补休"等复杂规则）。"""
    items = [
        date(year, 1, 1),                                   # 元日
        _nth_weekday(year, 1, 0, 2),                        # 成人之日
        date(year, 2, 11),                                  # 建国纪念日
        date(year, 2, 23),                                  # 天皇诞生日
        date(year, 4, 29),                                  # 昭和之日
        date(year, 5, 3),                                   # 宪法纪念日
        date(year, 5, 4),                                   # 绿之日
        date(year, 5, 5),                                   # 儿童之日
        _nth_weekday(year, 7, 0, 3),                        # 海之日
        date(year, 8, 11),                                  # 山之日
        date(year, 11, 3),                                  # 文化之日
        date(year, 11, 23),                                 # 勤劳感谢之日
    ]
    return frozenset(items)


@lru_cache(maxsize=None)
def _hk_holidays(year: int) -> frozenset:
    """香港 HKEX 节假日近似集合（固定节假日，忽略农历新年等浮动假）。"""
    items = [
        date(year, 1, 1),                                   # 元旦
        date(year, 5, 1),                                   # 劳动节
        date(year, 7, 1),                                   # 香港特别行政区成立纪念日
        date(year, 10, 1),                                  # 国庆日
        date(year, 12, 25),                                 # 圣诞节
        date(year, 12, 26),                                 # 圣诞节后第一个工作日
    ]
    return frozenset(items)


_COUNTRY_HOLIDAYS = {
    "US": lambda y: holidays_for_year(y),
    "EU": _eu_holidays,
    "UK": _uk_holidays,
    "JP": _jp_holidays,
    "HK": _hk_holidays,
}


def holidays_for_country(country: str, year: int) -> frozenset:
    """返回指定国家/地区在某年的休市节假日集合（纯函数、可测试）。"""
    fn = _COUNTRY_HOLIDAYS.get((country or "").upper())
    if fn is None:
        return frozenset()
    return fn(year)


def _normalize_exchange(exchange: Optional[str]) -> Optional[str]:
    """把资产表里的 exchange 字段归一化到 EXCHANGE_SESSIONS 的键。"""
    if not exchange:
        return None
    return EXCHANGE_ALIASES.get((exchange or "").upper().strip())


def market_status_for_exchange(exchange: str, dt: DateLike) -> str:
    """按交易所返回市场状态（严格停盘的核心判定）。

    - 未知交易所 -> 退化为经典美式 ``market_status(dt)``，保证向后兼容；
    - 所有交易所周末均休市（WEEKEND）；
    - 所属国家节假日 -> HOLIDAY；
    - 交易日按时段窗口判定 OPEN / CLOSED（支持跨午夜时段）。
    传入纯 date 视为该交易日盘中，返回 OPEN。
    """
    key = _normalize_exchange(exchange)
    sess = EXCHANGE_SESSIONS.get(key) if key else None
    if sess is None:
        return market_status(dt)

    d = _to_date(dt)
    if is_weekend(d):
        return MARKET_WEEKEND

    country = sess["country"]
    if d in holidays_for_country(country, d.year):
        return MARKET_HOLIDAY

    if not isinstance(dt, datetime):
        return MARKET_OPEN

    minutes = dt.hour * 60 + dt.minute
    oh, om = sess["open"]
    ch, cm = sess["close"]
    open_min = oh * 60 + om
    close_min = ch * 60 + cm
    if close_min < open_min:  # 跨午夜：如东京 20:00~02:00
        if minutes >= open_min or minutes < close_min:
            return MARKET_OPEN
    else:
        if open_min <= minutes < close_min:
            return MARKET_OPEN
    return MARKET_CLOSED


# ---------------------------------------------------------------- 资产类别路由
# 不同资产类别遵循不同的交易时段规则：
# - 股票类（EQUITY/ETF/INDEX/BOND）按各自交易所日历（默认美式）；
# - 外汇/商品类（FX/COMMODITY）近似 7×24 交易，仅在周末整体休市。
EQUITY_LIKE_CLASSES = {"EQUITY", "ETF", "INDEX", "BOND"}
FX_LIKE_CLASSES = {"FX", "COMMODITY"}


def market_status_for(asset_class: str, dt: DateLike, exchange: Optional[str] = None) -> str:
    """按资产类别 + 交易所返回市场状态（严格停盘的核心判定）。

    - 若给出可识别的 ``exchange``，按该交易所独立日历判定（错峰、独立节假日）；
    - 外汇/商品类：周末 -> WEEKEND，其余一律 OPEN（近似 7×24）；
    - 其余股票类：未指明交易所时回退到经典美式 ``market_status(dt)``。
    """
    if exchange:
        norm = _normalize_exchange(exchange)
        if norm and norm in EXCHANGE_SESSIONS:
            return market_status_for_exchange(exchange, dt)
    if (asset_class or "").upper() in FX_LIKE_CLASSES:
        return MARKET_WEEKEND if is_weekend(_to_date(dt)) else MARKET_OPEN
    return market_status(dt)


def is_open_for(asset_class: str, dt: DateLike, exchange: Optional[str] = None) -> bool:
    """某资产在给定时刻是否处于可交易（开市）状态。"""
    return market_status_for(asset_class, dt, exchange) == MARKET_OPEN
