"""
FinanceSim News Engine
负责新闻生成、管理和传播
"""
import random
import uuid
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class NewsImportance(Enum):
    BREAKING = "BREAKING"
    MAJOR = "MAJOR"
    MARKET = "MARKET"
    COMPANY = "COMPANY"
    MACRO = "MACRO"
    MINOR = "MINOR"


@dataclass
class NewsItem:
    """新闻项"""
    id: str
    headline: str
    body: str
    importance: NewsImportance
    sentiment: float  # -1.0 to 1.0
    category: str  # MARKET, COMPANY, MACRO, GLOBAL
    affected_assets: List[str] = field(default_factory=list)
    affected_sectors: List[str] = field(default_factory=list)
    source: str = "FINANCESIM"
    created_at: datetime = field(default_factory=datetime.now)
    is_read: bool = False
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "headline": self.headline,
            "body": self.body,
            "importance": self.importance.value,
            "sentiment": self.sentiment,
            "category": self.category,
            "affected_assets": self.affected_assets,
            "affected_sectors": self.affected_sectors,
            "source": self.source,
            "created_at": self.created_at.isoformat(),
            "is_read": self.is_read
        }


class SafeDict(dict):
    """模板格式化用的安全字典。

    新闻模板的占位符远多于调用方显式传入的参数，缺失的 key 会通过
    NewsGenerator._default_for 生成合理随机值，避免 KeyError。
    """
    def __missing__(self, key):
        return NewsGenerator._default_for(key)


def _fmt_price(p: float) -> str:
    """价格格式化：指数/大盘股不带小数，普通标的带两位小数。"""
    try:
        p = float(p)
    except (TypeError, ValueError):
        p = 0.0
    if p >= 1000:
        return f"${p:,.0f}"
    return f"${p:,.2f}"


def _fmt_pct(c: float) -> str:
    """带符号的百分比。"""
    try:
        c = float(c)
    except (TypeError, ValueError):
        c = 0.0
    return f"{c:+.2f}%"


# 板块驱动叙事：把"板块涨跌幅"落地成具体的现实感原因，而非随机填词
SECTOR_DRIVERS = {
    "Technology": ["AI demand optimism", "strong cloud earnings", "upbeat analyst commentary", "data-center capex tailwinds"],
    "Communication Services": ["robust ad revenue", "subscriber gains", "streaming momentum"],
    "Financials": ["a steeper yield curve", "rate-cut expectations", "resilient net interest margins"],
    "Healthcare": ["positive trial readouts", "pipeline progress", "a defensive rotation"],
    "Energy": ["softer crude prices", "OPEC+ supply signals", "weaker demand forecasts"],
    "Consumer Discretionary": ["upbeat same-store sales", "resilient consumer spending", "easy comparisons"],
    "Consumer Staples": ["steady demand", "pricing power", "a defensive bid"],
    "Industrials": ["healthy order books", "reshoring capex", "infrastructure spending"],
    "Materials": ["firm commodity prices", "China demand hopes", "supply constraints"],
    "Utilities": ["rate-sensitive flows", "regulated returns", "renewables investment"],
    "Real Estate": ["lower rate expectations", "lease-rate stabilization"],
    "Other": ["broad market flows", "positioning adjustments"],
}


