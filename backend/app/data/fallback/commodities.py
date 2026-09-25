"""
Fallback commodity data generator.
Deterministically generates initial commodity states.
"""
import random
from typing import Dict, List


def generate_commodity_initial_state() -> Dict[str, Dict]:
    """
    Generate initial commodity state for offline mode.
    Uses deterministic seed for reproducibility.
    """
    random.seed(42)
    
    commodities = {
        "CL": {
            "ticker": "CL",
            "name": "WTI Crude Oil",
            "category": "ENERGY",
            "price": 78.50,
            "change_24h": 0.012,
            "high_24h": 79.20,
            "low_24h": 77.80,
            "volume": 125000,
            "open_interest": 450000,
            "supply_demand": {"demand_trend": "stable", "supply_risk": "low"},
            "inventory": 385.2,  # million barrels
        },
        "BZ": {
            "ticker": "BZ",
            "name": "Brent Crude",
            "category": "ENERGY",
            "price": 82.30,
            "change_24h": 0.008,
            "high_24h": 83.10,
            "low_24h": 81.50,
            "volume": 98000,
            "open_interest": 380000,
            "supply_demand": {"demand_trend": "stable", "supply_risk": "low"},
            "inventory": 342.8,
        },
        "NG": {
            "ticker": "NG",
            "name": "Natural Gas",
            "category": "ENERGY",
            "price": 2.85,
            "change_24h": -0.025,
            "high_24h": 2.92,
            "low_24h": 2.80,
            "volume": 156000,
            "open_interest": 520000,
            "supply_demand": {"demand_trend": "increasing", "supply_risk": "medium"},
            "inventory": 245.6,
        },
        "GC": {
            "ticker": "GC",
            "name": "Gold",
            "category": "PRECIOUS_METAL",
            "price": 2345.80,
            "change_24h": 0.005,
            "high_24h": 2358.50,
            "low_24h": 2332.40,
            "volume": 89000,
            "open_interest": 290000,
            "supply_demand": {"demand_trend": "strong", "supply_risk": "low"},
            "inventory": 8500.0,
        },
        "SI": {
            "ticker": "SI",
            "name": "Silver",
            "category": "PRECIOUS_METAL",
            "price": 28.45,
            "change_24h": 0.015,
            "high_24h": 28.90,
            "low_24h": 28.10,
            "volume": 45000,
            "open_interest": 125000,
            "supply_demand": {"demand_trend": "stable", "supply_risk": "medium"},
            "inventory": 420.5,
        },
        "HG": {
            "ticker": "HG",
            "name": "Copper",
            "category": "METAL",
            "price": 4.52,
            "change_24h": -0.008,
            "high_24h": 4.58,
            "low_24h": 4.48,
            "volume": 67000,
            "open_interest": 180000,
            "supply_demand": {"demand_trend": "decreasing", "supply_risk": "medium"},
            "inventory": 125.3,
        },
        "PL": {
            "ticker": "PL",
            "name": "Platinum",
            "category": "PRECIOUS_METAL",
            "price": 985.50,
            "change_24h": 0.003,
            "high_24h": 992.00,
            "low_24h": 978.50,
            "volume": 12000,
            "open_interest": 35000,
            "supply_demand": {"demand_trend": "stable", "supply_risk": "high"},
            "inventory": 25.8,
        },
        "ZC": {
            "ticker": "ZC",
            "name": "Corn",
            "category": "AGRICULTURE",
            "price": 4.85,
            "change_24h": 0.005,
            "high_24h": 4.92,
            "low_24h": 4.78,
            "volume": 34000,
            "open_interest": 95000,
            "supply_demand": {"demand_trend": "stable", "supply_risk": "medium"},
            "inventory": 2100.5,
        },
        "ZW": {
            "ticker": "ZW",
            "name": "Wheat",
            "category": "AGRICULTURE",
            "price": 6.12,
            "change_24h": -0.012,
            "high_24h": 6.25,
            "low_24h": 6.05,
            "volume": 28000,
            "open_interest": 78000,
            "supply_demand": {"demand_trend": "decreasing", "supply_risk": "medium"},
            "inventory": 1850.2,
        },
        "ZS": {
            "ticker": "ZS",
            "name": "Soybeans",
            "category": "AGRICULTURE",
            "price": 12.85,
            "change_24h": 0.008,
            "high_24h": 13.02,
            "low_24h": 12.68,
            "volume": 41000,
            "open_interest": 115000,
            "supply_demand": {"demand_trend": "stable", "supply_risk": "medium"},
            "inventory": 980.5,
        },
    }
    
    return commodities


def generate_commodity_price_history() -> Dict[str, List[Dict]]:
    """
    Generate historical price data for commodities.
    30 days of OHLCV data with deterministic randomness.
    """
    random.seed(123)
    
    initial_prices = {
        "CL": {"price": 78.50, "volatility": 0.015},
        "BZ": {"price": 82.30, "volatility": 0.014},
        "NG": {"price": 2.85, "volatility": 0.025},
        "GC": {"price": 2345.80, "volatility": 0.008},
        "SI": {"price": 28.45, "volatility": 0.012},
        "HG": {"price": 4.52, "volatility": 0.010},
        "PL": {"price": 985.50, "volatility": 0.011},
        "ZC": {"price": 4.85, "volatility": 0.009},
        "ZW": {"price": 6.12, "volatility": 0.010},
        "ZS": {"price": 12.85, "volatility": 0.009},
    }
    
    history = {}
    
    for ticker, config in initial_prices.items():
        base_price = config["price"]
        volatility = config["volatility"]
        
        prices = []
        current_price = base_price
        
        for day in range(30, 0, -1):
            change = random.gauss(0, volatility)
            current_price *= (1 + change)
            
            high = current_price * (1 + abs(random.gauss(0, volatility * 0.5)))
            low = current_price * (1 - abs(random.gauss(0, volatility * 0.5)))
            volume = int(random.uniform(20000, 150000))
            
            prices.append({
                "date": f"2026-09-{day:02d}",
                "open": round(current_price * (1 + random.gauss(0, volatility * 0.3)), 2),
                "high": round(high, 2),
                "low": round(low, 2),
                "close": round(current_price, 2),
                "volume": volume,
            })
        
        history[ticker] = prices
    
    return history
