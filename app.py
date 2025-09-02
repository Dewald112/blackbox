import streamlit as st
import requests
import time
from collections import deque

# --- CONFIG ---
DEFAULT_API_KEY = "866d83aa328846aea043e4c7cda95dc0"
ROLLING_WINDOW = 100
CURRENCY_PAIRS = ['EUR/USD', 'USD/ZAR', 'EUR/ZAR']
STRATEGY_NAMES = ['Trend-Follow', 'Mean-Revert', 'Breakout']

# --- SESSION STATE INIT ---
if 'stats' not in st.session_state:
    st.session_state['stats'] = {name: {'trades': 0, 'wins': 0, 'total_pnl': 0, 'max_drawdown': 0, 'equity': 1000, 'equity_curve': []} for name in STRATEGY_NAMES}
if 'history' not in st.session_state:
    st.session_state['history'] = []
if 'rolling_history' not in st.session_state:
    st.session_state['rolling_history'] = deque(maxlen=ROLLING_WINDOW)
if 'last_signal' not in st.session_state:
    st.session_state['last_signal'] = None
if 'last_trade' not in st.session_state:
    st.session_state['last_trade'] = None
if 'usd_zar' not in st.session_state:
    st.session_state['usd_zar'] = 18.0
if 'last_price_usd' not in st.session_state:
    st.session_state['last_price_usd'] = 1.0
if 'last_price_zar' not in st.session_state:
    st.session_state['last_price_zar'] = 18.0

# --- STRATEGY CLASSES ---
class BaseStrategy:
    def __init__(self, name):
        self.name = name
    def check_signal(self, history):
        raise NotImplementedError
    def simulate_trade(self, signal, price):
        raise NotImplementedError

class TrendFollowStrategy(BaseStrategy):
    def __init__(self):
        super().__init__('Trend-Follow')
    def check_signal(self, history):
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
        if signal == 'buy':
            return {'pnl': 10, 'win': True, 'entry': price, 'stop': price-0.002, 'target': price+0.004}
        elif signal == 'sell':
            return {'pnl': -5, 'win': False, 'entry': price, 'stop': price+0.002, 'target': price-0.004}
        return {'pnl': 0, 'win': None, 'entry': None, 'stop': None, 'target': None}

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
            return {'pnl': 8, 'win': True, 'entry': price, 'stop': price-0.0015, 'target': price+0.003}
        elif signal == 'sell':
            return {'pnl': -4, 'win': False, 'entry': price, 'stop': price+0.0015, 'target': price-0.003}
        return {'pnl': 0, 'win': None, 'entry': None, 'stop': None, 'target': None}

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
            return {'pnl': 15, 'win': True, 'entry': price, 'stop': price-0.003, 'target': price+0.006}
        elif signal == 'sell':
            return {'pnl': -7, 'win': False, 'entry': price, 'stop': price+0.003, 'target': price-0.006}
        return {'pnl': 0, 'win': None, 'entry': None, 'stop': None, 'target': None}

# --- METRICS ---
def update_metrics(stats, strategy_name, trade_result):
    s = stats[strategy_name]
    s['trades'] += 1
    if trade_result['win']:
        s['wins'] += 1
    s['total_pnl'] += trade_result['pnl']
    s['equity'] += trade_result['pnl']
    s['equity_curve'].append(s['equity'])
    peak = max(s['equity_curve']) if s['equity_curve'] else s['equity']
    dd = peak - s['equity']
    if dd > s['max_drawdown']:
        s['max_drawdown'] = dd

# --- LIVE PRICE FETCH ---
def get_live_price(api_key):
    url_eur_usd = f'https://api.twelvedata.com/price?symbol=EUR/USD&apikey={api_key}'
    url_usd_zar = f'https://api.twelvedata.com/price?symbol=USD/ZAR&apikey={api_key}'
    try:
        resp_eur_usd = requests.get(url_eur_usd)
        data_eur_usd = resp_eur_usd.json()
        resp_usd_zar = requests.get(url_usd_zar)
        data_usd_zar = resp_usd_zar.json()
        price_eur_usd = float(data_eur_usd['price']) if 'price' in data_eur_usd else None
        price_usd_zar = float(data_usd_zar['price']) if 'price' in data_usd_zar else None
        if price_eur_usd is None or price_usd_zar is None:
            st.error(f"API error. EUR/USD response: {data_eur_usd}\nUSD/ZAR response: {data_usd_zar}")
            return None, None, None
        price_eur_zar = price_eur_usd * price_usd_zar
        return price_eur_usd, price_usd_zar, price_eur_zar
    except Exception as e:
        st.error(f"Exception fetching prices: {e}")
        return None, None, None

