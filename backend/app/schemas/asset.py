from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Any

class AssetCreate(BaseModel):
    ticker: str
    type: str  # EQUITY, ETF, INDEX, FX, BOND
    name: Optional[str] = None
    exchange: Optional[str] = None
    sector: Optional[str] = None
    industry: Optional[str] = None
    currency: str = "USD"
    market_cap: Optional[float] = None
    beta: Optional[float] = None
    volatility: Optional[float] = None
    fundamentals: Optional[dict] = None
    price: float

class AssetResponse(BaseModel):
    id: int
    world_id: int
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
    fundamentals: Optional[dict]
    created_at: datetime
    
    class Config:
        from_attributes = True

class PriceBar(BaseModel):
    id: int
    asset_id: int
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    data_source: str
    
    class Config:
        from_attributes = True
