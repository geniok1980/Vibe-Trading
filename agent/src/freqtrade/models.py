"""
Freqtrade data models.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class TradeStatus(str, Enum):
    """Trade status enum."""
    OPEN = "open"
    CLOSED = "closed"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class Balance(BaseModel):
    """Account balance model."""
    total: float = Field(description="Total balance")
    free: float = Field(description="Available balance")
    used: float = Field(description="Balance used in orders")
    currency: str = Field(description="Currency symbol (e.g., USDT)")


class Trade(BaseModel):
    """Trade/Position model."""
    trade_id: int = Field(alias="trade_id")
    pair: str = Field(description="Trading pair (e.g., BTC/USDT)")
    side: str = Field(description="Trade side (long/short)")
    amount: float = Field(description="Trade amount")
    entry_price: float = Field(description="Entry price")
    current_price: Optional[float] = Field(default=None, description="Current price")
    close_price: Optional[float] = Field(default=None, description="Close price")
    pnl: Optional[float] = Field(default=None, description="Profit/Loss")
    pnl_pct: Optional[float] = Field(default=None, description="P&L percentage")
    status: TradeStatus = Field(description="Trade status")
    open_date: datetime = Field(alias="open_date")
    close_date: Optional[datetime] = Field(default=None, alias="close_date")
    fee: Optional[float] = Field(default=None, description="Trade fee")

    class Config:
        populate_by_name = True


class TradeResponse(BaseModel):
    """Trade API response wrapper."""
    trades: List[Trade]
    trades_count: int
    total_trades: int


class OrderStatus(str, Enum):
    """Order status enum."""
    PENDING = "pending"
    OPEN = "open"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


class Order(BaseModel):
    """Order model."""
    order_id: str
    symbol: str
    side: str  # buy/sell
    type: str  # market/limit
    amount: float
    price: Optional[float] = None
    status: OrderStatus
    filled: float = 0.0
    remaining: float = 0.0
    created_at: Optional[datetime] = None


class BotStatus(BaseModel):
    """Bot status model."""
    is_running: bool = Field(description="Is bot running")
    mode: str = Field(description="Bot mode (spot/margin/futures)")
    strategy: str = Field(description="Current strategy name")
    dry_run: bool = Field(description="Is dry-run (paper trading) mode")
    pairlist: List[str] = Field(description="Trading pairs")
    stake_currency: str = Field(description="Stake currency")
    stake_amount: Optional[float] = Field(default=None, description="Stake amount")
    open_trades: int = Field(description="Number of open trades")
    max_open_trades: int = Field(description="Max concurrent trades")


class StrategyInfo(BaseModel):
    """Strategy information."""
    name: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    indicators: List[str] = Field(default_factory=list)
    buy_signal: bool = True
    sell_signal: bool = True


class FreqtradeConfig(BaseModel):
    """Freqtrade configuration for live trading."""
    api_url: str = Field(default="http://localhost:8080")
    api_key: str = Field(description="Freqtrade API key")
    exchange: str = Field(default="binance", description="Exchange name")
    stake_currency: str = Field(default="USDT", description="Stake currency")
    stake_amount: Optional[float] = Field(default=None, description="Stake amount (None = unlimited)")
    max_open_trades: int = Field(default=1, description="Max concurrent trades")
    dry_run: bool = Field(default=True, description="Paper trading mode")
    stoploss: float = Field(default=-0.10, description="Default stoploss")
    trailing_stop: bool = Field(default=False, description="Enable trailing stop")
    timeframe: str = Field(default="1h", description="Default timeframe")
