"""
Strategy converter - Vibe-Trading → Freqtrade format.
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
import logging

from .models import FreqtradeConfig
from .exceptions import StrategyError

logger = logging.getLogger(__name__)


class FreqtradeIndicator(BaseModel):
    """Freqtrade indicator definition."""
    name: str
    value: str = Field(description="Indicator expression (e.g., 'rsi > 30')")
    

class FreqtradeBuyRule(BaseModel):
    """Buy condition rule."""
    id: str
    expression: str = Field(description="Condition expression")
    

class FreqtradeSellRule(BaseModel):
    """Sell condition rule."""
    id: str
    expression: str = Field(description="Condition expression")


class FreqtradeStrategy(BaseModel):
    """Freqtrade strategy format."""
    name: str
    description: str = ""
    
    # Timeframe
    timeframe: str = "1h"
    
    # Stake settings
    stake_currency: str = "USDT"
    stake_amount: Optional[str] = Field(default="unlimited", description="Stake amount or 'unlimited'")
    
    # Risk management
    stoploss: float = -0.10
    trailing_stop: bool = False
    trailing_stop_positive: float = 0.04
    trailing_stop_offset: float = 0.05
    
    # ROI (Take profit levels)
    minimal_roi: Dict[str, float] = Field(
        default_factory=lambda: {
            "0": 0.05,    # 5% immediately
            "24": 0.03,   # 3% after 24 hours
            "72": 0.01,   # 1% after 72 hours
        }
    )
    
    # Indicators used
    indicators_buy: List[str] = Field(default_factory=list)
    indicators_sell: List[str] = Field(default_factory=list)
    
    # Custom settings
    max_open_trades: int = 1
    ask_strategy: Dict[str, Any] = Field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to Freqtrade strategy dict."""
        return {
            "strategy_name": self.name,
            "timeframe": self.timeframe,
            "stake_currency": self.stake_currency,
            "stake_amount": self.stake_amount,
            "stoploss": self.stoploss,
            "trailing_stop": self.trailing_stop,
            "trailing_stop_positive": self.trailing_stop_positive,
            "trailing_stop_offset": self.trailing_stop_offset,
            "minimal_roi": self.minimal_roi,
            "max_open_trades": self.max_open_trades,
        }


