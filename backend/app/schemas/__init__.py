"""
FinanceSim Pydantic Schemas
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


# ========== World Schemas ==========

class WorldCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    mode: str = Field(default="simulation", pattern="^(sandbox|simulation|challenge|career)$")
    starting_capital: float = Field(default=100000.0, gt=0)
    starting_date: Optional[datetime] = None
    seed: Optional[str] = None
    simulation_speed: float = Field(default=1.0, gt=0)
    difficulty: str = Field(default="normal", pattern="^(easy|normal|hard|expert)$")


class WorldResponse(BaseModel):
    id: int
    name: str
    mode: str
    current_day: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class WorldUpdate(BaseModel):
    name: Optional[str] = None
    mode: Optional[str] = None
    simulation_speed: Optional[float] = None


# ========== Asset Schemas ==========

class AssetCreate(BaseModel):
    ticker: str = Field(..., min_length=1, max_length=20)
    type: str = Field(..., pattern="^(EQUITY|ETF|INDEX|FX|BOND)$")
    name: Optional[str] = None
    exchange: Optional[str] = None
    sector: Optional[str] = None
    industry: Optional[str] = None
    currency: str = "USD"
    market_cap: Optional[float] = None
    beta: Optional[float] = None
    volatility: Optional[float] = None
    fundamentals: Optional[Dict[str, Any]] = None


class AssetResponse(BaseModel):
    id: int
    ticker: str
    type: str
    name: Optional[str]
    exchange: Optional[str]
    sector: Optional[str]
    industry: Optional[str]
    currency: str
    market_cap: Optional[float]
    beta: Optional[float]
    volatility: Optional[float]
    fundamentals: Optional[Dict[str, Any]]
    
    class Config:
        from_attributes = True


class PriceBar(BaseModel):
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    data_source: str = "simulated"


# ========== Order Schemas ==========

class OrderCreate(BaseModel):
    asset_ticker: str
    side: str = Field(..., pattern="^(BUY|SELL)$")
    type: str = Field(..., pattern="^(MARKET|LIMIT|STOP|STOP_LIMIT)$")
    quantity: float = Field(..., gt=0)
    price: Optional[float] = None
    stop_price: Optional[float] = None


class OrderResponse(BaseModel):
    id: str
    asset_ticker: str
    side: str
    type: str
    quantity: float
    price: Optional[float]
    stop_price: Optional[float]
    filled_quantity: float
    avg_fill_price: Optional[float]
    status: str
    created_by: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class TradeResponse(BaseModel):
    id: str
    asset_ticker: str
    price: float
    quantity: float
    timestamp: datetime
    order_id_buy: Optional[str]
    order_id_sell: Optional[str]
    
    class Config:
        from_attributes = True


# ========== Portfolio Schemas ==========

class PositionResponse(BaseModel):
    asset_ticker: str
    quantity: float
    avg_price: float
    last_price: float
    unrealized_pnl: float
    pnl_percent: float
    
    class Config:
        from_attributes = True


class PortfolioResponse(BaseModel):
    cash: float
    positions: List[PositionResponse]
    total_value: float
    total_pnl: float
    total_pnl_percent: float
    
    class Config:
        from_attributes = True


# ========== Simulation Schemas ==========

class SimulationStatus(BaseModel):
    world_id: int
    current_day: int
    current_time: datetime
    speed: float
    is_paused: bool
    market_regime: str


# ========== Event/News Schemas ==========

class EventCreate(BaseModel):
    type: str
    severity: Optional[float] = Field(None, ge=0, le=1)
    title: Optional[str] = None
    body: Optional[str] = None
    affected_assets: Optional[List[str]] = None
    affected_sectors: Optional[List[str]] = None


class NewsResponse(BaseModel):
    id: str
    headline: str
    importance: str
    sentiment: Optional[float]
    affected_assets: Optional[List[str]]
    created_at: datetime
    
    class Config:
        from_attributes = True


# ========== Analytics Schemas ==========

class ReturnsRequest(BaseModel):
    ticker: str
    period: str = Field(default="1y", pattern="^(1d|1w|1m|3m|6m|1y|5y|max)$")


class ReturnsResponse(BaseModel):
    ticker: str
    returns: List[float]
    annualized_return: float
    sharpe_ratio: float
    max_drawdown: float


class CorrelationRequest(BaseModel):
    tickers: List[str]
    period: str = "1y"


class CorrelationResponse(BaseModel):
    tickers: List[str]
    matrix: List[List[float]]
    period: str
