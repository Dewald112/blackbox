# breakout.py
from .base import BaseStrategy

class BreakoutStrategy(BaseStrategy):
    def __init__(self):
        super().__init__('Breakout')

    def check_signal(self, history):
        if len(history) < 10:
            return None
        high = max(list(history)[-10:])
        low = min(list(history)[-10:])
        price = history[-1]
        if price >= high:
            return 'buy'
        elif price <= low:
            return 'sell'
        return None

    def simulate_trade(self, signal, price):
        if signal == 'buy':
            return {'pnl': 15, 'win': True}
        elif signal == 'sell':
            return {'pnl': -7, 'win': False}
        return {'pnl': 0, 'win': None}