# --- UI LAYOUT ---
st.set_page_config(page_title="FX Trading App", layout="wide")
st.markdown("<style>.fixed-top {position:fixed;top:0;left:0;width:100%;background:#fff;z-index:1000;padding:8px 0;border-bottom:1px solid #eee;}</style>", unsafe_allow_html=True)
st.markdown('<div class="fixed-top">', unsafe_allow_html=True)
api_key = st.text_input("Enter your Twelve Data API Key:", value=st.session_state.get('api_key', DEFAULT_API_KEY), key="api_key_top_unique")
st.markdown('</div>', unsafe_allow_html=True)
if api_key and api_key != st.session_state.get('api_key', DEFAULT_API_KEY):
    st.session_state['api_key'] = api_key

tab_live, tab_lab, tab_blackbox = st.tabs(["Live", "Lab", "BLACKBOX"])

# --- LIVE TAB ---
with tab_live:
    st.markdown("## Live Market")
    col1, col2 = st.columns([1,1])
    with col1:
        currency_pair = st.selectbox("Currency Pair", CURRENCY_PAIRS, key="currency_pair_select")
        st.session_state['currency_pair'] = currency_pair
    with col2:
        strategy = st.selectbox("Strategy", STRATEGY_NAMES, key="strategy_select")
        st.session_state['strategy'] = strategy
    st.markdown(f"### {currency_pair} Live Chart")
    tv_symbol = currency_pair.replace('/', '')
    st.components.v1.html(f"<iframe src='https://s.tradingview.com/widgetembed/?symbol=FX_IDC:{tv_symbol}&interval=1&theme=light' width='100%' height='400' frameborder='0'></iframe>", height=400)
    fetch_btn = st.button("Get Latest Price", key="fetch_btn_live_1")
    auto_refresh = st.checkbox("Auto-Refresh (every 60s)", value=False, key="auto_refresh_live_1")
    if fetch_btn or (auto_refresh and st.session_state.get('last_refresh', 0) + 60 < time.time()):
        price_usd, usd_zar, price_eur_zar = get_live_price(api_key)
        if price_usd is not None:
            run_price = price_usd
            st.session_state['last_price_usd'] = price_usd
            st.session_state['usd_zar'] = usd_zar
            st.session_state['last_price_zar'] = price_eur_zar
            st.success(f"Fetched live price: EUR/USD={price_usd}, USD/ZAR={usd_zar}, EUR/ZAR={price_eur_zar}")
            # Simulate trades for all strategies
            suggestions = []
            for strat in [TrendFollowStrategy(), MeanRevertStrategy(), BreakoutStrategy()]:
                signal = strat.check_signal(st.session_state['rolling_history'])
                trade = strat.simulate_trade(signal, run_price)
                update_metrics(st.session_state['stats'], strat.name, trade)
                if signal:
                    suggestions.append(f"{signal.title()} – USD ({trade['pnl']:+} Profit) (Risk=1%)")
                else:
                    suggestions.append(f"Hold – USD (0 Profit) (Risk=1%)")
            for s in suggestions:
                st.write(s)
        else:
            st.error("Could not fetch prices. Check your API key or try again later.")

# --- LAB TAB ---
with tab_lab:
    st.markdown("## Strategy Lab")
    stats = st.session_state['stats']
    running_totals = [f"{name}: {stat['total_pnl']:+.0f}" for name, stat in stats.items()]
    st.write("Running Totals:", ", ".join(running_totals))
    strat_choice = st.radio("Select Strategy to Test", STRATEGY_NAMES, key="lab_strategy_radio")
    test_btn = st.button("Simulate Trade", key="lab_test_btn")
    history_btn = st.button("Simulate All Trades on History", key="lab_history_btn")
    strategy_obj = next(s for s in [TrendFollowStrategy(), MeanRevertStrategy(), BreakoutStrategy()] if s.name == strat_choice)
    if test_btn:
        signal = strategy_obj.check_signal(st.session_state['rolling_history'])
        trade = strategy_obj.simulate_trade(signal, st.session_state.get('last_price_usd', 1))
        update_metrics(stats, strat_choice, trade)
        st.success(f"Simulated {strat_choice}: {signal if signal else 'Hold'} | PnL: {trade['pnl']}")
    if history_btn:
        # Reset stats for this strategy
        stats[strat_choice] = {'trades': 0, 'wins': 0, 'total_pnl': 0, 'max_drawdown': 0, 'equity': 1000, 'equity_curve': []}
        for price in st.session_state['history']:
            signal = strategy_obj.check_signal(st.session_state['history'])
            trade = strategy_obj.simulate_trade(signal, price)
            update_metrics(stats, strat_choice, trade)
        st.success(f"Simulated {strat_choice} on all history. Total trades: {stats[strat_choice]['trades']}, Total PnL: {stats[strat_choice]['total_pnl']}")
    st.line_chart(stats[strat_choice]['equity_curve'])

