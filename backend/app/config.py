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
    # 新闻源 API key（NewsAPI 等）。留空则新闻 provider 自动走免 key 的 RSS 源。
    NEWS_API_KEY: str = ""
    # 各 provider 的基础 URL，便于测试/私有部署覆盖。
    ALPHA_VANTAGE_BASE_URL: str = "https://www.alphavantage.co/query"
    FRED_BASE_URL: str = "https://api.stlouisfed.org/fred"
    NEWS_BASE_URL: str = "https://newsapi.org/v2"

    # ---- 免 key 数据源（OFFLINE-FIRST 默认优先路径：填了 key 才会升级为 keyed 源）----
    # 股价/ETF/指数：CNBC 公开行情接口（单标的，无需 key）。
    CNBC_QUOTE_URL: str = "https://quote.cnbc.com/quote-html-webservice/quote.htm"
    # 外汇：Frankfurter（ECB 参考汇率，无需 key，一次请求覆盖全部主要货币交叉盘）。
    FRANKFURTER_URL: str = "https://api.frankfurter.dev/v1/latest"
    # 宏观：FRED 公开 CSV 下载（无需 key，与 FRED 官方序列 id 完全同构）。
    FRED_CSV_URL: str = "https://fred.stlouisfed.org/graph/fredgraph.csv"
    # 新闻：公开 RSS 源（逗号分隔，无需 key，stdlib 直接解析）。
    NEWS_RSS_FEEDS: str = (
        "https://feeds.content.dowjones.io/public/rss/mw_topstories,"
        "https://feeds.a.dj.com/rss/RSSMarketsMain.xml,"
        "https://www.cnbc.com/id/100003114/device/rss/rss.html"
    )
    # 免 key 价格播种上限（单轮启动尝试的真实标的数，避免对公开源过度请求）。
    KEYLESS_PRICE_MAX: int = 200
    # 免 key 行情并发上限（CNBC 单标的逐只抓取）。
    KEYLESS_PRICE_CONCURRENCY: int = 6
    # 免 key 行情每批之间的节流（秒）。
    KEYLESS_PRICE_BATCH_DELAY: float = 0.08

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
