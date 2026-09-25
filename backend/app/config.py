"""
FinanceSim 配置管理
"""
import os
from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # 应用配置
    APP_NAME: str = "FinanceSim"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    # 数据库配置
    DATABASE_URL: str = "sqlite+aiosqlite:///./financesim.db"
    
    # API 配置
    API_PREFIX: str = "/api/v1"
    
    # 数据源配置
    ALPHA_VANTAGE_API_KEY: str = ""
    FRED_API_KEY: str = ""
    
    # 模拟配置
    DEFAULT_STARTING_CAPITAL: float = 100000.0
    DEFAULT_SIMULATION_SPEED: float = 1.0
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
