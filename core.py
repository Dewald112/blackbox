# core.py
# Main simulation loop and data feed


from collections import deque
import time
import requests
from strategies.trend_follow import TrendFollowStrategy
from strategies.mean_revert import MeanRevertStrategy
from strategies.breakout import BreakoutStrategy
from metrics import Metrics

ROLLING_WINDOW = 100
rolling_history = deque(maxlen=ROLLING_WINDOW)

strategies = [
    TrendFollowStrategy(),
    MeanRevertStrategy(),
    BreakoutStrategy()
]

metrics = Metrics()


# Alpha Vantage live price fetcher
API_KEY = 'YOUR_API_KEY_HERE'  # Replace with your Alpha Vantage API key
SYMBOL = 'EURUSD'

def get_live_price():
    url = f'https://www.alphavantage.co/query?function=CURRENCY_EXCHANGE_RATE&from_currency=EUR&to_currency=USD&apikey={API_KEY}'
    try:
        response = requests.get(url)
        data = response.json()
        price = float(data['Realtime Currency Exchange Rate']['5. Exchange Rate'])
        return price
    except Exception as e:
        print('Error fetching live price:', e)
        return None

def main():
    while True:
        price = get_live_price()
        if price is None:
            print('Waiting for next price...')
            time.sleep(10)
            continue
        rolling_history.append(price)
        for strategy in strategies:
            signal = strategy.check_signal(rolling_history)
            trade_result = strategy.simulate_trade(signal, price)
            metrics.update(strategy.name, trade_result)
        metrics.print_dashboard()
        time.sleep(60)  # Fetch new price every minute

if __name__ == "__main__":
    main()
