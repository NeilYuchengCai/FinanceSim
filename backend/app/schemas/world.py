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
    # 与 app/schemas/__init__.py 的 WorldResponse 保持一致：
    # 初始资金/模拟速度/难度需随世界响应暴露给前端。
    starting_capital: float = 100000.0
    simulation_speed: float = 1.0
    difficulty: str = "normal"

    class Config:
        from_attributes = True
