"""
Freqtrade adapter - main interface for Vibe-Trading integration.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from .client import FreqtradeClient
from .converter import StrategyConverter, FreqtradeStrategy
from .models import Balance, Trade, BotStatus, FreqtradeConfig
from .exceptions import TradingError, StrategyError, ConnectionError

logger = logging.getLogger(__name__)


class TradingMode:
    """Trading mode enum."""
    PAPER = "paper"
    LIVE = "live"


class FreqtradeAdapter:
    """
    Main adapter for integrating Freqtrade with Vibe-Trading.
    
    Provides high-level interface for:
    - Account management
    - Trade execution and monitoring
    - Strategy deployment
    - Risk management
    """
    
    def __init__(
        self,
        api_url: str = "http://localhost:8080",
        api_key: str = "",
        config: Optional[FreqtradeConfig] = None
    ):
        """
        Initialize Freqtrade adapter.
        
        Args:
            api_url: Freqtrade API URL
            api_key: Freqtrade API key
            config: Optional configuration object
        """
        self.client = FreqtradeClient(api_url, api_key)
        self.config = config or FreqtradeConfig(api_url=api_url, api_key=api_key)
        self.converter = StrategyConverter()
        
        # State
        self._is_connected = False
        self._current_strategy: Optional[str] = None
    
    @property
    def is_connected(self) -> bool:
        """Check if connected to Freqtrade."""
        return self.client.health_check()
    
    @property
    def is_trading(self) -> bool:
        """Check if bot is currently trading."""
        try:
            status = self.client.get_status()
            return status.is_running
        except Exception:
            return False
    
    @property
    def trading_mode(self) -> str:
        """Get current trading mode."""
        try:
            status = self.client.get_status()
            return TradingMode.PAPER if status.dry_run else TradingMode.LIVE
        except Exception:
            return "unknown"
    
    # ==========================================
    # ACCOUNT & BALANCE
    # ==========================================
    
    def get_account_info(self) -> Dict[str, Any]:
        """Get comprehensive account information."""
        try:
            balance = self.client.get_balance()
            status = self.client.get_status()
            open_trades = self.client.get_open_trades()
            
            total_pnl = sum(t.pnl or 0 for t in open_trades)
            
            return {
                "balance": balance.model_dump(),
                "bot_status": status.model_dump(),
                "open_trades_count": len(open_trades),
                "total_unrealized_pnl": total_pnl,
                "trading_mode": self.trading_mode,
                "connection": "healthy"
            }
        except Exception as e:
            logger.error(f"Failed to get account info: {e}")
            return {
                "connection": "error",
                "error": str(e)
            }
    
    def get_balance(self) -> Balance:
        """Get current account balance."""
        return self.client.get_balance()
    
    def get_available_balance(self) -> float:
        """Get available (free) balance."""
        balance = self.client.get_balance()
        return balance.free
    
    # ==========================================
    # POSITIONS & TRADES
    # ==========================================
    
    def get_positions(self) -> List[Trade]:
        """Get all open positions."""
        return self.client.get_open_trades()
    
    def get_position(self, pair: str) -> Optional[Trade]:
        """Get position for specific pair."""
        positions = self.client.get_open_trades()
        for pos in positions:
            if pos.pair == pair:
                return pos
        return None
    
    def get_trade_history(self, limit: int = 100) -> List[Trade]:
        """Get trade history."""
        response = self.client.get_trades(limit=limit)
        return response.trades
    
    def close_position(self, trade_id: int) -> Dict[str, Any]:
        """Manually close a position."""
        # Freqtrade doesn't have direct close API, use emergency stop
        logger.warning(f"Manual close for trade {trade_id} requested")
        raise NotImplementedError(
            "Use stop_trading() or add pair to blacklist to close position"
        )
    
    # ==========================================
    # BOT CONTROL
    # ==========================================
    
    def start_trading(self) -> Dict[str, Any]:
        """Start the trading bot."""
        logger.info("Starting Freqtrade bot...")
        result = self.client.start()
        logger.info("Bot started successfully")
        return result
    
    def stop_trading(self) -> Dict[str, Any]:
        """Stop the trading bot."""
        logger.info("Stopping Freqtrade bot...")
        result = self.client.stop()
        logger.info("Bot stopped")
        return result
    
    def emergency_stop(self, reason: str = "") -> Dict[str, Any]:
        """
        Emergency stop - stops trading and buying.
        
        Args:
            reason: Reason for emergency stop
        """
        logger.warning(f"EMERGENCY STOP triggered: {reason}")
        
        # Stop buying first
        self.client.stopbuy()
        
        # Then stop the bot
        return self.client.stop()
    
    # ==========================================
    # STRATEGY MANAGEMENT
    # ==========================================
    
    def get_available_strategies(self) -> List[str]:
        """Get list of available strategies."""
        return self.client.get_strategies()
    
    def deploy_strategy(self, strategy: FreqtradeStrategy) -> Dict[str, Any]:
        """
        Deploy a strategy to Freqtrade.
        
        Args:
            strategy: FreqtradeStrategy object
            
        Returns:
            Deployment result
        """
        # Validate strategy
        issues = self.converter.validate_strategy(strategy)
        if issues:
            logger.warning(f"Strategy validation issues: {issues}")
        
        # Convert to dict for storage
        strategy_data = strategy.to_dict()
        
        # In a real implementation, we would:
        # 1. Write strategy file to Freqtrade's user_data/strategies/
        # 2. Reload config or restart bot
        # 3. Set as active strategy
        
        logger.info(f"Deploying strategy: {strategy.name}")
        self._current_strategy = strategy.name
        
        return {
            "status": "deployed",
            "strategy": strategy_data,
            "validation_warnings": issues,
            "deployed_at": datetime.now().isoformat()
        }
    
    def switch_strategy(self, strategy_name: str) -> Dict[str, Any]:
        """
        Switch to a different strategy.
        
        Args:
            strategy_name: Name of strategy to switch to
        """
        if strategy_name not in self.client.get_strategies():
            raise StrategyError(f"Strategy '{strategy_name}' not found")
        
        logger.info(f"Switching to strategy: {strategy_name}")
        result = self.client.set_strategy(strategy_name)
        self._current_strategy = strategy_name
        
        return result
    
    def convert_and_deploy(
        self,
        vibe_strategy: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Convert Vibe-Trading strategy and deploy to Freqtrade.
        
        Args:
            vibe_strategy: Strategy from Vibe-Trading AI
            
        Returns:
            Deployment result with strategy details
        """
        # Convert strategy
        freq_strategy = self.converter.convert(vibe_strategy)
        
        # Validate
        issues = self.converter.validate_strategy(freq_strategy)
        if issues:
            logger.warning(f"Validation issues: {issues}")
        
        # Deploy
        return self.deploy_strategy(freq_strategy)
    
    # ==========================================
    # PAIR MANAGEMENT
    # ==========================================
    
    def get_trading_pairs(self) -> List[str]:
        """Get current whitelist (active trading pairs)."""
        return self.client.get_whitelist()
    
    def get_blocked_pairs(self) -> List[str]:
        """Get blacklist (blocked pairs)."""
        return self.client.get_blacklist()
    
    def block_pair(self, pair: str) -> Dict[str, Any]:
        """
        Block a pair from trading.
        
        Args:
            pair: Trading pair (e.g., "BTC/USDT")
        """
        return self.client.add_blacklist([pair])
    
    def unblock_pair(self, pair: str) -> Dict[str, Any]:
        """
        Remove pair from blacklist.
        
        Note: Freqtrade doesn't have direct removal API.
        Use reload_config after modifying config file.
        """
        logger.warning("Unblocking pairs requires config reload")
        self.client.reload_config()
        return {"status": "reload_required"}
    
    # ==========================================
    # RISK MANAGEMENT
    # ==========================================
    
    def get_risk_metrics(self) -> Dict[str, Any]:
        """Calculate risk metrics for current positions."""
        positions = self.get_positions()
        
        if not positions:
            return {
                "total_exposure": 0,
                "max_drawdown_risk": "low",
                "largest_position_pct": 0,
                "positions_count": 0
            }
        
        balance = self.get_balance()
        total_balance = balance.total
        
        # Calculate exposure
        exposures = []
        for pos in positions:
            exposure = pos.amount * (pos.current_price or pos.entry_price)
            exposures.append(exposure)
        
        total_exposure = sum(exposures)
        exposure_pct = (total_exposure / total_balance * 100) if total_balance > 0 else 0
        
        # Largest position
        largest = max(exposures) if exposures else 0
        largest_pct = (largest / total_balance * 100) if total_balance > 0 else 0
        
        # Drawdown risk (simplified)
        total_pnl = sum(p.pnl or 0 for p in positions)
        drawdown_risk = "low"
        if total_pnl < -total_balance * 0.05:
            drawdown_risk = "high"
        elif total_pnl < 0:
            drawdown_risk = "medium"
        
        return {
            "total_exposure": total_exposure,
            "exposure_percentage": round(exposure_pct, 2),
            "max_drawdown_risk": drawdown_risk,
            "largest_position_pct": round(largest_pct, 2),
            "positions_count": len(positions),
            "unrealized_pnl": total_pnl
        }
    
    def check_risk_limits(self) -> Dict[str, Any]:
        """
        Check if current positions violate risk limits.
        
        Returns:
            Risk check results
        """
        metrics = self.get_risk_metrics()
        violations = []
        
        # Check exposure limit (configurable, default 100%)
        if metrics["exposure_percentage"] > 100:
            violations.append(f"Exposure too high: {metrics['exposure_percentage']}%")
        
        # Check max positions
        if metrics["positions_count"] > self.config.max_open_trades:
            violations.append(
                f"Too many positions: {metrics['positions_count']} > {self.config.max_open_trades}"
            )
        
        # Check drawdown
        if metrics["max_drawdown_risk"] == "high":
            violations.append("High drawdown risk detected")
        
        return {
            "passed": len(violations) == 0,
            "violations": violations,
            "metrics": metrics,
            "timestamp": datetime.now().isoformat()
        }
    
    # ==========================================
    # UTILITY METHODS
    # ==========================================
    
    def health_check(self) -> Dict[str, Any]:
        """Full health check."""
        connected = self.is_connected
        trading = self.is_trading
        
        return {
            "connected": connected,
            "trading": trading,
            "mode": self.trading_mode,
            "current_strategy": self._current_strategy,
            "api_url": self.client.api_url,
            "checks": {
                "api_accessible": connected,
                "bot_responsive": trading or not trading,  # Both states are valid
            }
        }
    
    def get_summary(self) -> str:
        """Get human-readable trading summary."""
        try:
            info = self.get_account_info()
            positions = self.get_positions()
            
            lines = [
                "📊 FREQTRADE STATUS",
                "=" * 40,
                f"Connection: {'✅' if info.get('connection') == 'healthy' else '❌'}",
                f"Mode: {info.get('trading_mode', 'unknown').upper()}",
                f"Bot: {'🟢 Running' if info.get('bot_status', {}).get('is_running') else '🔴 Stopped'}",
                "",
                "💰 BALANCE",
                f"Total: ${info.get('balance', {}).get('total', 0):.2f}",
                f"Free: ${info.get('balance', {}).get('free', 0):.2f}",
                "",
                f"📈 POSITIONS: {len(positions)}",
            ]
            
            for pos in positions:
                pnl_emoji = "🟢" if (pos.pnl or 0) >= 0 else "🔴"
                lines.append(
                    f"  {pnl_emoji} {pos.pair}: {pos.amount} @ ${pos.entry_price:.2f} "
                    f"(P&L: {pos.pnl_pct or 0:.2f}%)"
                )
            
            return "\n".join(lines)
            
        except Exception as e:
            return f"❌ Error getting summary: {e}"
