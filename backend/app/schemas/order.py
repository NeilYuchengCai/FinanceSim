from pydantic import BaseModel
from datetime import datetime
from decimal import Decimal
from typing import Optional

class OrderCreate(BaseModel):
    asset_ticker: str
    side: str  # BUY or SELL
    type: str  # MARKET, LIMIT, STOP, STOP_LIMIT
    quantity: float
    price: Optional[float] = None
    stop_price: Optional[float] = None

class OrderResponse(BaseModel):
    id: str
    ticker: str
    side: str
    type: str
    quantity: float
    price: Optional[float]
    filled_quantity: float
    status: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class TradeResponse(BaseModel):
    id: str
    ticker: str
    price: float
    quantity: float
    timestamp: datetime
    
    class Config:
        from_attributes = True
