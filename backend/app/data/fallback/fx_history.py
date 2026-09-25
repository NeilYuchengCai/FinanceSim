"""
FinanceSim FX Fallback Data
外汇市场历史数据，用于离线初始化
"""
import json
from datetime import datetime, timedelta
from typing import Dict, List

# 确定性种子用于生成可重现的历史数据
_SEED = 42

def _generate_fx_history() -> Dict[str, List[Dict]]:
    """
    生成主要货币对的30天历史价格数据
    使用简化随机游走模拟合理价格波动
    """
    import random
    random.seed(_SEED)

    # 初始价格配置 (基于2024年初市场价)
    initial_prices = {
        "EUR/USD": {"base": "EUR", "quote": "USD", "price": 1.0850, "volatility": 0.0005},
        "GBP/USD": {"base": "GBP", "quote": "USD", "price": 1.2650, "volatility": 0.0006},
        "USD/JPY": {"base": "USD", "quote": "JPY", "price": 148.50, "volatility": 0.0008},
        "USD/CHF": {"base": "USD", "quote": "CHF", "price": 0.8850, "volatility": 0.0005},
        "AUD/USD": {"base": "AUD", "quote": "USD", "price": 0.6550, "volatility": 0.0007},
        "USD/CAD": {"base": "USD", "quote": "CAD", "price": 1.3550, "volatility": 0.0005},
        "NZD/USD": {"base": "NZD", "quote": "USD", "price": 0.6150, "volatility": 0.0007},
        "USD/CNY": {"base": "USD", "quote": "CNY", "price": 7.1500, "volatility": 0.0003},
    }

    # 生成30个交易日，每天8个时间点 (9:00-16:00)
    base_date = datetime(2024, 1, 2)  # 从1月2日开始
    history: Dict[str, List[Dict]] = {}

    for ticker, config in initial_prices.items():
        prices: List[Dict] = []
        current_price = config["price"]
        vol = config["volatility"]

        for day in range(30):
            # 跳过周末
            if base_date.weekday() >= 5:
                base_date += timedelta(days=1)
                continue

            # 每天生成8个价格点
            for hour in range(9, 17):
                timestamp = base_date.replace(hour=hour, minute=0, second=0)

                # 随机游走
                change = random.gauss(0, vol)
                current_price = max(0.001, current_price * (1 + change))

                # 计算OHLC
                high = current_price * (1 + abs(random.gauss(0, vol * 0.5)))
                low = current_price * (1 - abs(random.gauss(0, vol * 0.5)))
                open_price = prices[-1]["close"] if prices else current_price * 0.999

                prices.append({
                    "timestamp": timestamp.isoformat() + "Z",
                    "open": round(open_price, 5 if current_price > 10 else 4),
                    "high": round(high, 5 if current_price > 10 else 4),
                    "low": round(low, 5 if current_price > 10 else 4),
                    "close": round(current_price, 5 if current_price > 10 else 4),
                    "volume": random.randint(1000, 10000)
                })

            base_date += timedelta(days=1)

        history[ticker] = prices

    return history


# 生成并存储历史数据
FX_HISTORY_DATA = _generate_fx_history()

# 导出为JSON供加载使用
def get_fx_fallback_data() -> Dict:
    """返回完整的外汇fallback数据"""
    return {
        "metadata": {
            "source": "fallback",
            "data_type": "historical",
            "generated_at": datetime.now().isoformat(),
            "coverage_days": 30,
            "pairs": list(FX_HISTORY_DATA.keys())
        },
        "pairs": FX_HISTORY_DATA
    }


def get_pair_history(ticker: str, limit: int = 100) -> List[Dict]:
    """获取指定货币对的历史价格"""
    ticker = ticker.upper()
    history = FX_HISTORY_DATA.get(ticker, [])
    return history[-limit:] if history else []


if __name__ == "__main__":
    # 测试数据生成
    data = get_fx_fallback_data()
    print(f"Generated history for {len(data['pairs'])} pairs")
    for pair, hist in data['pairs'].items():
        print(f"  {pair}: {len(hist)} data points, last price: {hist[-1]['close']}")
