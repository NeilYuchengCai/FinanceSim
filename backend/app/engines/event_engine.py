"""
FinanceSim Event Engine
负责事件生成、传播和时序追踪
"""
import random
import uuid
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class Event:
    """事件类"""
    id: str
    type: str  # COMPANY, EARNINGS, MA, MACRO, CENTRAL_BANK, etc.
    severity: float  # 0.0 to 1.0
    title: str
    body: str
    affected_assets: List[str]
    affected_sectors: List[str]
    macro_effect: Dict = field(default_factory=dict)
    sentiment_effect: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)
    duration_days: int = 0  # 事件影响持续时间
    propagated: bool = False  # 是否已传播

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "type": self.type,
            "severity": self.severity,
            "title": self.title,
            "body": self.body,
            "affected_assets": self.affected_assets,
            "affected_sectors": self.affected_sectors,
            "macro_effect": self.macro_effect,
            "sentiment_effect": self.sentiment_effect,
            "created_at": self.created_at.isoformat(),
            "duration_days": self.duration_days
        }


class EventGenerator:
    """事件生成器"""
    
    EVENT_TYPES = [
        ("earnings", "COMPANY"),
        ("product_launch", "COMPANY"),
        ("management_change", "COMPANY"),
        ("regulatory", "COMPANY"),
        ("ma", "COMPANY"),
        ("guidance", "COMPANY"),
        ("geopolitical", "MACRO"),
        ("central_bank", "MACRO"),
        ("inflation_shock", "MACRO"),
        ("employment_shock", "MACRO"),
        ("liquidity_crisis", "CRISIS"),
        ("banking_crisis", "CRISIS"),
        ("black_swan", "CRISIS")
    ]
    
    SECTOR_MAP = {
        "earnings": ["Technology", "Healthcare", "Finance", "Energy", "Consumer"],
        "product_launch": ["Technology", "Consumer"],
        "management_change": ["Technology", "Finance"],
        "regulatory": ["Finance", "Healthcare", "Energy"],
        "ma": ["Technology", "Healthcare", "Finance"],
        "geopolitical": ["All"],
        "central_bank": ["All"],
        "inflation_shock": ["All"],
        "employment_shock": ["All"],
        "liquidity_crisis": ["Finance", "Technology"],
        "banking_crisis": ["Finance"],
        "black_swan": ["All"]
    }
    
    def __init__(self, world_id: int):
        self.world_id = world_id
        self.events: List[Event] = []
        self._day_counter = 0
    
    def generate_event(self, assets: List[Dict], sectors: List[str]) -> Event:
        """生成随机事件"""
        event_type, event_category = random.choice(self.EVENT_TYPES)
        severity = random.uniform(0.1, 1.0)
        
        # 根据事件类型调整严重程度
        if event_category == "CRISIS":
            severity = max(severity, 0.6)  # 危机事件至少中等强度
        elif event_category == "COMPANY":
            severity *= 0.6  # 公司事件强度减半
        
        # 确定受影响资产
        affected_assets = []
        affected_sectors = []
        
        if event_category == "COMPANY":
            # 公司级事件，影响单个或少数资产
            n_affected = random.randint(1, min(3, len(assets)))
            affected = random.sample(assets, n_affected)
            affected_assets = [a["ticker"] for a in affected]
            affected_sectors = list(set(a.get("sector", "Unknown") for a in affected))
        elif event_category == "MACRO":
            # 宏观事件，影响多个资产
            n_affected = random.randint(5, min(20, len(assets)))
            affected = random.sample(assets, n_affected)
            affected_assets = [a["ticker"] for a in affected]
            affected_sectors = list(set(a.get("sector", "Unknown") for a in assets))
        elif event_category == "CRISIS":
            # 危机事件，影响全市场
            affected_assets = [a["ticker"] for a in assets]
            affected_sectors = sectors if sectors else ["All"]
        
        # 生成标题和正文
        title, body = self._generate_content(event_type, severity, affected_assets, sectors)
        
        # 情绪影响（与事件类型相关）
        sentiment = self._calculate_sentiment(event_type, severity)
        
        # 持续时间（危机事件持续更长）
        duration = self._calculate_duration(event_type, severity)
        
        event = Event(
            id=str(uuid.uuid4()),
            type=event_type,
            severity=severity,
            title=title,
            body=body,
            affected_assets=affected_assets,
            affected_sectors=affected_sectors,
            sentiment_effect=sentiment,
            duration_days=duration,
            macro_effect=self._generate_macro_effect(event_type, severity)
        )
        
        self.events.append(event)
        logger.info(f"Event generated: {event_type} severity={severity:.2f} duration={duration}days")
        
        return event
    
    def _generate_macro_effect(self, event_type: str, severity: float) -> Dict:
        """生成宏观效应"""
        effects = {}
        
        if event_type in ["inflation_shock", "employment_shock"]:
            effects["inflation_impact"] = severity * random.uniform(0.005, 0.02)
            effects["gdp_impact"] = -severity * random.uniform(0.002, 0.01)
        elif event_type in ["central_bank", "geopolitical"]:
            effects["rate_impact"] = severity * random.uniform(0.001, 0.005)
            effects["risk_premium"] = severity * random.uniform(0.002, 0.01)
        elif event_type in ["liquidity_crisis", "banking_crisis"]:
            effects["credit_spread"] = severity * random.uniform(0.01, 0.05)
            effects["liquidity_premium"] = severity * random.uniform(0.005, 0.02)
        elif event_type == "black_swan":
            effects["volatility_spike"] = severity * random.uniform(0.1, 0.3)
            effects["risk_premium"] = severity * random.uniform(0.02, 0.05)
        
        return effects
    
    def _calculate_sentiment(self, event_type: str, severity: float) -> float:
        """计算情绪影响"""
        positive_events = ["earnings", "product_launch", "ma"]
        negative_events = ["regulatory", "liquidity_crisis", "banking_crisis", "black_swan"]
        
        if event_type in positive_events:
            return random.uniform(0.2, 0.8) * severity
        elif event_type in negative_events:
            return random.uniform(-0.8, -0.2) * severity
        else:
            return random.uniform(-1, 1) * severity
    
    def _calculate_duration(self, event_type: str, severity: float) -> int:
        """计算事件持续时间（天数）"""
        if event_type in ["earnings", "product_launch", "guidance"]:
            return random.randint(1, 3)
        elif event_type in ["regulatory", "management_change", "ma"]:
            return random.randint(3, 10)
        elif event_type in ["geopolitical", "central_bank", "inflation_shock", "employment_shock"]:
            return random.randint(5, 20)
        elif event_type in ["liquidity_crisis", "banking_crisis"]:
            return random.randint(10, 30)
        elif event_type == "black_swan":
            return random.randint(20, 60)
        else:
            return random.randint(1, 5)
    
    def _generate_content(self, event_type: str, severity: float, 
                          affected: List[str], sectors: List[str]) -> Tuple[str, str]:
        """生成事件内容"""
        templates = {
            "earnings": (
                f"{affected[0] if affected else 'Company'} Reports Quarterly Earnings",
                f"Earnings report released for {affected[0] if affected else 'the company'}. "
                f"Severity: {'high' if severity > 0.7 else 'moderate' if severity > 0.3 else 'low'}."
            ),
            "product_launch": (
                f"{affected[0] if affected else 'Company'} Launches New Product",
                f"A new product announcement from {affected[0] if affected else 'the company'} has been made."
            ),
            "management_change": (
                f"{affected[0] if affected else 'Company'} Announces Leadership Change",
                f"Management change at {affected[0] if affected else 'the company'} has been announced."
            ),
            "regulatory": (
                "Regulatory Action Announced",
                f"New regulatory action affecting {', '.join(affected[:3]) if affected else 'the sector'}."
            ),
            "ma": (
                f"Major M&A Activity",
                f"Significant merger or acquisition activity involving {', '.join(affected[:2]) if affected else 'companies'}."
            ),
            "geopolitical": (
                "Geopolitical Tension Escalates",
                "Rising geopolitical tensions affecting global markets."
            ),
            "central_bank": (
                "Central Bank Policy Decision",
                "Major central bank has announced a policy decision affecting interest rates."
            ),
            "inflation_shock": (
                "Inflation Surprise",
                "Unexpected inflation data released, impacting market expectations."
            ),
            "employment_shock": (
                "Employment Data Shock",
                "Surprise employment figures released, affecting market sentiment."
            ),
            "liquidity_crisis": (
                "Liquidity Crisis Emerges",
                "Signs of liquidity stress in financial markets detected."
            ),
            "banking_crisis": (
                "Banking Sector Stress",
                "Critical developments in the banking sector affecting multiple institutions."
            ),
            "black_swan": (
                "Black Swan Event",
                "Unprecedented event with major market impact."
            )
        }
        
        title, body = templates.get(event_type, ("Unknown Event", "An event has occurred."))
        return title, body
    
    def get_events(self, limit: int = 50) -> List[Dict]:
        """获取最近事件"""
        return [
            e.to_dict()
            for e in reversed(self.events)
        ][:limit]
    
    def get_events_by_type(self, event_type: str, limit: int = 20) -> List[Dict]:
        """按类型获取事件"""
        return [
            e.to_dict()
            for e in reversed(self.events)
            if e.type == event_type
        ][:limit]
    
    def get_events_by_asset(self, ticker: str, limit: int = 20) -> List[Dict]:
        """按资产获取事件"""
        return [
            e.to_dict()
            for e in reversed(self.events)
            if ticker in e.affected_assets
        ][:limit]