# --- BLACKBOX TAB ---
with tab_blackbox:
    st.markdown("## BLACKBOX")
    st.markdown("<div style='background:#222;color:#fff;padding:24px;border-radius:8px;font-size:1.2em;font-weight:bold;'>", unsafe_allow_html=True)
    st.write("Mysterious AI Insight:")
    last_strat = st.session_state.get('strategy', STRATEGY_NAMES[0])
    strategy_obj = next(s for s in [TrendFollowStrategy(), MeanRevertStrategy(), BreakoutStrategy()] if s.name == last_strat)
    signal = strategy_obj.check_signal(st.session_state['rolling_history'])
    if signal == 'buy':
        explanation = "Price crossed above moving average. Momentum detected."
    elif signal == 'sell':
        explanation = "Price dropped below support. Possible reversal."
    else:
        explanation = "No strong signal. Market is neutral."
    st.write(explanation)
    st.markdown("</div>", unsafe_allow_html=True)
import streamlit as st
import requests
import time
from collections import deque

DEFAULT_API_KEY = "fce3291a96424dafa8df299f22e09172"
ROLLING_WINDOW = 100
CURRENCY_PAIRS = ['EUR/USD', 'USD/ZAR', 'EUR/ZAR']
STRATEGY_NAMES = ['Trend-Follow', 'Mean-Revert', 'Breakout']

# --- SESSION STATE INIT ---
if 'stats' not in st.session_state:
    st.session_state['stats'] = {name: {'trades': 0, 'wins': 0, 'total_pnl': 0, 'max_drawdown': 0, 'equity': 1000, 'equity_curve': []} for name in STRATEGY_NAMES}
if 'history' not in st.session_state:
    st.session_state['history'] = []
if 'rolling_history' not in st.session_state:
    st.session_state['rolling_history'] = deque(maxlen=ROLLING_WINDOW)
if 'last_signal' not in st.session_state:
    st.session_state['last_signal'] = None
if 'last_trade' not in st.session_state:
    st.session_state['last_trade'] = None
if 'usd_zar' not in st.session_state:
    st.session_state['usd_zar'] = 18.0
if 'last_price_usd' not in st.session_state:
    st.session_state['last_price_usd'] = 1.0
if 'last_price_zar' not in st.session_state:
    st.session_state['last_price_zar'] = 18.0

# --- STRATEGY CLASSES ---
class BaseStrategy:
    def __init__(self, name):
        self.name = name
    def check_signal(self, history):
        raise NotImplementedError
    def simulate_trade(self, signal, price):
        raise NotImplementedError




tab_live, tab_lab, tab_blackbox = st.tabs(["Live", "Lab", "BLACKBOX"])


import streamlit as st
import requests
import time
from collections import deque

# --- CONFIG ---
API_KEY = 'YOUR_API_KEY_HERE'  # <-- Replace with your Alpha Vantage API key
ROLLING_WINDOW = 100
SYMBOL = 'EURUSD'

# --- STRATEGY CLASSES ---
class BaseStrategy:
    def __init__(self, name):
        self.name = name
    def check_signal(self, history):
        raise NotImplementedError
    def simulate_trade(self, signal, price):
        raise NotImplementedError

class TrendFollowStrategy(BaseStrategy):
    def __init__(self):
        super().__init__('Trend-Follow')
    def check_signal(self, history):
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
        if signal == 'buy':
            return {'pnl': 10, 'win': True}
        elif signal == 'sell':
            return {'pnl': -5, 'win': False}
        return {'pnl': 0, 'win': None}

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

# --- METRICS ---
def update_metrics(stats, strategy_name, trade_result):
    s = stats[strategy_name]
    s['trades'] += 1
    if trade_result['win']:
        s['wins'] += 1
    s['total_pnl'] += trade_result['pnl']
    s['equity'] += trade_result['pnl']
    s['equity_curve'].append(s['equity'])
    peak = max(s['equity_curve']) if s['equity_curve'] else s['equity']
    dd = peak - s['equity']
    if dd > s['max_drawdown']:
        s['max_drawdown'] = dd

