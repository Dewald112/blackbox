# mean_revert.py
from .base import BaseStrategy

class MeanRevertStrategy(BaseStrategy):
    def __init__(self):
        super().__init__('Mean-Revert')

    def check_signal(self, history):
        if len(history) < 20:
            return None
        avg = sum(list(history)[-20:]) / 20
        price = history[-1]
        if price < avg * 0.99:
            return 'buy'
        elif price > avg * 1.01:
            return 'sell'
        return None

    def simulate_trade(self, signal, price):
        if signal == 'buy':
            return {'pnl': 8, 'win': True}
        elif signal == 'sell':
            return {'pnl': -4, 'win': False}
        return {'pnl': 0, 'win': None}