class EventPropagation:
    """事件传播引擎 - 多级影响传播"""
    
    # 传播衰减系数（按层级）
    LEVEL_DECAYS = {
        "direct": 1.0,
        "sector": 0.7,
        "market": 0.5,
        "macro": 0.3,
        "fx": 0.2,
        "bond": 0.15
    }
    
    def __init__(self):
        self.propagation_log: List[Dict] = []
    
    def propagate(self, event: Event, all_assets: List[Dict]) -> List[Dict]:
        """
        多级传播事件影响
        返回: [{asset_ticker, impact, level, sector}, ...]
        """
        impacts = []
        asset_map = {a["ticker"]: a for a in all_assets}
        
        # Level 1: 直接受影响资产
        for ticker in event.affected_assets:
            asset = asset_map.get(ticker, {})
            impacts.append({
                "ticker": ticker,
                "impact": event.severity * event.sentiment_effect,
                "level": "direct",
                "sector": asset.get("sector", "Unknown")
            })
        
        # Level 2: 行业传播（同Sector的其他资产）
        sector_assets = {}
        for a in all_assets:
            sector = a.get("sector", "Unknown")
            if sector not in sector_assets:
                sector_assets[sector] = []
            sector_assets[sector].append(a["ticker"])
        
        for sector in event.affected_sectors:
            for ticker in sector_assets.get(sector, []):
                if ticker not in event.affected_assets:
                    impacts.append({
                        "ticker": ticker,
                        "impact": event.severity * self.LEVEL_DECAYS["sector"] * event.sentiment_effect,
                        "level": "sector",
                        "sector": sector
                    })
        
        # Level 3: 市场传播（当severity > 0.7时）
        if event.severity > 0.7:
            all_tickers = [a["ticker"] for a in all_assets]
            already_impacted = {i["ticker"] for i in impacts}
            for ticker in all_tickers:
                if ticker not in already_impacted:
                    impacts.append({
                        "ticker": ticker,
                        "impact": event.severity * self.LEVEL_DECAYS["market"] * event.sentiment_effect,
                        "level": "market",
                        "sector": asset_map.get(ticker, {}).get("sector", "Unknown")
                    })
        
        # Level 4: 宏观传播（当severity > 0.8时）
        if event.severity > 0.8 and event.macro_effect:
            impacts.append({
                "ticker": "MACRO",
                "impact": event.severity * self.LEVEL_DECAYS["macro"],
                "level": "macro",
                "effects": event.macro_effect
            })
        
        # 记录传播日志
        self.propagation_log.append({
            "event_id": event.id,
            "event_type": event.type,
            "total_impacts": len(impacts),
            "timestamp": event.created_at.isoformat()
        })
        
        logger.info(f"Event propagation: {event.type} -> {len(impacts)} assets")
        return impacts
    
    def get_propagation_summary(self, limit: int = 20) -> List[Dict]:
        """获取传播摘要"""
        return list(reversed(self.propagation_log))[:limit]


class EventTimeline:
    """事件时间线追踪"""
    
    def __init__(self):
        self.events_by_asset: Dict[str, List[Dict]] = {}
        self.events_by_date: Dict[str, List[Dict]] = {}
    
    def add_event(self, event: Event, assets: List[Dict]):
        """添加事件到时间线"""
        event_dict = event.to_dict()
        
        # 按资产索引
        for ticker in event.affected_assets:
            if ticker not in self.events_by_asset:
                self.events_by_asset[ticker] = []
            self.events_by_asset[ticker].append(event_dict)
        
        # 按日期索引
        date_key = event.created_at.strftime("%Y-%m-%d")
        if date_key not in self.events_by_date:
            self.events_by_date[date_key] = []
        self.events_by_date[date_key].append(event_dict)
    
    def get_asset_timeline(self, ticker: str, limit: int = 50) -> List[Dict]:
        """获取资产事件时间线"""
        return self.events_by_asset.get(ticker, [])[-limit:]
    
    def get_date_range(self, start_date: str, end_date: str) -> List[Dict]:
        """获取日期范围内的事件"""
        results = []
        for date, events in self.events_by_date.items():
            if start_date <= date <= end_date:
                results.extend(events)
        return sorted(results, key=lambda x: x["created_at"])
