# trend_follow.py
from .base import BaseStrategy

class TrendFollowStrategy(BaseStrategy):
    def __init__(self):
        super().__init__('Trend-Follow')

    def check_signal(self, history):
        # Simple moving average crossover
        if len(history) < 20:
            return None
        short_ma = sum(list(history)[-5:]) / 5
        long_ma = sum(list(history)[-20:]) / 20
        if short_ma > long_ma:
            return 'buy'
        elif short_ma < long_ma:
            return 'sell'
        return None

    def simulate_trade(self, signal, price):
        # Placeholder: simulate fixed P/L
        if signal == 'buy':
            return {'pnl': 10, 'win': True}
        elif signal == 'sell':
            return {'pnl': -5, 'win': False}
        return {'pnl': 0, 'win': None}
