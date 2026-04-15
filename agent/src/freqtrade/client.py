"""
Freqtrade REST API client.
"""

import httpx
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

from .models import (
    Balance, Trade, TradeResponse, BotStatus,
    Order, OrderStatus, StrategyInfo, TradeStatus
)
from .exceptions import FreqtradeError, ConnectionError, AuthenticationError

logger = logging.getLogger(__name__)


class FreqtradeClient:
    """
    Freqtrade REST API client.
    
    Provides methods to interact with Freqtrade trading bot.
    Requires Freqtrade running with API enabled.
    """
    
    def __init__(
        self,
        api_url: str = "http://localhost:8080",
        api_key: str = "",
        timeout: int = 30
    ):
        """
        Initialize Freqtrade client.
        
        Args:
            api_url: Freqtrade API URL
            api_key: Freqtrade API key (from config.json)
            timeout: Request timeout in seconds
        """
        self.api_url = api_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        
        self._headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        } if api_key else {"Content-Type": "application/json"}
    
    def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make request to Freqtrade API."""
        url = f"{self.api_url}{endpoint}"
        
        try:
            with httpx.Client(timeout=self.timeout) as client:
                if method.upper() == "GET":
                    response = client.get(url, headers=self._headers)
                elif method.upper() == "POST":
                    response = client.post(url, headers=self._headers, json=data)
                elif method.upper() == "DELETE":
                    response = client.delete(url, headers=self._headers)
                else:
                    raise ValueError(f"Unsupported method: {method}")
                
                if response.status_code == 401:
                    raise AuthenticationError("Invalid API key")
                elif response.status_code >= 400:
                    raise FreqtradeError(
                        f"API error {response.status_code}: {response.text}"
                    )
                
                return response.json()
                
        except httpx.ConnectError as e:
            raise ConnectionError(f"Cannot connect to Freqtrade at {url}: {e}")
        except httpx.TimeoutException:
            raise ConnectionError(f"Request timeout after {self.timeout}s")
    
    async def _async_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make async request to Freqtrade API."""
        url = f"{self.api_url}{endpoint}"
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                if method.upper() == "GET":
                    response = await client.get(url, headers=self._headers)
                elif method.upper() == "POST":
                    response = await client.post(url, headers=self._headers, json=data)
                elif method.upper() == "DELETE":
                    response = await client.delete(url, headers=self._headers)
                else:
                    raise ValueError(f"Unsupported method: {method}")
                
                if response.status_code == 401:
                    raise AuthenticationError("Invalid API key")
                elif response.status_code >= 400:
                    raise FreqtradeError(
                        f"API error {response.status_code}: {response.text}"
                    )
                
                return response.json()
                
        except httpx.ConnectError as e:
            raise ConnectionError(f"Cannot connect to Freqtrade at {url}: {e}")
        except httpx.TimeoutException:
            raise ConnectionError(f"Request timeout after {self.timeout}s")
    
    def get_balance(self) -> Balance:
        """Get account balance."""
        data = self._request("GET", "/api/v1/balance")
        
        # Parse balance from Freqtrade response
        currency = list(data.get("currencies", {}).keys())[0] if data.get("currencies") else "USDT"
        curr_data = data.get("currencies", {}).get(currency, {})
        
        return Balance(
            total=data.get("total", 0),
            free=data.get("free", 0),
            used=data.get("used", 0),
            currency=currency
        )
    
    def get_balance_async(self) -> Dict[str, Any]:
        """Get account balance (async version returning raw dict)."""
        return self._request("GET", "/api/v1/balance")
    
    def get_open_trades(self) -> List[Trade]:
        """Get open trades/positions."""
        data = self._request("GET", "/api/v1/status")
        
        trades = []
        for t in data:
            trades.append(Trade(
                trade_id=t.get("trade_id", 0),
                pair=t.get("pair", ""),
                side="long" if t.get("is_short", False) else "long",
                amount=t.get("amount", 0),
                entry_price=t.get("open_rate", 0),
                current_price=t.get("current_rate"),
                pnl=t.get("profit_abs"),
                pnl_pct=t.get("profit_ratio", 0) * 100 if t.get("profit_ratio") else None,
                status=TradeStatus.OPEN,
                open_date=datetime.fromisoformat(t.get("open_date", "").replace("Z", "+00:00"))
            ))
        
        return trades
    
    def get_trades(
        self,
        limit: int = 100,
        offset: int = 0
    ) -> TradeResponse:
        """Get trade history."""
        data = self._request(
            "GET",
            f"/api/v1/trades?limit={limit}&offset={offset}"
        )
        
        trades = []
        for t in data.get("trades", []):
            trades.append(Trade(
                trade_id=t.get("id", 0),
                pair=t.get("pair", ""),
                side="long" if t.get("is_short", False) else "long",
                amount=t.get("amount", 0),
                entry_price=t.get("open_rate", 0),
                close_price=t.get("close_rate"),
                pnl=t.get("profit_abs"),
                pnl_pct=t.get("profit_ratio", 0) * 100 if t.get("profit_ratio") else None,
                status=TradeStatus.CLOSED if t.get("close_date") else TradeStatus.OPEN,
                open_date=datetime.fromisoformat(t.get("open_date", "").replace("Z", "+00:00")),
                close_date=datetime.fromisoformat(t.get("close_date", "").replace("Z", "+00:00")) if t.get("close_date") else None,
                fee=t.get("fee_open", 0)
            ))
        
        return TradeResponse(
            trades=trades,
            trades_count=len(trades),
            total_trades=data.get("trades_count", len(trades))
        )
    
    def get_status(self) -> BotStatus:
        """Get bot status."""
        data = self._request("GET", "/api/v1/show_config")
        
        return BotStatus(
            is_running=data.get("bot_control", {}).get("is_running", False),
            mode=data.get("dry_run", True) and "dry_run" or "live",
            strategy=data.get("strategy", "Unknown"),
            dry_run=data.get("dry_run", True),
            pairlist=data.get("pairlists", []),
            stake_currency=data.get("stake_currency", "USDT"),
            stake_amount=data.get("tradable_balance"),
            open_trades=0,
            max_open_trades=data.get("max_open_trades", 1)
        )
    
    def start(self) -> Dict[str, Any]:
        """Start the bot."""
        return self._request("POST", "/api/v1/start")
    
    def stop(self) -> Dict[str, Any]:
        """Stop the bot."""
        return self._request("POST", "/api/v1/stop")
    
    def stopbuy(self) -> Dict[str, Any]:
        """Stop buying (but continue holding positions)."""
        return self._request("POST", "/api/v1/stopbuy")
    
    def reload_config(self) -> Dict[str, Any]:
        """Reload configuration."""
        return self._request("POST", "/api/v1/reload_config")
    
    def get_strategies(self) -> List[str]:
        """Get available strategies."""
        data = self._request("GET", "/api/v1/strategies")
        return data.get("strategies", [])
    
    def set_strategy(self, strategy_name: str) -> Dict[str, Any]:
        """Change active strategy."""
        return self._request("POST", f"/api/v1/strategy/{strategy_name}")
    
    def get_whitelist(self) -> List[str]:
        """Get current pair whitelist."""
        data = self._request("GET", "/api/v1/whitelist")
        return data.get("whitelist", [])
    
    def get_blacklist(self) -> List[str]:
        """Get current pair blacklist."""
        data = self._request("GET", "/api/v1/blacklist")
        return data.get("blacklist", [])
    
    def add_blacklist(self, pairs: List[str]) -> Dict[str, Any]:
        """Add pairs to blacklist."""
        return self._request("POST", "/api/v1/blacklist", data={"blacklist": pairs})
    
    def health_check(self) -> bool:
        """Check if Freqtrade is accessible."""
        try:
            self._request("GET", "/api/v1/show_config")
            return True
        except Exception as e:
            logger.warning(f"Health check failed: {e}")
            return False