# --- LIVE PRICE FETCH ---
def get_live_price(api_key):
    url = f'https://www.alphavantage.co/query?function=CURRENCY_EXCHANGE_RATE&from_currency=EUR&to_currency=USD&apikey={api_key}'
    try:
        response = requests.get(url)
        data = response.json()
        price = float(data['Realtime Currency Exchange Rate']['5. Exchange Rate'])
        return price
    except Exception:
        return None

# --- RUN SIMULATION FUNCTION ---
def run_simulation(price):
    if 'history' not in st.session_state:
        st.session_state['history'] = []
    if 'rolling_history' not in st.session_state:
        st.session_state['rolling_history'] = deque(maxlen=ROLLING_WINDOW)
    if 'stats' not in st.session_state:
        st.session_state['stats'] = {name: {'trades': 0, 'wins': 0, 'total_pnl': 0, 'max_drawdown': 0, 'equity': 1000, 'equity_curve': []} for name in ['Trend-Follow','Mean-Revert','Breakout']}
    strategies = [TrendFollowStrategy(), MeanRevertStrategy(), BreakoutStrategy()]
    st.session_state['history'].append(price)
    st.session_state['rolling_history'].append(price)
    for strategy in strategies:
        signal = strategy.check_signal(st.session_state['rolling_history'])
        trade_result = strategy.simulate_trade(signal, price)
        update_metrics(st.session_state['stats'], strategy.name, trade_result)

# --- STREAMLIT UI ---
st.set_page_config(page_title="FX Trading App", layout="wide")
st.title("FX Trading App")

# --- Fixed API Key Input ---
api_key = st.text_input("Enter your Twelve Data API Key:", value=st.session_state.get('api_key', DEFAULT_API_KEY), key="api_key_top")
if api_key and api_key != st.session_state.get('api_key', DEFAULT_API_KEY):
    st.session_state['api_key'] = api_key

# --- Tabs ---
tab_live, tab_lab, tab_blackbox = st.tabs(["Live", "Lab", "BLACKBOX"])

# --- LIVE TAB ---
with tab_live:
    st.markdown("## Live Market")
    fetch_btn = st.button("Get Latest Price", key="fetch_btn_live")
    auto_refresh = st.checkbox("Auto-Refresh (every 60s)", value=False, key="auto_refresh_live")
    if fetch_btn or (auto_refresh and st.session_state.get('last_refresh', 0) + 60 < time.time()):
        price = get_live_price(api_key)
        if price is not None:
            run_simulation(price)
            st.session_state['last_refresh'] = time.time()
            st.success(f"Fetched live price: {price}")
        else:
            st.error("Could not fetch prices. Check your API key or try again later.")
    stats = st.session_state['stats']
    if stats:
        best = max(stats, key=lambda k: stats[k]['equity'])
        s = stats[best]
        st.metric("Current Signal", best)
        st.metric("Win %", f"{(s['wins']/s['trades']*100) if s['trades'] else 0:.1f}%")
        st.metric("Avg P/L", f"${(s['total_pnl']/s['trades']) if s['trades'] else 0:.2f}")
        st.metric("Max Drawdown", f"-${s['max_drawdown']:.2f}")
        st.metric("Equity", f"${s['equity']:.2f}")
        st.line_chart(s['equity_curve'])

# --- LAB TAB ---
with tab_lab:
    st.markdown("## Strategy Lab")
    st.table([
        {
            "Strategy": name,
            "Win %": f"{(stat['wins']/stat['trades']*100) if stat['trades'] else 0:.1f}",
            "Avg P/L": f"${(stat['total_pnl']/stat['trades']) if stat['trades'] else 0:.2f}",
            "Max DD": f"-${stat['max_drawdown']:.2f}",
            "Equity": f"${stat['equity']:.2f}"
        } for name, stat in stats.items()
    ])

# --- BLACKBOX TAB ---
with tab_blackbox:
    st.markdown("## BLACKBOX")
    st.write("Mysterious AI Insight:")
    # Example explanation logic
    explanation = "No strong signal. Market is neutral."
    st.write(explanation)
import streamlit as st
import requests
import time
from collections import deque

# --- CONFIG ---
API_KEY = 'YOUR_API_KEY_HERE'  # <-- Replace with your Alpha Vantage API key
ROLLING_WINDOW = 100
SYMBOL = 'EURUSD'

# --- STRATEGY CLASSES ---
class BaseStrategy:
    def __init__(self, name):
        self.name = name
    def check_signal(self, history):
        raise NotImplementedError
    def simulate_trade(self, signal, price):
        raise NotImplementedError

