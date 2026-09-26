"""
FinanceSim Simulation Clock
负责模拟时间管理
"""
import time
import logging
from datetime import datetime, timedelta
from typing import Optional, Callable
from enum import Enum

from app.services.trading_calendar import (
    holiday_name,
    is_trading_day,
    market_status,
    next_trading_day,
    weekday_name,
)

logger = logging.getLogger(__name__)


class SimulationSpeed(Enum):
    PAUSED = 0
    X1 = 1
    X10 = 10
    X100 = 100
    X1000 = 1000


class SimulationClock:
    """模拟时钟"""
    
    def __init__(self, start_time: datetime = None, current_day: int = 0):
        self.start_time = start_time or datetime.now()
        # 从持久化天数恢复时同步推进模拟时间，保证 tick() 的天数计算与恢复值自洽
        self.current_time = self.start_time + timedelta(days=current_day)
        self.current_day = current_day
        self.speed = SimulationSpeed.X1
        self.is_paused = True
        self.last_tick_time = None
        self.tick_callbacks: list = []
        self.day_end_callbacks: list = []
    
    def start(self):
        """开始模拟"""
        self.is_paused = False
        self.last_tick_time = time.time()
        logger.info(f"Simulation started at {self.current_time}")
    
    def pause(self):
        """暂停模拟"""
        self.is_paused = True
        logger.info(f"Simulation paused at day {self.current_day}")
    
    def reset(self, new_start_time: datetime = None):
        """重置模拟"""
        self.start_time = new_start_time or datetime.now()
        self.current_time = self.start_time
        self.current_day = 0
        self.is_paused = True
        logger.info("Simulation reset")
    
    def set_speed(self, speed: SimulationSpeed):
        """设置速度"""
        self.speed = speed
        logger.info(f"Simulation speed set to {speed.name}")
    
    def add_tick_callback(self, callback: Callable):
        """添加 tick 回调"""
        self.tick_callbacks.append(callback)
    
    def add_day_end_callback(self, callback: Callable):
        """添加日终回调"""
        self.day_end_callbacks.append(callback)
    
    def tick(self) -> bool:
        """
        执行一个 tick
        Returns: True if a new day started
        """
        if self.is_paused:
            return False
        
        now = time.time()
        elapsed = now - self.last_tick_time

        # 根据速度计算模拟时间推进：
        # elapsed 是真实经过的秒数，乘以速度倍率后仍是「秒」的量纲，
        # 因此统一按秒推进模拟时间（X1 = 1 秒真实时间 -> 1 秒模拟时间）。
        # PAUSED 的 value 为 0，倍率 0 自然不推进，无需特判。
        multiplier = self.speed.value if isinstance(self.speed, SimulationSpeed) else 1
        sim_delta = timedelta(seconds=elapsed * multiplier)

        self.current_time += sim_delta
        self.last_tick_time = now
        
        # 检查是否跨天
        new_day = int((self.current_time - self.start_time).days)
        if new_day > self.current_day:
            self.current_day = new_day
            logger.info(f"New simulation day: {self.current_day}")
            
            # 触发日终回调
            for cb in self.day_end_callbacks:
                try:
                    cb(self.current_day)
                except Exception as e:
                    logger.error(f"Day end callback error: {e}")
            
            return True
        
        # 触发 tick 回调
        for cb in self.tick_callbacks:
            try:
                cb(self.current_time)
            except Exception as e:
                logger.error(f"Tick callback error: {e}")
        
        return False
    
    def step(self, days: int = 1):
        """步进指定天数"""
        old_day = self.current_day
        self.current_time += timedelta(days=days)
        self.current_day = old_day + days
        logger.info(f"Stepped {days} days to day {self.current_day}")
        
        # 触发日终回调
        for cb in self.day_end_callbacks:
            try:
                cb(self.current_day)
            except Exception as e:
                logger.error(f"Day end callback error: {e}")
        
        return self.current_day
    
    def get_status(self) -> dict:
        """
        获取时钟状态。
        除原有的 current_time / current_day / speed / is_paused 外，
        附带交易日历信息（星期几、是否交易日、市场状态、下一个交易日、节假日名称）。
        """
        sim_time = self.current_time.replace(microsecond=0)
        return {
            "current_time": sim_time.isoformat(),
            "current_day": self.current_day,
            "speed": self.speed.name,
            "is_paused": self.is_paused,
            "weekday": weekday_name(sim_time),
            "is_trading_day": is_trading_day(sim_time),
            "market_status": market_status(sim_time),
            "next_trading_day": next_trading_day(sim_time).isoformat(),
            "holiday_name": holiday_name(sim_time),
        }
