"""
FinanceSim News Engine
负责新闻生成、管理和传播
"""
import random
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
            "importance": self.importance.value,
            "sentiment": self.sentiment,
            "category": self.category,
            "affected_assets": self.affected_assets,
            "affected_sectors": self.affected_sectors,
            "source": self.source,
            "created_at": self.created_at.isoformat(),
            "is_read": self.is_read
        }


class NewsGenerator:
    """新闻生成器"""
    
    TEMPLATES = {
        "earnings_beat": [
            "{company} reports Q{quarter} earnings of ${eps} per share, beating estimates by {pct}%",
            "{company} beats expectations with strong {sector} demand driving growth"
        ],
        "earnings_miss": [
            "{company} misses Q{quarter} earnings estimates, posting ${eps} vs ${expected} expected",
            "{company} shares fall after disappointing {sector} results"
        ],
        "rate_decision": [
            "Federal Reserve {action} interest rates by {bp} basis points to {rate}%",
            "Central bank {action} monetary policy stance, signaling { Outlook}"
        ],
        "inflation_data": [
            "US inflation {direction} to {pct}% in latest CPI reading, above/below expectations",
            "Consumer prices {direction} {pct}%, marking {highest/lowest} level in months"
        ],
        "employment_report": [
            "US adds {n} jobs in {month}, unemployment rate holds at {rate}%",
            "Labor market remains {tight/loose} as {n} new positions created"
        ],
        "gdp_report": [
            "US economy grows at {pct}% annual rate in Q{quarter}, {beating/missing} forecasts",
            "GDP growth {direction}s to {pct}%, economy shows {strength/resilience}"
        ],
        "merger_acquisition": [
            "{company1} to acquire {company2} in ${value}B deal, expanding {sector} footprint",
            "Major M&A activity: {company1} announces ${value}B acquisition of {company2}"
        ],
        "product_launch": [
            "{company} unveils {product}, targeting {market} segment",
            "New product launch from {company} could reshape {sector} landscape"
        ],
        "regulatory_action": [
            "SEC {action} {company} over {issue}, potential {penalty} implications",
            "Regulatory scrutiny intensifies for {company} as {issue} comes under review"
        ],
        "management_change": [
            "{company} announces CEO {change}, {new_outgoing} stepping down after {tenure} years",
            "{company} appoints {name} as new CEO, effective {date}"
        ],
        "geopolitical": [
            "Geopolitical tensions escalate as {event} raises concerns about {impact}",
            "Global markets react to {event}, trade uncertainty weighs on sentiment"
        ],
        "credit_event": [
            "{company} downgraded to {rating} by {agency}, outlook {outlook}",
            "Credit rating {action} for {company}, reflecting {concern} risks"
        ]
    }
    
    SECTORS = ["Technology", "Healthcare", "Finance", "Energy", "Consumer", "Industrial", "Materials"]
    COMPANIES = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "JPM", "JNJ", "XOM", "PG", "V", "WMT", "DIS", "NFLX"]
    
    def __init__(self):
        self.news_items: List[NewsItem] = []
        self._news_id_counter = 0
    
    def generate_news(self, assets: List[Dict], macro_state: Optional[Dict] = None) -> List[NewsItem]:
        """生成新闻"""
        news_list = []
        
        # 根据宏观状态生成新闻
        if macro_state:
            news_list.extend(self._generate_macro_news(macro_state))
        
        # 生成公司级新闻
        news_list.extend(self._generate_company_news(assets))
        
        # 按重要性排序
        news_list.sort(key=lambda x: list(NewsImportance).index(x.importance))
        
        self.news_items.extend(news_list)
        return news_list
    
    def _generate_macro_news(self, state: Dict) -> List[NewsItem]:
        """生成宏观新闻"""
        news = []
        
        # 通胀新闻
        inflation = state.get("inflation", 0.02)
        if inflation > 0.03:
            news.append(self._create_news(
                "inflation_data",
                importance=NewsImportance.MACRO,
                sentiment=-0.3 * (inflation - 0.02),
                category="MACRO"
            ))
        
        # 就业新闻
        unemployment = state.get("unemployment", 0.05)
        if unemployment > 0.06:
            news.append(self._create_news(
                "employment_report",
                importance=NewsImportance.MACRO,
                sentiment=-0.2,
                category="MACRO"
            ))
        
        # GDP新闻
        gdp = state.get("gdp_growth", 0.025)
        if gdp < 0:
            news.append(self._create_news(
                "gdp_report",
                importance=NewsImportance.BREAKING,
                sentiment=-0.5,
                category="MACRO"
            ))
        
        return news
    
    def _generate_company_news(self, assets: List[Dict]) -> List[NewsItem]:
        """生成公司新闻"""
        news = []
        
        for asset in assets:
            # 随机生成事件
            if random.random() < 0.3:  # 30%概率生成新闻
                event_type = random.choice(["earnings_beat", "earnings_miss", "product_launch", "merger_acquisition"])
                
                sentiment = random.uniform(-0.5, 0.5)
                importance = NewsImportance.MAJOR if abs(sentiment) > 0.3 else NewsImportance.COMPANY
                
                news.append(self._create_news(
                    event_type,
                    company=asset.get("ticker", "Company"),
                    sentiment=sentiment,
                    importance=importance,
                    category="COMPANY"
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
        """创建新闻项"""
        templates = self.TEMPLATES.get(template_type, ["Unknown event occurred"])
        headline = random.choice(templates).format(**kwargs)
        
        # 生成ID
        self._news_id_counter += 1
        news_id = f"NEWS-{self._news_id_counter:06d}"
        
        return NewsItem(
            id=news_id,
            headline=headline,
            body=f"News report: {headline}",
            importance=importance,
            sentiment=sentiment,
            category=category
        )
    
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
    
    def generate_daily_news(self, assets: List[Dict], macro_state: Optional[Dict] = None) -> List[Dict]:
        """生成每日新闻"""
        news_list = self.generator.generate_news(assets, macro_state)
        logger.info(f"Generated {len(news_list)} news items")
        return [n.to_dict() for n in news_list]
    
    def get_headlines(self, limit: int = 20) -> List[Dict]:
        """获取头条新闻"""
        return self.generator.get_news(limit=limit, importance="BREAKING")
    
    def get_briefing(self, hours: int = 24) -> Dict:
        """获取简报"""
        return self.generator.get_briefing(hours)
