"""
Freqtrade Integration Module for Vibe-Trading

Provides live trading execution via Freqtrade REST API.
"""

from .client import FreqtradeClient
from .adapter import FreqtradeAdapter
from .converter import StrategyConverter
from .exceptions import FreqtradeError, TradingError

__all__ = [
    "FreqtradeClient",
    "FreqtradeAdapter",
    "StrategyConverter",
    "FreqtradeError",
    "TradingError",
]