class NewsGenerator:
    """新闻生成器"""
    
    TEMPLATES = {
        "earnings_beat": [
            "{company} reports Q{quarter} earnings of ${eps} per share, beating estimates by {pct}%",
            "{company} beats expectations with strong {sector} demand driving growth",
            "{company} raises full-year guidance after Q{quarter} profit surge of {pct}%"
        ],
        "earnings_miss": [
            "{company} misses Q{quarter} earnings estimates, posting ${eps} vs ${expected} expected",
            "{company} shares fall after disappointing {sector} results",
            "{company} cuts outlook as Q{quarter} revenue declines {pct}% year over year"
        ],
        "rate_decision": [
            "Federal Reserve {action} interest rates by {bp} basis points to {rate}%",
            "Central bank {action} monetary policy stance, signaling {outlook}",
            "Policymakers hold rates steady at {rate}%, citing {outlook}"
        ],
        "inflation_data": [
            "US inflation {direction} to {pct}% in latest CPI reading, versus {expected}% expected",
            "Consumer prices {direction} {pct}%, marking a {significance} level in recent months",
            "Core inflation {direction} to {pct}% annually, shaping rate expectations"
        ],
        "employment_report": [
            "US adds {n} jobs in {month}, unemployment rate holds at {rate}%",
            "Labor market remains {condition} as {n} new positions created",
            "Unemployment {direction} to {rate}% amid {condition} hiring activity"
        ],
        "gdp_report": [
            "US economy grows at {pct}% annual rate in Q{quarter}, {result} forecasts",
            "GDP growth {direction}s to {pct}%, economy shows {condition}",
            "Quarterly GDP expands {pct}% as consumer spending stays {condition}"
        ],
        "merger_acquisition": [
            "{company1} to acquire {company2} in ${value}B deal, expanding {sector} footprint",
            "Major M&A activity: {company1} announces ${value}B acquisition of {company2}",
            "{company1} and {company2} confirm ${value}B merger talks in {sector}"
        ],
        "product_launch": [
            "{company} unveils {product}, targeting {market} segment",
            "New product launch from {company} could reshape {sector} landscape",
            "{company} enters {market} with {product}, challenging {sector} incumbents"
        ],
        "regulatory_action": [
            "SEC {action} {company} over {issue}, potential {impact} implications",
            "Regulatory scrutiny intensifies for {company} as {issue} comes under review",
            "Antitrust regulators {action} regarding {company}'s {issue}"
        ],
        "management_change": [
            "{company} announces CEO transition with {name} taking over effective {date}",
            "{company} names {name} as new CEO, succeeding leadership after {tenure} years",
            "Leadership change at {company} appoints {name} effective {date}"
        ],
        "geopolitical": [
            "Geopolitical tensions escalate as {issue} raises concerns about {impact}",
            "Global markets react to {issue}, trade uncertainty weighs on sentiment",
            "Diplomatic developments on {issue} drive risk sentiment across {market}"
        ],
        "credit_event": [
            "{company} credit outlook revised to {outlook} by {agency}",
            "Credit rating {action} for {company}, reflecting {concern} risks",
            "{company} maintains {rating} rating from {agency}, outlook {outlook}"
        ]
    }
    
    SECTORS = ["Technology", "Healthcare", "Financials", "Energy", "Consumer Discretionary", "Industrials", "Materials", "Communication Services"]
    COMPANIES = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "JPM", "JNJ", "XOM", "PG", "V", "WMT", "DIS", "NFLX", "META", "BAC", "HD", "CVX", "ABBV", "ORCL"]
    
    MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
    PRODUCTS = ["a next-generation AI platform", "an updated flagship device", "a cloud services suite", "an electric vehicle lineup", "a premium subscription tier"]
    AGENCIES = ["Moody's", "Standard & Poor's", "Fitch Ratings"]
    NAMES = ["a veteran industry executive", "the former chief operating officer", "an external hire from a rival firm", "the company president"]
    ISSUES = ["supply chain disruptions", "a trade policy dispute", "data privacy compliance", "pricing practices", "export controls", "an ongoing antitrust review"]
    
    def __init__(self):
        self.news_items: List[NewsItem] = []
        self._news_id_counter = 0
    
    @staticmethod
    def _default_for(key: str):
        """为模板中缺失的占位符生成合理的随机默认值。
        模板本身远多于调用方显式提供的参数，因此这里做兜底，避免 KeyError。"""
        r = random.random
        mapping = {
            "company": lambda: random.choice(NewsGenerator.COMPANIES),
            "company1": lambda: random.choice(NewsGenerator.COMPANIES),
            "company2": lambda: random.choice(
                [c for c in NewsGenerator.COMPANIES if True]
            ),
            "sector": lambda: random.choice(NewsGenerator.SECTORS),
            "eps": lambda: round(r() * 3.5 + 0.5, 2),
            "expected": lambda: round(r() * 3.5 + 0.5, 2),
            "pct": lambda: round(r() * 12 + 0.5, 1),
            "quarter": lambda: random.randint(1, 4),
            "bp": lambda: random.choice([25, 50, 75]),
            "rate": lambda: round(r() * 4.5 + 0.5, 2),
            "n": lambda: random.randint(50, 350) * 1000,
            "month": lambda: random.choice(NewsGenerator.MONTHS),
            "direction": lambda: random.choice(["rose", "fell", "climbed", "eased"]),
            "action": lambda: random.choice(["raises", "cuts", "reviewed", "holds"]),
            "outlook": lambda: random.choice(["a dovish tone", "a hawkish tone", "policy patience", "caution on growth"]),
            "significance": lambda: random.choice(["notable", "moderate", "elevated"]),
            "condition": lambda: random.choice(["resilient", "tight", "subdued", "robust"]),
            "result": lambda: random.choice(["beating", "matching", "missing"]),
            "value": lambda: round(r() * 45 + 1.5, 1),
            "product": lambda: random.choice(NewsGenerator.PRODUCTS),
            "market": lambda: random.choice(["enterprise", "consumer", "mid-tier", "international"]),
            "issue": lambda: random.choice(NewsGenerator.ISSUES),
            "impact": lambda: random.choice(["valuation", "compliance costs", "near-term margins", "market access"]),
            "name": lambda: random.choice(NewsGenerator.NAMES),
            "date": lambda: "next quarter",
            "tenure": lambda: random.randint(3, 15),
            "concern": lambda: random.choice(["refinancing", "margin compression", "cyclical demand"]),
            "agency": lambda: random.choice(NewsGenerator.AGENCIES),
            "rating": lambda: random.choice(["AAA", "AA", "A", "BBB"]),
        }
        gen = mapping.get(key)
        return gen() if gen else "N/A"
    
    def generate_news(self, assets: List[Dict], macro_state: Optional[Dict] = None, min_count: int = 10) -> List[NewsItem]:
        """生成新闻

        min_count 保证账面新闻的下限：单次 30% 概率的公司新闻在资产较少时
        平均只有一两条，会话启动后新闻页会出现空白，因此这里补到足够数量为度。
        """
        news_list = []
        
        # 根据宏观状态生成新闻
        if macro_state:
            news_list.extend(self._generate_macro_news(macro_state))
        
        # 生成公司级新闻
        news_list.extend(self._generate_company_news(assets))
        
        # 补足到最低数量，避免新闻列表过度稀疏
        fallback = assets or [{"ticker": c, "sector": "Technology"} for c in self.COMPANIES]
        attempts = 0
        while len(news_list) < min_count and attempts < 25:
            attempts += 1
            news_list.extend(self._generate_company_news(fallback))
        
        # 按重要性排序
        news_list.sort(key=lambda x: list(NewsImportance).index(x.importance))
        
        self.news_items.extend(news_list)
        return news_list
    
    # ---------------------------------------------------------------- 市场挂钩新闻
    def generate_market_news(self, snapshot, macro_state: Optional[Dict] = None,
                             target_date=None) -> List[NewsItem]:
        """基于真实行情快照 + 真实宏观状态生成"与市场紧密挂钩"的新闻。

        snapshot: market_stream.snapshot_full() 的结果，每项含
            t ticker / p 现价 / c 累计涨跌幅 / n 名称 / s 板块 / y 类型 / d 当日涨跌幅
        不再使用固定模版随机填值，而是根据真实波动幅度、板块轮动、宏观读数来组织叙事。
        """
        if target_date is None:
            target_date = datetime.now()
        # 用模拟日的序数做随机种子：同一天新闻可复现，不同天天然不同（避免随机模版 spam）
        rng = random.Random(target_date.toordinal())

        news: List[NewsItem] = []
        equities = [s for s in (snapshot or []) if s.get("y") in ("EQUITY", "ETF")]
        indices = [s for s in (snapshot or []) if s.get("y") == "INDEX"]

        # 1) 市场整体定调
        if equities:
            avg = sum(s.get("d", s.get("c", 0.0)) for s in equities) / max(len(equities), 1)
            idx_info = indices[0] if indices else None
            news.append(self._market_headline(avg, idx_info))

        # 2) 板块轮动：领涨 / 领跌板块
        sector_chg: Dict[str, List[float]] = {}
        for s in equities:
            sector_chg.setdefault(s.get("s") or "Other", []).append(s.get("d", s.get("c", 0.0)))
        sector_avg = {sec: sum(v) / len(v) for sec, v in sector_chg.items()}
        ranked = sorted(sector_avg.items(), key=lambda kv: kv[1])
        if ranked:
            loser = ranked[0]
            gainer = ranked[-1]
            if abs(gainer[1]) >= 0.4:
                news.append(self._sector_headline(gainer[0], gainer[1], up=True, rng=rng))
            if loser[0] != gainer[0] and abs(loser[1]) >= 0.4:
                news.append(self._sector_headline(loser[0], loser[1], up=False, rng=rng))

        # 3) 个股异动（按当日涨跌幅取前 N，仅纳入够"新闻级"的波动，避免出现 +0.00% 的尴尬标题）
        movers = sorted(equities, key=lambda s: abs(s.get("d", s.get("c", 0.0))), reverse=True)
        added = 0
        for s in movers:
            ch = s.get("d", s.get("c", 0.0))
            if abs(ch) < 0.8:
                continue
            if added >= 5:
                break
            news.append(self._mover_headline(s, ch, rng))
            added += 1
        # 波动不够时不再强行塞一条 +0.00% 的个股标题，由市场定调/板块/事件新闻补足

        # 4) 宏观新闻（真实宏观状态驱动）
        if macro_state:
            news.extend(self._macro_news(macro_state))

        # 5) 锚定真实个股的事件新闻（管理层 / 监管 / 并购），只引用真实 ticker
        news.extend(self._event_news(movers, macro_state, rng))

        # 按重要性排序
        news.sort(key=lambda x: list(NewsImportance).index(x.importance))
        for item in news:
            item.created_at = target_date.replace(hour=9, minute=30, second=0, microsecond=0)
        self.news_items.extend(news)
        return news

    def _make(self, headline, body, importance, sentiment, category,
              affected_assets=None, affected_sectors=None) -> NewsItem:
        self._news_id_counter += 1
        return NewsItem(
            id=str(uuid.uuid4()),
            headline=headline,
            body=body,
            importance=importance,
            sentiment=sentiment,
            category=category,
            affected_assets=affected_assets or [],
            affected_sectors=affected_sectors or [],
        )

    def _market_headline(self, avg: float, idx_info) -> NewsItem:
        a = avg
        if a > 1.5:
            mag, imp, sent = "rally as risk appetite returns", NewsImportance.MAJOR, min(a / 3.0, 1.0)
            if a > 3:
                imp = NewsImportance.BREAKING
        elif a > 0.3:
            mag, imp, sent = "edge higher, led by cyclicals", NewsImportance.MARKET, min(a / 3.0, 0.6)
        elif a > -0.3:
            mag, imp, sent = "drift in narrow ranges as investors await catalysts", NewsImportance.MINOR, 0.0
        elif a > -1.5:
            mag, imp, sent = "slip as profit-taking sets in", NewsImportance.MARKET, max(a / 3.0, -0.6)
        else:
            mag, imp, sent = "sell off on renewed risk aversion", NewsImportance.MAJOR, max(a / 3.0, -1.0)
            if a < -3:
                imp = NewsImportance.BREAKING
        idx_txt = ""
        if idx_info:
            idx_pct = idx_info.get("d", idx_info.get("c", 0.0))
            if abs(idx_pct) < 0.05:
                idx_txt = f" with the {idx_info.get('n')} little changed"
            else:
                idx_txt = f" with the {idx_info.get('n')} {_fmt_pct(idx_pct)}"
        headline = f"US equities {mag}{idx_txt}"
        body = (f"Broad benchmarks {mag}{idx_txt}. The session's move leaves the average constituent "
                f"around {_fmt_pct(a)} on the day, with internals broadly consistent across large caps.")
        return self._make(headline, body, imp, round(sent, 3), "MARKET")

    def _sector_headline(self, sector: str, chg: float, up: bool, rng: random.Random) -> NewsItem:
        drivers = SECTOR_DRIVERS.get(sector, SECTOR_DRIVERS["Other"])
        driver = rng.choice(drivers)
        pct = _fmt_pct(chg)
        if up:
            headline = f"{sector} shares lead the advance, buoyed by {driver} as the group adds {pct}"
            body = (f"The {sector} complex outperformed, with the group averaging {pct} on the session. "
                    f"Desks cited {driver} as the principal tailwind behind the move.")
            sent = min(chg / 3.0, 0.8)
        else:
            headline = f"{sector} lags, weighed by {driver} as the group sheds {pct}"
            body = (f"{sector} names underperformed, the group averaging {pct}. "
                    f"Strategists pointed to {driver} as the main headwind.")
            sent = max(chg / 3.0, -0.8)
        return self._make(headline, body, NewsImportance.MARKET, round(sent, 3), "MARKET",
                         affected_sectors=[sector])

    def _mover_headline(self, s: dict, chg: float, rng: random.Random) -> NewsItem:
        name = s.get("n") or s.get("t")
        ticker = s.get("t")
        price = _fmt_price(s.get("p"))
        pct = _fmt_pct(chg)
        sector = s.get("s") or "Other"
        drivers = SECTOR_DRIVERS.get(sector, SECTOR_DRIVERS["Other"])
        driver = rng.choice(drivers)
        big = abs(chg) >= 3.0
        if chg >= 0:
            if big:
                headline = f"{name} ({ticker}) jumps {pct} to {price} as {driver} fuels an earnings-beat narrative"
            else:
                headline = f"{name} ({ticker}) climbs {pct} to {price} on {driver}"
            body = (f"{name} ({ticker}) advanced {pct} to {price}. "
                    f"Flows were driven by {driver}; the move extends recent relative strength in the name.")
            sent = min(chg / 3.0, 1.0)
            imp = NewsImportance.MAJOR if big else NewsImportance.COMPANY
        else:
            if big:
                headline = f"{name} ({ticker}) tumbles {pct} to {price} as {driver} sparks a guidance-miss rethink"
            else:
                headline = f"{name} ({ticker}) slides {pct} to {price} as {driver} pressures the shares"
            body = (f"{name} ({ticker}) fell {pct} to {price}. "
                    f"Traders flagged {driver} as the catalyst behind the weakness.")
            sent = max(chg / 3.0, -1.0)
            imp = NewsImportance.MAJOR if big else NewsImportance.COMPANY
        return self._make(headline, body, imp, round(sent, 3), "COMPANY",
                         affected_assets=[ticker], affected_sectors=[sector])

    def _macro_news(self, macro: Dict) -> List[NewsItem]:
        out: List[NewsItem] = []
        inflation = float(macro.get("inflation", 0.02))
        interest = float(macro.get("interest_rate", 0.05))
        unemployment = float(macro.get("unemployment", 0.05))
        gdp = float(macro.get("gdp_growth", 0.025))
        conf = float(macro.get("consumer_confidence", 1.0))
        phase = str(macro.get("cycle_phase", "EXPANSION"))

        infl_pct = inflation * 100
        if infl_pct > 3:
            out.append(self._make(
                f"Inflation runs hot at {infl_pct:.1f}%, keeping the Fed on a hawkish path",
                f"Consumer prices rose {infl_pct:.1f}% year over year, above the central bank's target and "
                f"reinforcing expectations that policy will stay restrictive for longer.",
                NewsImportance.MACRO, -0.4, "MACRO"))
        elif infl_pct > 1.5:
            out.append(self._make(
                f"CPI prints at {infl_pct:.1f}%, close to the Fed's target",
                f"Headline inflation came in at {infl_pct:.1f}%, a reading markets interpreted as consistent "
                f"with a gradual normalization in price pressures.",
                NewsImportance.MACRO, 0.1, "MACRO"))
        elif infl_pct > 0:
            out.append(self._make(
                f"Inflation cools to {infl_pct:.1f}%, easing policy pressure",
                f"Price growth slowed to {infl_pct:.1f}%, giving policymakers more room to support activity.",
                NewsImportance.MACRO, 0.25, "MACRO"))
        else:
            out.append(self._make(
                f"Deflationary signal as prices fall {abs(infl_pct):.1f}%",
                f"Consumer prices declined {abs(infl_pct):.1f}% year over year, raising concerns about demand.",
                NewsImportance.BREAKING, -0.5, "MACRO"))

        rate_pct = interest * 100
        if phase in ("OVERHEAT", "PEAK"):
            out.append(self._make(
                f"Federal Reserve holds the policy rate at {rate_pct:.2f}% amid late-cycle risks",
                f"The central bank left its benchmark at {rate_pct:.2f}%, signaling caution as the expansion "
                f"shows signs of maturity.",
                NewsImportance.MACRO, -0.1, "MACRO"))
        elif phase in ("CONTRACTION", "STAGNATION"):
            out.append(self._make(
                f"Federal Reserve holds the policy rate at {rate_pct:.2f}% as growth softens",
                f"Policymakers kept rates at {rate_pct:.2f}% while acknowledging a loss of momentum in activity.",
                NewsImportance.MACRO, 0.0, "MACRO"))
        else:
            out.append(self._make(
                f"Federal Reserve holds the policy rate at {rate_pct:.2f}%",
                f"The benchmark rate was maintained at {rate_pct:.2f}%, with the committee striking a balanced tone.",
                NewsImportance.MACRO, 0.05, "MACRO"))

        unemp_pct = unemployment * 100
        if unemp_pct < 4:
            out.append(self._make(
                f"Labor market stays tight with unemployment at {unemp_pct:.1f}%",
                f"The jobless rate held at {unemp_pct:.1f}%, a level consistent with full employment.",
                NewsImportance.MACRO, 0.1, "MACRO"))
        elif unemp_pct > 6:
            out.append(self._make(
                f"Labor market softens as unemployment climbs to {unemp_pct:.1f}%",
                f"The unemployment rate rose to {unemp_pct:.1f}%, the highest in some time and a worry for demand.",
                NewsImportance.MACRO, -0.3, "MACRO"))
        else:
            out.append(self._make(
                f"Unemployment steady at {unemp_pct:.1f}%",
                f"The jobless rate was little changed at {unemp_pct:.1f}%, indicating a stable labor backdrop.",
                NewsImportance.MACRO, 0.0, "MACRO"))

        gdp_pct = gdp * 100
        phase_word = {
            "EXPANSION": "broad-based growth",
            "RECOVERY": "early-cycle rebound",
            "PEAK": "late-cycle momentum",
            "CONTRACTION": "slowing activity",
            "STAGNATION": "stagflation concerns",
        }.get(phase, "moderate expansion")
        out.append(self._make(
            f"Economy expands at {gdp_pct:.1f}% annualized in a {phase_word} environment",
            f"Output grew {gdp_pct:.1f}% annualized, painting a picture of {phase_word}.",
            NewsImportance.MARKET, (0.2 if gdp_pct > 0 else -0.4), "MACRO"))

        if conf < 0.85:
            out.append(self._make(
                f"Consumer sentiment sours to {conf:.2f}, a warning for spending",
                f"The confidence index fell to {conf:.2f}, suggesting households are turning more cautious.",
                NewsImportance.MACRO, -0.2, "MACRO"))
        elif conf > 1.15:
            out.append(self._make(
                f"Consumer confidence strengthens to {conf:.2f}",
                f"The confidence index rose to {conf:.2f}, underpinning the outlook for consumption.",
                NewsImportance.MACRO, 0.2, "MACRO"))

        return out[:5]

    def _event_news(self, movers, macro_state=None, rng: random.Random = None) -> List[NewsItem]:
        out: List[NewsItem] = []
        if not movers:
            return out
        if rng is None:
            rng = random
        # 按模拟日种子挑选"主角"，使快进的每一天聚焦不同真实个股，而非千篇一律
        top = rng.choice(movers)
        name = top.get("n") or top.get("t")
        ticker = top.get("t")
        sector = top.get("s") or "Other"
        ch = top.get("d", top.get("c", 0.0))
        direction = "higher" if ch >= 0 else "lower"

        # 管理层变动（锚定真实个股）
        out.append(self._make(
            f"{name} names a new CEO as shares trade {direction}",
            f"{name} ({ticker}) announced a leadership transition. The stock has been trading {direction} "
            f"ahead of the change, and investors will watch whether capital allocation plans shift.",
            NewsImportance.COMPANY, (0.1 if ch >= 0 else -0.1), "COMPANY",
            affected_assets=[ticker], affected_sectors=[sector]))

        # 监管 / 并购（引用同板块另一只真实个股）
        same_sector = [m for m in movers if (m.get("s") or "Other") == sector and m.get("t") != ticker]
        if same_sector:
            other = rng.choice(same_sector)
            out.append(self._make(
                f"{name} said to be exploring a combination with {other.get('t')} in the {sector} space",
                f"People familiar with the matter said {name} ({ticker}) has held preliminary talks with "
                f"{other.get('t')} ({other.get('n') or other.get('t')}) about a tie-up spanning {sector}.",
                NewsImportance.MAJOR, 0.2, "COMPANY",
                affected_assets=[ticker, other.get("t")], affected_sectors=[sector]))
        else:
            out.append(self._make(
                f"Regulators open a review of {name} over competitive practices",
                f"Authorities confirmed a review of {name} ({ticker}), focusing on competitive conduct. "
                f"The inquiry adds an overhang for the shares.",
                NewsImportance.COMPANY, -0.15, "COMPANY",
                affected_assets=[ticker], affected_sectors=[sector]))
        return out

    def _generate_macro_news(self, state: Dict) -> List[NewsItem]:
        """生成宏观新闻

        除了阈值触发的异常态新闻外，常态下也要产出一到两条描述当前宏观环境的
        新闻，否则默认参数下宏观新闻永远是空的。
        """
        news = []
        
        inflation = state.get("inflation", 0.02)
        unemployment = state.get("unemployment", 0.05)
        gdp = state.get("gdp_growth", 0.025)
        interest_rate = state.get("interest_rate", 0.05)

        # 央行政策 - 常态描述
        news.append(self._create_news(
            "rate_decision",
            importance=NewsImportance.MACRO,
            sentiment=0.0,
            category="MACRO",
            rate=round(interest_rate * 100, 2)
        ))
        
        # 通胀新闻
        if inflation > 0.03:
            news.append(self._create_news(
                "inflation_data",
                importance=NewsImportance.MACRO if inflation < 0.05 else NewsImportance.BREAKING,
                sentiment=-0.3 * (inflation - 0.02) * 10,
                category="MACRO",
                pct=round(inflation * 100, 2),
                direction="rose",
                expected=round(state.get("expected_inflation", max(inflation - 0.004, 0)) * 100, 2)
            ))
        else:
            news.append(self._create_news(
                "inflation_data",
                importance=NewsImportance.MACRO,
                sentiment=0.05,
                category="MACRO",
                pct=round(inflation * 100, 2),
                direction="eased",
                expected=round(max(inflation - 0.003, 0) * 100, 2)
            ))
        
        # 就业新闻
        if unemployment > 0.06:
            news.append(self._create_news(
                "employment_report",
                importance=NewsImportance.MACRO,
                sentiment=-0.2,
                category="MACRO",
                rate=round(unemployment * 100, 2),
                condition="subdued"
            ))
        else:
            news.append(self._create_news(
                "employment_report",
                importance=NewsImportance.MARKET,
                sentiment=0.05,
                category="MACRO",
                rate=round(unemployment * 100, 2),
                condition="resilient"
            ))
        
        # GDP新闻
        if gdp < 0:
            news.append(self._create_news(
                "gdp_report",
                importance=NewsImportance.BREAKING,
                sentiment=-0.5,
                category="MACRO",
                pct=round(gdp * 100, 2),
                result="missing",
                condition="contraction"
            ))
        else:
            news.append(self._create_news(
                "gdp_report",
                importance=NewsImportance.MARKET,
                sentiment=0.1 if gdp > 0.02 else -0.05,
                category="MACRO",
                pct=round(gdp * 100, 2),
                result="beating" if gdp > 0.02 else "matching",
                condition="moderate expansion"
            ))
        
        return news
    
    def _generate_company_news(self, assets: List[Dict]) -> List[NewsItem]:
        """生成公司新闻"""
        news = []
        
        for asset in assets:
            # 随机生成事件
            if random.random() < 0.3:  # 30%概率生成新闻
                event_type = random.choice([
                    "earnings_beat", "earnings_miss", "product_launch",
                    "merger_acquisition", "regulatory_action", "management_change",
                    "geopolitical", "credit_event"
                ])
                
                sentiment = random.uniform(-0.5, 0.5)
                importance = NewsImportance.MAJOR if abs(sentiment) > 0.3 else NewsImportance.COMPANY
                ticker = asset.get("ticker", "Company")
                sector = asset.get("sector", "Technology")
                
                kwargs = {
                    "sector": sector,
                    "affected_assets": [ticker],
                    "affected_sectors": [sector],
                }
                
                if event_type == "merger_acquisition":
                    # 并购需要两家不同的公司，否则 headline 会变成自己收购自己
                    others = [a.get("ticker") for a in assets if a.get("ticker") and a.get("ticker") != ticker]
                    pool = others or [c for c in self.COMPANIES if c != ticker]
                    kwargs["company1"] = ticker
                    kwargs["company2"] = random.choice(pool) if pool else random.choice(self.COMPANIES)
                else:
                    kwargs["company"] = ticker
                
                news.append(self._create_news(
                    event_type,
                    sentiment=sentiment,
                    importance=importance,
                    category="COMPANY",
                    **kwargs
                ))
        
        return news
    
    def _create_news(
        self,
        template_type: str,
        importance: NewsImportance = NewsImportance.MARKET,
        sentiment: float = 0.0,
        category: str = "MARKET",
        **kwargs
    ) -> NewsItem:
        """创建新闻项

        模板含有大量占位符，调用方通常只提供 company。这里用 SafeDict 兜底，
        任何缺失的占位符都会得到合理的随机值，避免 KeyError 导致的 500。
        """
        templates = self.TEMPLATES.get(template_type, ["Unknown event occurred"])
        try:
            # 必须用 format_map：str.format(d) 会把 dict 当成位置参数传给 {0}，
            # 占位符 {company} 等反而找不到值，__missing__ 也不会被触发。
            headline = random.choice(templates).format_map(SafeDict(kwargs))
        except Exception as e:  # 兜底：任何格式化异常都不应让请求失败
            logger.warning(f"News template '{template_type}' render failed: {e}")
            company = kwargs.get("company", "the company")
            headline = f"{company} reports developments affecting its {kwargs.get('sector', 'sector')} operations"
        
        # 生成ID（uuid4：进程重启后不与历史新闻重号，落库后仍全局唯一）
        self._news_id_counter += 1
        news_id = str(uuid.uuid4())
        
        body = self._build_body(template_type, kwargs)
        
        return NewsItem(
            id=news_id,
            headline=headline,
            body=body,
            importance=importance,
            sentiment=sentiment,
            category=category,
            affected_assets=kwargs.get("affected_assets", []),
            affected_sectors=kwargs.get("affected_sectors", [])
        )
    
    def _build_body(self, template_type: str, kwargs: Dict) -> str:
        """生成新闻正文"""
        company = kwargs.get("company", kwargs.get("company1", "The company"))
        sector = kwargs.get("sector", "the market")
        templates = {
            "earnings_beat": f"{company} delivered stronger-than-expected results, with management highlighting resilient demand across its core {sector} operations. Analysts had positioned for a more modest outcome, and several noted that margin execution was the primary positive surprise. The company reaffirmed its capital return program.",
            "earnings_miss": f"{company} fell short of consensus expectations, with weaker-than-forecast volumes in {sector} weighing on both revenue and profitability. Management pointed to near-term transitory factors and outlined cost discipline measures to protect full-year targets.",
            "rate_decision": f"Monetary policymakers delivered their latest decision, balancing persistent inflation pressures against signs of moderating growth. Markets repositioned rate expectations immediately following the announcement, with {sector} showing the strongest sensitivity to the move.",
            "inflation_data": f"The latest consumer price readings inform expectations for the policy path ahead. Core measures remain the focus for policymakers assessing whether disinflation is durable. Currency and {sector} markets repriced modestly on the release.",
            "employment_report": f"Payroll data offers a fresh read on labor market tightness and its implications for wage growth. The unemployment rate and participation dynamics were both scrutinized for signs of cooling. Households continue to draw support from a still-solid jobs backdrop.",
            "gdp_report": f"The latest output data frames the growth trajectory entering the period ahead. Contributions from consumption, investment, and net exports were examined for evidence of broadening momentum. {sector} remains a key swing factor for the aggregate picture.",
            "merger_acquisition": f"The proposed combination is positioned to deliver scale benefits and cross-sell opportunities within {sector}. Integration execution and regulatory clearance timelines are the central risks flagged by observers. Financing terms imply disciplined leverage through closing.",
            "product_launch": f"The introduction broadens {company}'s addressable market and deepens its competitive moat. Early channel checks will inform expectations for the adoption curve. Competitors across {sector} face incremental pressure on pricing and feature parity.",
            "regulatory_action": f"Regulators escalated their review, introducing an overhang for near-term operations and disclosure obligations. Potential remedies range from conduct restrictions to monetary penalties. Legal exposure is difficult to size at this stage.",
            "management_change": f"Leadership succession introduces both continuity and change into {company}'s strategic agenda. Investors will focus on whether capital allocation priorities remain intact. Execution over coming quarters will determine whether the transition is accretive.",
            "geopolitical": f"Heightened uncertainty is feeding through to risk premia across asset classes. Energy, logistics, and {sector} supply chains are most directly exposed to escalation. Portfolio managers report reduced conviction and wider bid-ask spreads.",
            "credit_event": f"The ratings action alters borrowing costs and index eligibility considerations for the issuer. Spreads across the {sector} complex adjusted in sympathy. Refinancing requirements over the next two years are now under closer scrutiny.",
        }
        return templates.get(template_type, f"Market update affecting {company} and the {sector} sector.")
    
    def get_news(self, limit: int = 50, category: Optional[str] = None, importance: Optional[str] = None) -> List[Dict]:
        """获取新闻列表"""
        news = self.news_items.copy()
        
        if category:
            news = [n for n in news if n.category == category]
        if importance:
            news = [n for n in news if n.importance.value == importance]
        
        # 按时间倒序
        news.sort(key=lambda x: x.created_at, reverse=True)
        
        return [n.to_dict() for n in news[:limit]]
    
    def get_briefing(self, hours: int = 24) -> Dict:
        """生成每日简报"""
        cutoff = datetime.now() - timedelta(hours=hours)
        recent_news = [n for n in self.news_items if n.created_at >= cutoff]
        
        if not recent_news:
            return {"summary": "No significant news in the past {} hours".format(hours)}
        
        breaking = [n for n in recent_news if n.importance == NewsImportance.BREAKING]
        major = [n for n in recent_news if n.importance == NewsImportance.MAJOR]
        
        # 计算综合情绪指数
        sentiment_scores = [n.sentiment for n in recent_news]
        avg_sentiment = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0
        
        # 按类别分组
        by_category = {}
        for n in recent_news:
            cat = n.category
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(n)
        
        return {
            "period": f"Last {hours} hours",
            "total_items": len(recent_news),
            "breaking_count": len(breaking),
            "major_count": len(major),
            "sentiment_index": round(avg_sentiment, 3),
            "sentiment_label": "Bullish" if avg_sentiment > 0.2 else ("Bearish" if avg_sentiment < -0.2 else "Neutral"),
            "by_category": {
                cat: {
                    "count": len(items),
                    "avg_sentiment": round(sum(n.sentiment for n in items) / len(items), 3),
                    "top_story": items[0].to_dict() if items else None
                }
                for cat, items in by_category.items()
            },
            "top_stories": [n.to_dict() for n in sorted(recent_news, key=lambda x: x.importance.value)[:5]],
            "market_impact_summary": self._generate_impact_summary(recent_news)
        }
    
    def _generate_impact_summary(self, news: List[NewsItem]) -> str:
        """生成市场影响摘要"""
        if not news:
            return "No recent news affecting markets."
        
        breaking = [n for n in news if n.importance == NewsImportance.BREAKING]
        if breaking:
            return f"⚠️ BREAKING: {breaking[0].headline}"
        
        major = [n for n in news if n.importance == NewsImportance.MAJOR]
        if major:
            return f"📰 Major developments: {major[0].headline}"
        
        avg_sentiment = sum(n.sentiment for n in news) / len(news)
        if avg_sentiment > 0.3:
            return "📈 Positive sentiment driving market optimism"
        elif avg_sentiment < -0.3:
            return "📉 Negative sentiment weighing on markets"
        return "⚖️ Mixed signals across market news"
    
    def get_daily_summary(self, day_offset: int = 0) -> Dict:
        """获取指定日期的新闻摘要"""
        from datetime import date
        target_date = date.today() - timedelta(days=day_offset)
        next_date = target_date + timedelta(days=1)
        
        day_news = [
            n for n in self.news_items
            if n.created_at.date() == target_date
        ]
        
        if not day_news:
            return {
                "date": target_date.isoformat(),
                "total_news": 0,
                "summary": "No news recorded for this day",
                "highlight": None,
                "market_sentiment": "Neutral"
            }
        
        breaking = [n for n in day_news if n.importance == NewsImportance.BREAKING]
        major = [n for n in day_news if n.importance == NewsImportance.MAJOR]
        
        # 计算当日情绪
        sentiments = [n.sentiment for n in day_news]
        avg_sentiment = sum(sentiments) / len(sentiments) if sentiments else 0
        
        # 找出影响最大的新闻
        most_impactful = max(day_news, key=lambda x: abs(x.sentiment))
        
        return {
            "date": target_date.isoformat(),
            "total_news": len(day_news),
            "breaking_count": len(breaking),
            "major_count": len(major),
            "summary": self._generate_daily_summary_text(day_news, avg_sentiment),
            "highlight": most_impactful.to_dict(),
            "market_sentiment": "Bullish" if avg_sentiment > 0.2 else ("Bearish" if avg_sentiment < -0.2 else "Neutral"),
            "sentiment_score": round(avg_sentiment, 3),
            "news_items": [n.to_dict() for n in sorted(day_news, key=lambda x: x.importance.value)[:10]]
        }
    
    def _generate_daily_summary_text(self, news: List[NewsItem], avg_sentiment: float) -> str:
        """生成每日摘要文本"""
        parts = []
        
        # 情绪判断
        if avg_sentiment > 0.3:
            parts.append("Markets closed on a strongly positive note.")
        elif avg_sentiment > 0.1:
            parts.append("Markets showed moderate optimism.")
        elif avg_sentiment < -0.3:
            parts.append("Markets faced significant headwinds.")
        elif avg_sentiment < -0.1:
            parts.append("Markets experienced some weakness.")
        else:
            parts.append("Markets traded in a mixed fashion.")
        
        # 重大事件
        breaking = [n for n in news if n.importance == NewsImportance.BREAKING]
        if breaking:
            parts.append(f"Breaking: {breaking[0].headline}")
        
        major = [n for n in news if n.importance == NewsImportance.MAJOR]
        if major:
            top_major = major[0]
            parts.append(f"Key development: {top_major.headline}")
        
        return " ".join(parts)