class TrendFollowStrategy(BaseStrategy):
    def __init__(self):
        super().__init__('Trend-Follow')
    def check_signal(self, history):
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
        if signal == 'buy':
            return {'pnl': 10, 'win': True}
        elif signal == 'sell':
            return {'pnl': -5, 'win': False}
        return {'pnl': 0, 'win': None}

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

# --- METRICS ---
def update_metrics(stats, strategy_name, trade_result):
    s = stats[strategy_name]
    s['trades'] += 1
    if trade_result['win']:
        s['wins'] += 1
    s['total_pnl'] += trade_result['pnl']
    s['equity'] += trade_result['pnl']
    s['equity_curve'].append(s['equity'])
    peak = max(s['equity_curve']) if s['equity_curve'] else s['equity']
    dd = peak - s['equity']
    if dd > s['max_drawdown']:
        s['max_drawdown'] = dd

# --- LIVE PRICE FETCH ---
def get_live_price(api_key):
    url = f'https://www.alphavantage.co/query?function=CURRENCY_EXCHANGE_RATE&from_currency=EUR&to_currency=USD&apikey={api_key}'
    try:
        response = requests.get(url)
        data = response.json()
        price = float(data['Realtime Currency Exchange Rate']['5. Exchange Rate'])
        return price
    except Exception as e:
        return None

# --- STREAMLIT UI ---
st.set_page_config(page_title="Forex Trading Assistant", layout="wide")
st.title("Forex Trading Assistant")

st.markdown("""
**Instructions:**
1. Enter your Alpha Vantage API key above.
2. Click 'Fetch Live Price' or enable Auto-Refresh.
3. View live strategy stats and charts below.
""")

api_key_input = st.text_input("Alpha Vantage API Key", value=API_KEY)
if api_key_input and api_key_input != API_KEY:
    API_KEY = api_key_input

auto_refresh = st.checkbox("Auto-Refresh every 60 seconds", value=False)
fetch_btn = st.button("Fetch Live Price & Update")

if 'history' not in st.session_state:
    st.session_state['history'] = []
if 'rolling_history' not in st.session_state:
    st.session_state['rolling_history'] = deque(maxlen=ROLLING_WINDOW)
if 'stats' not in st.session_state:
    st.session_state['stats'] = {name: {'trades': 0, 'wins': 0, 'total_pnl': 0, 'max_drawdown': 0, 'equity': 1000, 'equity_curve': []} for name in ['Trend-Follow','Mean-Revert','Breakout']}

strategies = [TrendFollowStrategy(), MeanRevertStrategy(), BreakoutStrategy()]

def run_simulation(price):
    st.session_state['history'].append(price)
    st.session_state['rolling_history'].append(price)
    for strategy in strategies:
        signal = strategy.check_signal(st.session_state['rolling_history'])
        trade_result = strategy.simulate_trade(signal, price)
        update_metrics(st.session_state['stats'], strategy.name, trade_result)

if fetch_btn or (auto_refresh and st.session_state.get('last_refresh', 0) + 60 < time.time()):
    price = get_live_price(API_KEY)
    if price is None:
        st.error('Could not fetch live price. Check your API key or internet connection.')
    else:
        run_simulation(price)
        st.session_state['last_refresh'] = time.time()
        st.success(f'Fetched live price: {price}')

st.subheader("Coach Mode (Main Dashboard)")
stats = st.session_state['stats']
if stats:
    best = max(stats, key=lambda k: stats[k]['equity'])
    s = stats[best]
    st.metric("Current Signal", best)
    st.metric("Win %", f"{(s['wins']/s['trades']*100) if s['trades'] else 0:.1f}%")
    st.metric("Avg P/L", f"${(s['total_pnl']/s['trades']) if s['trades'] else 0:.2f}")
    st.metric("Max Drawdown", f"-${s['max_drawdown']:.2f}")
    st.metric("Equity", f"${s['equity']:.2f}")
    st.line_chart(s['equity_curve'])

st.subheader("Sandbox / Strategy Lab")
st.table([
    {
        "Strategy": name,
        "Win %": f"{(stat['wins']/stat['trades']*100) if stat['trades'] else 0:.1f}",
        "Avg P/L": f"${(stat['total_pnl']/stat['trades']) if stat['trades'] else 0:.2f}",
        "Max DD": f"-${stat['max_drawdown']:.2f}",
        "Equity": f"${stat['equity']:.2f}"
    }
    for name, stat in stats.items()
])