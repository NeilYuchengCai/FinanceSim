"""
Fallback data module for offline-first operation.
All data is deterministically generated from seeds.
"""
from app.data.fallback.fx_history import generate_fx_history
from app.data.fallback.commodities import generate_commodity_initial_state

__all__ = [
    "generate_fx_history",
    "generate_commodity_initial_state",
]
