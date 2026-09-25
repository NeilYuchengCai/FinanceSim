"""
FinanceSim Simulation Clock
负责模拟时间管理
"""
import time
import logging
from datetime import datetime, timedelta
from typing import Optional, Callable
from enum import Enum

logger = logging.getLogger(__name__)


class SimulationSpeed(Enum):
    PAUSED = 0
    X1 = 1
    X10 = 10
    X100 = 100
    X1000 = 1000


class SimulationClock:
    """模拟时钟"""
    
    def __init__(self, start_time: datetime = None):
        self.start_time = start_time or datetime.now()
        self.current_time = self.start_time
        self.current_day = 0
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
        
        # 根据速度计算模拟时间推进
        if self.speed == SimulationSpeed.X1:
            sim_duration = elapsed  # 1:1 映射
        elif self.speed == SimulationSpeed.X10:
            sim_duration = elapsed * 10
        elif self.speed == SimulationSpeed.X100:
            sim_duration = elapsed * 100
        elif self.speed == SimulationSpeed.X1000:
            sim_duration = elapsed * 1000
        else:
            sim_duration = 0
        
        # 推进模拟时间（每分钟为一个 tick）
        sim_delta = timedelta(minutes=sim_duration)
        old_day = self.current_day
        
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
        """获取时钟状态"""
        return {
            "current_time": self.current_time.isoformat(),
            "current_day": self.current_day,
            "speed": self.speed.name,
            "is_paused": self.is_paused
        }
