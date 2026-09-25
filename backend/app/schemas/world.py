from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class WorldCreate(BaseModel):
    name: str
    mode: str = "simulation"
    seed: Optional[str] = None

class WorldResponse(BaseModel):
    id: int
    name: str
    mode: str
    created_at: datetime
    current_day: int
    seed: Optional[str] = None
    
    class Config:
        from_attributes = True
