"""
FinanceSim 测试套件
"""
import pytest
import sys
import os
# Add backend directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from decimal import Decimal


class TestMarketRegime:
    """市场状态机测试"""
    
    def test_initial_state(self):
        from app.engines.market_engine import MarketRegime
        regime = MarketRegime()
        assert regime.current_state == "CALM"
    
    def test_volatility_multiplier(self):
        from app.engines.market_engine import MarketRegime
        regime = MarketRegime()
        assert regime.get_volatility_multiplier() == 0.8  # CALM state
    
    def test_trend_bias(self):
        from app.engines.market_engine import MarketRegime
        regime = MarketRegime()
        assert regime.get_trend_bias() == 0.0  # CALM state has no bias


class TestOrderBook:
    """订单簿测试"""
    
    def test_add_order(self):
        from app.engines.matching_engine import OrderBook, Order
        
        book = OrderBook("AAPL")
        order = Order(
            order_id="test-1",
            ticker="AAPL",
            side="BUY",
            order_type="LIMIT",
            quantity=Decimal("100"),
            price=Decimal("180.00")
        )
        
        trades = book.add_order(order)
        assert len(trades) == 0  # No matching sell order
    
    def test_market_order_match(self):
        from app.engines.matching_engine import OrderBook, Order
        from decimal import Decimal

        book = OrderBook("AAPL")

        # 先添加限价卖单（有明确价格，可被市价买单成交）
        sell_order = Order(
            order_id="sell-1",
            ticker="AAPL",
            side="SELL",
            order_type="LIMIT",
            quantity=Decimal("100"),
            price=Decimal("185.00")
        )
        book.add_order(sell_order)

        # 添加市价买单（应成交）
        buy_order = Order(
            order_id="buy-1",
            ticker="AAPL",
            side="BUY",
            order_type="MARKET",
            quantity=Decimal("50")
        )

        trades = book.add_order(buy_order)
        assert len(trades) == 1
        assert trades[0]["quantity"] == 50.0
        assert trades[0]["price"] == 185.0


class TestPortfolio:
    """投资组合测试"""
    
    def test_buy(self):
        from app.engines.portfolio_engine import PortfolioEngine
        
        portfolio = PortfolioEngine(world_id=1, initial_cash=Decimal("100000"))
        trade = portfolio.buy("AAPL", 100, 185.0)
        
        assert trade["type"] == "BUY"
        assert trade["quantity"] == 100
        assert portfolio.cash == Decimal("100000") - Decimal("18500")
    
    def test_sell(self):
        from app.engines.portfolio_engine import PortfolioEngine
        
        portfolio = PortfolioEngine(world_id=1, initial_cash=Decimal("100000"))
        portfolio.buy("AAPL", 100, 185.0)
        portfolio.sell("AAPL", 50, 190.0)
        
        # 检查持仓
        pos = portfolio.get_position("AAPL")
        assert pos["quantity"] == 50.0
        assert pos["avg_price"] == 185.0
    
    def test_insufficient_funds(self):
        from app.engines.portfolio_engine import PortfolioEngine
        import pytest
        
        portfolio = PortfolioEngine(world_id=1, initial_cash=Decimal("1000"))
        
        with pytest.raises(ValueError):
            portfolio.buy("AAPL", 100, 185.0)


class TestAnalytics:
    """分析引擎测试"""
    
    def test_returns(self):
        from app.engines.analytics_engine import AnalyticsEngine
        
        prices = [100, 105, 102, 108]
        returns = AnalyticsEngine.calculate_returns(prices)
        
        assert len(returns) == 3
        assert abs(returns[0] - 0.05) < 0.0001  # (105-100)/100
    
    def test_volatility(self):
        from app.engines.analytics_engine import AnalyticsEngine
        
        returns = [0.01, -0.01, 0.02, -0.005]
        vol = AnalyticsEngine.volatility(returns)
        assert vol > 0
    
    def test_max_drawdown(self):
        from app.engines.analytics_engine import AnalyticsEngine
        
        equity = [100, 110, 105, 95, 100]
        dd = AnalyticsEngine.max_drawdown(equity)
        
        assert dd["max_dd"] > 0
        assert dd["peak"] == 110
        assert dd["trough"] == 95


class TestSimulationClock:
    """模拟时钟测试"""
    
    def test_pause_play(self):
        from app.engines.simulation_engine import SimulationClock
        from datetime import datetime
        
        clock = SimulationClock(start_time=datetime(2026, 9, 24))
        assert clock.is_paused
        
        clock.start()
        assert not clock.is_paused
        
        clock.pause()
        assert clock.is_paused
    
    def test_step(self):
        from app.engines.simulation_engine import SimulationClock
        from datetime import datetime
        
        clock = SimulationClock(start_time=datetime(2026, 9, 24))
        new_day = clock.step(5)
        
        assert new_day == 5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
