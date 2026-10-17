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

    # ---- 外部数据接入（OFFLINE-FIRST：默认全关，无 key 时行为与之前完全一致）----
    # 总开关：只有显式置为 True 时才会尝试调用任何外部 provider。
    # 默认 False，保证离线/无 key 环境下应用行为与引入框架前 100% 一致。
    USE_EXTERNAL_DATA: bool = False
    # 新闻源 API key（NewsAPI 等）。留空则新闻 provider 不启用。
    NEWS_API_KEY: str = ""
    # 各 provider 的基础 URL，便于测试/私有部署覆盖。
    ALPHA_VANTAGE_BASE_URL: str = "https://www.alphavantage.co/query"
    FRED_BASE_URL: str = "https://api.stlouisfed.org/fred"
    NEWS_BASE_URL: str = "https://newsapi.org/v2"
    # 外部数据内存缓存 TTL（秒），避免重复打接口。
    EXTERNAL_CACHE_TTL_SECONDS: int = 300

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