class NewsEngine:
    """新闻引擎 - 主入口"""
    
    def __init__(self):
        self.generator = NewsGenerator()
        self.archived_news: List[NewsItem] = []
    
    def ensure_populated(self, assets: Optional[List[Dict]] = None, macro_state: Optional[Dict] = None) -> None:
        """确保新闻引擎内已有新闻，避免各端点返回空列表。

        优先用真实行情快照 + 真实宏观状态生成，彻底避免"固定模版随机"的新闻。
        仅在拿不到行情数据时退回模版生成。
        """
        if self.generator.news_items:
            return

        try:
            from app.services.market_stream import get_market_stream
            from app.routers.economy import _economic_engine
            stream = get_market_stream()
            snapshot = stream.snapshot_full() if stream else []
            macro = _economic_engine.get_macro_data() if _economic_engine is not None else None
            if snapshot:
                self.generator.generate_market_news(snapshot, macro)
                return
        except Exception as e:
            logger.warning(f"Market-linked ensure_populated failed, falling back to template: {e}")

        # 兜底：无行情数据时退回模版生成
        if assets is None:
            assets = [
                {"ticker": t, "name": t, "sector": s}
                for t, s in [
                    ("AAPL", "Technology"), ("MSFT", "Technology"), ("NVDA", "Technology"),
                    ("JPM", "Financials"), ("JNJ", "Healthcare"), ("XOM", "Energy"),
                    ("AMZN", "Consumer Discretionary"), ("TSLA", "Consumer Discretionary"),
                    ("CAT", "Industrials"), ("PG", "Consumer Staples"),
                ]
            ]
        if macro_state is None:
            macro_state = {
                "gdp_growth": 0.025,
                "inflation": 0.024,
                "unemployment": 0.048,
                "interest_rate": 0.05,
            }
        self.generate_daily_news(assets, macro_state)

    def generate_daily_news(self, assets: List[Dict], macro_state: Optional[Dict] = None) -> List[Dict]:
        """生成每日新闻（模版版，供测试端点 /generate 使用）"""
        news_list = self.generator.generate_news(assets, macro_state)
        logger.info(f"Generated {len(news_list)} news items")
        return [n.to_dict() for n in news_list]

    def generate_for_date(self, target_date: datetime, snapshot: List[Dict],
                          macro_state: Optional[Dict] = None) -> List[Dict]:
        """为指定模拟日期生成与市场挂钩的新闻。

        snapshot 来自 market_stream.snapshot_full()（真实行情），macro_state 来自经济引擎。
        新闻时间戳固定为该模拟日 09:30，使其按模拟时间排序而非真实时间。
        """
        news_list = self.generator.generate_market_news(snapshot, macro_state, target_date)
        logger.info(f"Generated {len(news_list)} market-linked news items for {target_date.date()}")
        return [n.to_dict() for n in news_list]
    
    def get_headlines(self, limit: int = 20) -> List[Dict]:
        """获取头条新闻 - 返回最新/最重要的若干条。

        这里不再只筛 BREAKING：突發新闻在常态下几乎不产生，会导致头条长期为空。
        """
        self.ensure_populated()
        return self.generator.get_news(limit=limit)

    async def refresh_external_news(self, limit: int = 20) -> bool:
        """可选：用外部新闻 provider 的真实头条覆盖合成新闻（只覆盖，不合并）。

        仅在 ``USE_EXTERNAL_DATA`` 且新闻 provider 启用时尝试；任何失败（无 key /
        网络 / 解析 / 限流）都被 ``maybe_fetch`` 吞掉并返回 ``None``，这里安全返回
        ``False`` 并保留原有（合成）新闻。成功返回 ``True``。
        """
        from app.data.providers import get_provider, maybe_fetch

        provider = get_provider("news_api")
        if provider is None or not provider.enabled:
            return False

        try:
            items = await maybe_fetch(provider, query="finance OR markets OR economy",
                                     limit=limit)
        except Exception as exc:  # 双保险
            logger.warning("External news fetch unexpected error: %s", exc)
            return False
        if not items:
            return False

        news_items = []
        for it in items:
            headline = (it.get("headline") or "").strip()
            if not headline:
                continue
            news_items.append(NewsItem(
                id=str(uuid.uuid4()),
                headline=headline,
                body=it.get("body") or "",
                importance=NewsImportance.MARKET,
                sentiment=0.0,
                category="GLOBAL",
                affected_assets=[],
                affected_sectors=[],
                source=it.get("source") or provider.name,
                created_at=datetime.now(),
                is_read=False,
            ))
        if not news_items:
            return False

        # 用真实头条替换合成新闻（保留 archived_news 归档不变）
        self.generator.news_items = news_items
        logger.info("Headlines refreshed from external provider %s (%d items)",
                    provider.name, len(news_items))
        return True
    
    def get_briefing(self, hours: int = 24) -> Dict:
        """获取简报"""
        return self.generator.get_briefing(hours)
