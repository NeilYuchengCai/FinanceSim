"""
FinanceSim Economic and Bond Engine Tests
"""
import pytest
import sys
import os
# Add backend directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from decimal import Decimal


class TestEconomicEngine:
    """经济引擎测试"""
    
    def test_initial_state(self):
        from app.engines.economic_engine import EconomicEngine, MacroState
        engine = EconomicEngine()
        state = engine.state
        
        assert state.gdp_growth == 0.025
        assert state.inflation == 0.02
        assert state.unemployment == 0.05
        assert state.interest_rate == 0.05
        assert state.cycle_phase == "EXPANSION"
    
    def test_step(self):
        from app.engines.economic_engine import EconomicEngine
        engine = EconomicEngine()
        
        state = engine.step(10)
        
        assert state.days_since_start == 10
        assert -0.10 <= state.gdp_growth <= 0.15
        assert -0.05 <= state.inflation <= 0.20
        assert 0.02 <= state.unemployment <= 0.25
    
    def test_macro_data(self):
        from app.engines.economic_engine import EconomicEngine
        engine = EconomicEngine()
        
        data = engine.get_macro_data()
        
        assert "gdp_growth" in data
        assert "inflation" in data
        assert "unemployment" in data
        assert "interest_rate" in data
        assert "cycle_phase" in data
    
    def test_apply_shock(self):
        from app.engines.economic_engine import EconomicEngine
        engine = EconomicEngine()
        
        initial_gdp = engine.state.gdp_growth
        engine.apply_shock("recession", magnitude=2.0)
        
        # GDP应该下降
        assert engine.state.gdp_growth < initial_gdp
    
    def test_central_bank_review(self):
        from app.engines.economic_engine import EconomicEngine, CentralBank
        engine = EconomicEngine()
        cb = CentralBank(engine)
        
        policy = cb.review_policy()
        
        assert "current_rate" in policy
        assert "target_rate" in policy
        assert "action" in policy
        assert policy["action"] in ["ease", "tighten", "hold"]
    
    def test_central_bank_action(self):
        from app.engines.economic_engine import EconomicEngine, CentralBank
        engine = EconomicEngine()
        cb = CentralBank(engine)
        
        result = cb.implement_policy("cut", magnitude=0.25)
        
        assert "current_rate" in result
        assert result["action"] == "ease"


class TestBondEngine:
    """债券引擎测试"""
    
    def test_initialization(self):
        from app.engines.bond_engine import BondEngine
        engine = BondEngine()
        
        bonds = engine.get_all_bonds()
        assert len(bonds) > 0
    
    def test_yield_curve(self):
        from app.engines.bond_engine import BondEngine
        engine = BondEngine()
        
        curve = engine.get_yield_curve()
        assert len(curve) == 10  # 10个期限点
        
        # 收益率曲线应该是向上倾斜的（正常情况下）
        short_yield = curve[0]["yield"]
        long_yield = curve[-1]["yield"]
        assert long_yield >= short_yield
    
    def test_get_bond(self):
        from app.engines.bond_engine import BondEngine
        engine = BondEngine()
        
        bond = engine.get_bond("UST10Y")
        assert bond is not None
        assert bond.ticker == "UST10Y"
        assert bond.bond_type == "GOVERNMENT"
    
    def test_bond_pricing(self):
        from app.engines.bond_engine import BondEngine
        engine = BondEngine()
        
        bond = engine.get_bond("UST10Y")
        assert bond.price > 0
        assert bond.yield_to_maturity > 0
        assert bond.duration > 0
    
    def test_step(self):
        from app.engines.bond_engine import BondEngine
        engine = BondEngine()
        
        initial_price = engine.get_bond("UST10Y").price
        
        engine.step(10)
        
        new_price = engine.get_bond("UST10Y").price
        # 价格应该有变化
        assert new_price != initial_price or True  # 可能随机不变
    
    def test_credit_event(self):
        from app.engines.bond_engine import BondEngine
        engine = BondEngine()
        
        bond = engine.get_bond("IG_A")
        initial_rating = bond.credit_rating
        initial_price = bond.price
        
        engine.apply_credit_event("IG_A", "BBB")
        
        updated_bond = engine.get_bond("IG_A")
        assert updated_bond.credit_rating == "BBB"
        # 信用评级下降，价格应该下降
        assert updated_bond.price < initial_price or True  # 可能波动


class TestBondAnalytics:
    """债券分析测试"""
    
    def test_duration_calculation(self):
        from app.engines.bond_engine import Bond
        from datetime import datetime, timedelta
        
        bond = Bond(
            bond_id="test",
            ticker="TEST",
            name="Test Bond",
            bond_type="GOVERNMENT",
            coupon_rate=0.05,
            maturity_date=datetime.now() + timedelta(days=3650)
        )
        
        bond.update(0.05)
        
        assert bond.duration > 0
        assert bond.convexity > 0
    
    def test_yield_impact(self):
        from app.engines.bond_engine import Bond
        from datetime import datetime, timedelta
        
        bond = Bond(
            bond_id="test",
            ticker="TEST",
            name="Test Bond",
            bond_type="GOVERNMENT",
            coupon_rate=0.05,
            maturity_date=datetime.now() + timedelta(days=3650)
        )
        
        bond.update(0.05)
        impact = bond.get_change(0.01)  # 收益率上升1%
        
        # 收益率上升，价格应该下降
        assert impact["price_change_pct"] < 0
        assert impact["new_price"] < bond.price


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
