"""
Fallback data module for offline-first operation.
All data is deterministically generated from seeds.
"""
from app.data.fallback.fx_history import get_fx_fallback_data
from app.data.fallback.commodities import generate_commodity_initial_state, generate_commodity_price_history

__all__ = [
    "get_fx_fallback_data",
    "generate_commodity_initial_state",
    "generate_commodity_price_history",
]
