"""
FinanceSim Fallback Data
内置初始数据，无网络时可用
"""
import json
from pathlib import Path

# 主要股票数据
FALLBACK_STOCKS = {
    "AAPL": {
        "ticker": "AAPL",
        "name": "Apple Inc.",
        "type": "EQUITY",
        "sector": "Technology",
        "industry": "Consumer Electronics",
        "exchange": "NASDAQ",
        "currency": "USD",
        "market_cap": 2800000000000,
        "beta": 1.25,
        "volatility": 0.28,
        "price": 185.50,
        "fundamentals": {
            "pe_ratio": 28.5,
            "eps": 6.42,
            "dividend_yield": 0.005
        }
    },
    "MSFT": {
        "ticker": "MSFT",
        "name": "Microsoft Corporation",
        "type": "EQUITY",
        "sector": "Technology",
        "industry": "Software",
        "exchange": "NASDAQ",
        "currency": "USD",
        "market_cap": 2500000000000,
        "beta": 1.15,
        "volatility": 0.25,
        "price": 380.00,
        "fundamentals": {
            "pe_ratio": 32.0,
            "eps": 11.80,
            "dividend_yield": 0.008
        }
    },
    "GOOGL": {
        "ticker": "GOOGL",
        "name": "Alphabet Inc.",
        "type": "EQUITY",
        "sector": "Technology",
        "industry": "Internet",
        "exchange": "NASDAQ",
        "currency": "USD",
        "market_cap": 1700000000000,
        "beta": 1.10,
        "volatility": 0.26,
        "price": 140.00,
        "fundamentals": {
            "pe_ratio": 25.0,
            "eps": 5.60,
            "dividend_yield": 0.0
        }
    },
    "AMZN": {
        "ticker": "AMZN",
        "name": "Amazon.com Inc.",
        "type": "EQUITY",
        "sector": "Consumer Discretionary",
        "industry": "E-Commerce",
        "exchange": "NASDAQ",
        "currency": "USD",
        "market_cap": 1500000000000,
        "beta": 1.20,
        "volatility": 0.30,
        "price": 145.00,
        "fundamentals": {
            "pe_ratio": 60.0,
            "eps": 2.42,
            "dividend_yield": 0.0
        }
    },
    "NVDA": {
        "ticker": "NVDA",
        "name": "NVIDIA Corporation",
        "type": "EQUITY",
        "sector": "Technology",
        "industry": "Semiconductors",
        "exchange": "NASDAQ",
        "currency": "USD",
        "market_cap": 1800000000000,
        "beta": 1.75,
        "volatility": 0.45,
        "price": 720.00,
        "fundamentals": {
            "pe_ratio": 65.0,
            "eps": 11.08,
            "dividend_yield": 0.0003
        }
    },
    "JPM": {
        "ticker": "JPM",
        "name": "JPMorgan Chase & Co.",
        "type": "EQUITY",
        "sector": "Financials",
        "industry": "Banking",
        "exchange": "NYSE",
        "currency": "USD",
        "market_cap": 450000000000,
        "beta": 1.05,
        "volatility": 0.22,
        "price": 155.00,
        "fundamentals": {
            "pe_ratio": 10.5,
            "eps": 14.76,
            "dividend_yield": 0.025
        }
    },
    "JNJ": {
        "ticker": "JNJ",
        "name": "Johnson & Johnson",
        "type": "EQUITY",
        "sector": "Healthcare",
        "industry": "Pharmaceuticals",
        "exchange": "NYSE",
        "currency": "USD",
        "market_cap": 380000000000,
        "beta": 0.65,
        "volatility": 0.15,
        "price": 148.00,
        "fundamentals": {
            "pe_ratio": 15.0,
            "eps": 9.87,
            "dividend_yield": 0.030
        }
    },
    "XOM": {
        "ticker": "XOM",
        "name": "Exxon Mobil Corporation",
        "type": "EQUITY",
        "sector": "Energy",
        "industry": "Oil & Gas",
        "exchange": "NYSE",
        "currency": "USD",
        "market_cap": 420000000000,
        "beta": 0.90,
        "volatility": 0.25,
        "price": 105.00,
        "fundamentals": {
            "pe_ratio": 12.0,
            "eps": 8.75,
            "dividend_yield": 0.035
        }
    },
    "PG": {
        "ticker": "PG",
        "name": "Procter & Gamble Co.",
        "type": "EQUITY",
        "sector": "Consumer Staples",
        "industry": "Household Products",
        "exchange": "NYSE",
        "currency": "USD",
        "market_cap": 350000000000,
        "beta": 0.55,
        "volatility": 0.14,
        "price": 145.00,
        "fundamentals": {
            "pe_ratio": 24.0,
            "eps": 6.04,
            "dividend_yield": 0.025
        }
    },
    "V": {
        "ticker": "V",
        "name": "Visa Inc.",
        "type": "EQUITY",
        "sector": "Financials",
        "industry": "Payment Services",
        "exchange": "NYSE",
        "currency": "USD",
        "market_cap": 500000000000,
        "beta": 0.95,
        "volatility": 0.20,
        "price": 260.00,
        "fundamentals": {
            "pe_ratio": 30.0,
            "eps": 8.67,
            "dividend_yield": 0.007
        }
    }
}

# 外汇汇率
FALLBACK_FX = {
    "EURUSD": {"base": "EUR", "quote": "USD", "price": 1.0850},
    "GBPUSD": {"base": "GBP", "quote": "USD", "price": 1.2650},
    "USDJPY": {"base": "USD", "quote": "JPY", "price": 151.50},
    "USDCHF": {"base": "USD", "quote": "CHF", "price": 0.8850},
    "AUDUSD": {"base": "AUD", "quote": "USD", "price": 0.6550},
    "USDCAD": {"base": "USD", "quote": "CAD", "price": 1.3650}
}

# 宏观数据
FALLBACK_MACRO = {
    "gdp_growth": 0.025,
    "inflation": 0.032,
    "unemployment": 0.038,
    "interest_rate": 0.0525,
    "consumer_confidence": 102.6,
    "industrial_production": 0.003
}


def load_fallback_data():
    """加载内置数据"""
    return {
        "stocks": FALLBACK_STOCKS,
        "fx": FALLBACK_FX,
        "macro": FALLBACK_MACRO
    }
