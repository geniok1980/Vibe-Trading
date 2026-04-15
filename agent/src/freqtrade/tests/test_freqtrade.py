"""
Tests for Freqtrade integration.
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime

from agent.src.freqtrade import (
    FreqtradeClient,
    FreqtradeAdapter,
    StrategyConverter,
    FreqtradeStrategy,
    FreqtradeError,
    ConnectionError,
    StrategyError
)
from agent.src.freqtrade.models import Balance, TradeStatus


class TestStrategyConverter:
    """Tests for StrategyConverter."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.converter = StrategyConverter()
    
    def test_convert_basic_strategy(self):
        """Test basic strategy conversion."""
        vibe_strategy = {
            "name": "RSI Strategy",
            "description": "Simple RSI-based strategy",
            "timeframe": "1h",
            "indicators": [
                {"name": "rsi", "formula": "RSI > 70", "buy_signal": False, "sell_signal": True},
                {"name": "rsi", "formula": "RSI < 30", "buy_signal": True, "sell_signal": False}
            ],
            "risk_management": {
                "max_loss": -0.05,
                "trailing_stop": True
            }
        }
        
        result = self.converter.convert(vibe_strategy)
        
        assert result.name == "RSI_Strategy"
        assert result.timeframe == "1h"
        assert result.stoploss == -0.05
        assert result.trailing_stop == True
    
    def test_sanitize_name(self):
        """Test strategy name sanitization."""
        assert self.converter._sanitize_name("My Strategy") == "My_Strategy"
        assert self.converter._sanitize_name("Strategy-2024") == "Strategy_2024"
        assert self.converter._sanitize_name("123Strategy") == "Vibe_123Strategy"
    
    def test_convert_formula(self):
        """Test formula conversion."""
        assert "ta.RSI" in self.converter._convert_formula("RSI > 70")
        assert "ta.EMA" in self.converter._convert_formula("EMA(20)")
        assert "ta.SMA" in self.converter._convert_formula("SMA 50")
    
    def test_validate_strategy(self):
        """Test strategy validation."""
        valid_strategy = FreqtradeStrategy(
            name="TestStrategy",
            stoploss=-0.10,
            trailing_stop=True,
            minimal_roi={"0": 0.05}
        )
        
        issues = self.converter.validate_strategy(valid_strategy)
        assert len(issues) == 0
        
        # Invalid stoploss
        invalid_strategy = FreqtradeStrategy(
            name="Bad",
            stoploss=0.10  # Should be negative
        )
        
        issues = self.converter.validate_strategy(invalid_strategy)
        assert any("Stoploss" in i for i in issues)


class TestFreqtradeClient:
    """Tests for FreqtradeClient."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.client = FreqtradeClient(
            api_url="http://localhost:8080",
            api_key="test_key"
        )
    
    def test_initialization(self):
        """Test client initialization."""
        assert self.client.api_url == "http://localhost:8080"
        assert self.client.api_key == "test_key"
        assert "Bearer test_key" in self.client._headers["Authorization"]
    
    def test_initialization_no_key(self):
        """Test initialization without API key."""
        client = FreqtradeClient()
        assert client.api_key == ""
        assert "Authorization" not in client._headers


class TestFreqtradeAdapter:
    """Tests for FreqtradeAdapter."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.adapter = FreqtradeAdapter(
            api_url="http://localhost:8080",
            api_key="test_key"
        )
    
    def test_initialization(self):
        """Test adapter initialization."""
        assert isinstance(self.adapter.client, FreqtradeClient)
        assert isinstance(self.adapter.converter, StrategyConverter)
    
    @patch.object(FreqtradeClient, 'health_check')
    def test_is_connected(self, mock_health):
        """Test connection check."""
        mock_health.return_value = True
        assert self.adapter.is_connected == True
        
        mock_health.return_value = False
        assert self.adapter.is_connected == False
    
    def test_convert_and_deploy(self):
        """Test strategy conversion and deployment."""
        vibe_strategy = {
            "name": "Test Strategy",
            "timeframe": "4h",
            "indicators": [
                {"name": "rsi", "formula": "RSI > 50", "buy_signal": True, "sell_signal": True}
            ]
        }
        
        result = self.adapter.convert_and_deploy(vibe_strategy)
        
        assert result["status"] == "deployed"
        assert "Test_Strategy" in result["strategy"]["name"]
    
    def test_emergency_stop(self):
        """Test emergency stop."""
        with patch.object(self.adapter.client, 'stopbuy') as mock_stopbuy:
            with patch.object(self.adapter.client, 'stop') as mock_stop:
                mock_stopbuy.return_value = {"status": "stopbuy_executed"}
                mock_stop.return_value = {"status": "stopped"}
                
                result = self.adapter.emergency_stop("Test emergency")
                
                mock_stopbuy.assert_called_once()
                mock_stop.assert_called_once()


class TestIntegration:
    """Integration tests (require running Freqtrade)."""
    
    @pytest.fixture
    def real_adapter(self):
        """Create adapter for integration testing."""
        return FreqtradeAdapter(
            api_url="http://localhost:8080",
            api_key="test_key"
        )
    
    @pytest.mark.integration
    def test_full_workflow(self, real_adapter):
        """Test complete trading workflow."""
        # This test requires a running Freqtrade instance
        
        # Skip if not connected
        if not real_adapter.is_connected:
            pytest.skip("Freqtrade not running")
        
        # Get status
        status = real_adapter.health_check()
        assert status["connected"] == True
        
        # Get strategies
        strategies = real_adapter.get_available_strategies()
        assert isinstance(strategies, list)
    
    @pytest.mark.integration
    def test_balance_fetch(self, real_adapter):
        """Test balance fetching."""
        if not real_adapter.is_connected:
            pytest.skip("Freqtrade not running")
        
        balance = real_adapter.get_balance()
        assert isinstance(balance.total, (int, float))
        assert isinstance(balance.free, (int, float))


# Run with: pytest agent/src/freqtrade/tests/test_freqtrade.py -v