class StrategyConverter:
    """
    Converts Vibe-Trading strategies to Freqtrade format.
    """
    
    # Common indicator mappings
    INDICATOR_TEMPLATES = {
        "rsi": "ta.RSI(close, period=14)",
        "ema": "ta.EMA(close, timeperiod=20)",
        "sma": "ta.SMA(close, timeperiod=50)",
        "macd": "ta.MACD(close)",
        "bollinger": "ta.BBANDS(close, timeperiod=20, nbdevup=2, nbdevdn=2)",
        "atr": "ta.ATR(high, low, close, timeperiod=14)",
        "adx": "ta.ADX(high, low, close, timeperiod=14)",
        "stoch": "ta.STOCH(high, low, close)",
        "cci": "ta.CCI(high, low, close, timeperiod=20)",
        "momentum": "ta.MOM(close, timeperiod=10)",
        "obv": "ta.OBV(close, volume)",
        "vwap": "ta.SMA(close * volume, timeperiod=20) / ta.SMA(volume, timeperiod=20)",
    }
    
    def __init__(self):
        """Initialize converter."""
        self.strategies: Dict[str, FreqtradeStrategy] = {}
    
    def convert(self, vibe_strategy: Dict[str, Any]) -> FreqtradeStrategy:
        """
        Convert Vibe-Trading strategy to Freqtrade format.
        
        Args:
            vibe_strategy: Strategy dict from Vibe-Trading AI
            
        Returns:
            FreqtradeStrategy ready for deployment
        """
        logger.info(f"Converting strategy: {vibe_strategy.get('name', 'unnamed')}")
        
        try:
            # Extract basic info
            name = self._sanitize_name(vibe_strategy.get("name", "VibeStrategy"))
            description = vibe_strategy.get("description", "")
            
            # Create base strategy
            strategy = FreqtradeStrategy(
                name=name,
                description=description,
                timeframe=vibe_strategy.get("timeframe", "1h"),
            )
            
            # Convert indicators
            indicators = vibe_strategy.get("indicators", [])
            buy_conditions = vibe_strategy.get("buy_conditions", [])
            sell_conditions = vibe_strategy.get("sell_conditions", [])
            
            # Process indicators
            if indicators:
                strategy.indicators_buy, strategy.indicators_sell = self._convert_indicators(indicators)
            
            # Process conditions
            if buy_conditions:
                strategy.indicators_buy.extend(self._convert_conditions(buy_conditions, "buy"))
            if sell_conditions:
                strategy.indicators_sell.extend(self._convert_conditions(sell_conditions, "sell"))
            
            # Extract risk parameters
            risk = vibe_strategy.get("risk_management", {})
            if risk:
                strategy.stoploss = risk.get("max_loss", -0.10)
                strategy.trailing_stop = risk.get("trailing_stop", False)
                if risk.get("take_profit"):
                    strategy.minimal_roi = {"0": risk["take_profit"]}
            
            # Extract position sizing
            position = vibe_strategy.get("position_sizing", {})
            if position:
                strategy.max_open_trades = position.get("max_positions", 1)
                if position.get("fixed_amount"):
                    strategy.stake_amount = str(position["fixed_amount"])
            
            # Store converted strategy
            self.strategies[name] = strategy
            
            logger.info(f"Strategy '{name}' converted successfully")
            return strategy
            
        except Exception as e:
            logger.error(f"Strategy conversion failed: {e}")
            raise StrategyError(f"Failed to convert strategy: {e}")
    
    def _sanitize_name(self, name: str) -> str:
        """Sanitize strategy name for Freqtrade."""
        # Replace spaces and special chars
        name = name.replace(" ", "_").replace("-", "_")
        # Remove any non-alphanumeric chars
        name = "".join(c for c in name if c.isalnum() or c == "_")
        # Add prefix if starts with number
        if name[0].isdigit():
            name = "Vibe_" + name
        return name
    
    def _convert_indicators(self, indicators: List[Dict[str, Any]]) -> tuple:
        """Convert indicator definitions."""
        buy_indicators = []
        sell_indicators = []
        
        for ind in indicators:
            name = ind.get("name", "")
            formula = ind.get("formula", "")
            buy_signal = ind.get("buy_signal", False)
            sell_signal = ind.get("sell_signal", False)
            
            # Convert formula if needed
            converted = self._convert_formula(formula)
            
            if buy_signal:
                buy_indicators.append(converted)
            if sell_signal:
                sell_indicators.append(converted)
        
        return buy_indicators, sell_indicators
    
    def _convert_conditions(self, conditions: List[Dict[str, Any]], direction: str) -> List[str]:
        """Convert trade conditions."""
        converted = []
        
        for cond in conditions:
            expr = cond.get("expression", cond.get("condition", ""))
            if expr:
                converted.append(self._convert_formula(expr))
        
        return converted
    
    def _convert_formula(self, formula: str) -> str:
        """
        Convert natural language formula to Python/TA-Lib format.
        
        Examples:
        - "RSI > 70" → "ta.RSI(close, period=14) > 70"
        - "SMA 50 crossing above EMA 200" → "(ta.SMA(close, 50) > ta.EMA(close, 200)) & (ta.SMA(close, 50).shift(1) <= ta.EMA(close, 200).shift(1))"
        """
        formula = formula.strip()
        
        # Handle common patterns
        formula_upper = formula.upper()
        
        # RSI pattern: "RSI > 70" or "RSI(14) > 70"
        if "RSI" in formula_upper:
            import re
            match = re.search(r'RSI\(?(\d+)?\)?', formula_upper)
            period = match.group(1) if match and match.group(1) else "14"
            formula = formula.replace("RSI", f"ta.RSI(close, period={period})")
        
        # EMA pattern
        if "EMA" in formula_upper:
            import re
            match = re.search(r'EMA\(?(\d+)?\)?', formula_upper)
            period = match.group(1) if match and match.group(1) else "20"
            formula = formula.replace("EMA", f"ta.EMA(close, timeperiod={period})")
        
        # SMA pattern
        if "SMA" in formula_upper:
            import re
            match = re.search(r'SMA\(?(\d+)?\)?', formula_upper)
            period = match.group(1) if match and match.group(1) else "50"
            formula = formula.replace("SMA", f"ta.SMA(close, timeperiod={period})")
        
        # MACD pattern
        if "MACD" in formula_upper:
            formula = formula.replace("MACD", "ta.MACD(close)")
        
        # Bollinger pattern
        if "BB" in formula_upper or "BOLLINGER" in formula_upper:
            formula = formula.replace("BB", "ta.BBANDS(close")
            formula = formula.replace("BOLLINGER", "ta.BBANDS(close")
        
        # ATR pattern
        if "ATR" in formula_upper:
            formula = formula.replace("ATR", "ta.ATR(high, low, close, timeperiod=14)")
        
        # ADX pattern
        if "ADX" in formula_upper:
            formula = formula.replace("ADX", "ta.ADX(high, low, close, timeperiod=14)")
        
        # Volume pattern
        if "VOLUME" in formula_upper or "VOL" in formula_upper:
            formula = formula.replace("VOLUME", "volume").replace("VOL", "volume")
        
        # Close price shortcut
        formula = formula.replace("CLOSE", "close").replace("Close", "close")
        formula = formula.replace("PRICE", "close").replace("Price", "close")
        
        # High/Low shortcuts
        formula = formula.replace("HIGH", "high").replace("High", "high")
        formula = formula.replace("LOW", "low").replace("Low", "low")
        
        return formula
    
    def generate_strategy_file(self, strategy: FreqtradeStrategy) -> str:
        """
        Generate Freqtrade strategy Python file content.
        
        Args:
            strategy: FreqtradeStrategy object
            
        Returns:
            Python file content as string
        """
        return f'''# pragma pylint: disable=missing-docstring, invalid-name, pointless-string-statement
# flake8: noqa: F401

from freqtrade.strategy import IStrategy
import freqtrade.vendor.qtpylib.indicators as qtpylib
import ta.trade as trade
import numpy as np


class {strategy.name}(IStrategy):
    """
    {strategy.description or f'{strategy.name} - Generated by Vibe-Trading AI'}
    """
    
    # Strategy parameters
    timeframe = "{strategy.timeframe}"
    stoploss = {strategy.stoploss}
    trailing_stop = {strategy.trailing_stop}
    trailing_stop_positive = {strategy.trailing_stop_positive}
    trailing_stop_offset = {strategy.trailing_stop_offset}
    minimal_roi = {strategy.minimal_roi}
    
    # Position sizing
    max_open_trades = {strategy.max_open_trades}
    stake_{strategy.stake_currency.lower()}_amount = {strategy.stake_amount}
    
    # Process only new candles
    process_only_new_candles = True
    
    # Use default order types
    order_types = {{
        "entry": "market",
        "exit": "market",
        "stoploss": "market",
        "stoploss_on_exchange": False
    }}
    
    # Buy indicators
    @property
    def indicators_buy(self):
        return {strategy.indicators_buy}
    
    # Sell indicators  
    @property
    def indicators_sell(self):
        return {strategy.indicators_sell}
    
    def populate_indicators(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        """
        Add indicators to dataframe.
        """
        # Add your indicators here
        # Example:
        # dataframe["rsi"] = ta.RSI(dataframe["close"])
        # dataframe["ema"] = ta.EMA(dataframe["close"], timeperiod=20)
        
        return dataframe
    
    def populate_buy_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        """
        Define buy signals.
        """
        dataframe.loc[
            (
                # Add your buy conditions here
                {" AND ".join(strategy.indicators_buy) if strategy.indicators_buy else "True"}
            ),
            "enter_long",
        ] = 1
        
        return dataframe
    
    def populate_sell_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        """
        Define sell signals.
        """
        dataframe.loc[
            (
                # Add your sell conditions here
                {" AND ".join(strategy.indicators_sell) if strategy.indicators_sell else "True"}
            ),
            "exit_long",
        ] = 1
        
        return dataframe
'''
    
    def validate_strategy(self, strategy: FreqtradeStrategy) -> List[str]:
        """
        Validate strategy for common issues.
        
        Returns:
            List of warning/error messages (empty if valid)
        """
        issues = []
        
        # Check name
        if not strategy.name or len(strategy.name) < 3:
            issues.append("Strategy name too short")
        
        # Check stoploss
        if strategy.stoploss >= 0:
            issues.append("Stoploss should be negative (e.g., -0.10 for -10%)")
        
        # Check ROI
        for roi, value in strategy.minimal_roi.items():
            if value <= 0:
                issues.append(f"ROI value for '{roi}' should be positive")
        
        # Check trailing stop
        if strategy.trailing_stop:
            if strategy.trailing_stop_positive <= abs(strategy.stoploss):
                issues.append("Trailing stop positive should be greater than stoploss")
        
        return issues
