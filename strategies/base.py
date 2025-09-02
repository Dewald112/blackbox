# base.py
# Base strategy class

class BaseStrategy:
    def __init__(self, name):
        self.name = name

    def check_signal(self, history):
        # Should return 'buy', 'sell', or None
        raise NotImplementedError

    def simulate_trade(self, signal, price):
        # Should return trade result dict
        raise NotImplementedError
