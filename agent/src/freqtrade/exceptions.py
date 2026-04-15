"""
Freqtrade exceptions module.
"""


class FreqtradeError(Exception):
    """Base exception for Freqtrade errors."""
    pass


class TradingError(FreqtradeError):
    """Trading-related errors (order failed, insufficient balance, etc)."""
    pass


class ConnectionError(FreqtradeError):
    """Connection errors to Freqtrade API."""
    pass


class StrategyError(FreqtradeError):
    """Strategy validation or conversion errors."""
    pass


class AuthenticationError(FreqtradeError):
    """Authentication errors (invalid API key, etc)."""
    pass
