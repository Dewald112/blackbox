# metrics.py
# Metrics calculations and dashboard printing

class Metrics:
    def __init__(self):
        self.stats = {}

    def update(self, strategy_name, trade_result):
        if strategy_name not in self.stats:
            self.stats[strategy_name] = {
                'trades': 0,
                'wins': 0,
                'total_pnl': 0,
                'max_drawdown': 0,
                'equity': 1000,
                'equity_curve': []
            }
        s = self.stats[strategy_name]
        s['trades'] += 1
        if trade_result['win']:
            s['wins'] += 1
        s['total_pnl'] += trade_result['pnl']
        s['equity'] += trade_result['pnl']
        s['equity_curve'].append(s['equity'])
        # Calculate max drawdown
        peak = max(s['equity_curve']) if s['equity_curve'] else s['equity']
        dd = peak - s['equity']
        if dd > s['max_drawdown']:
            s['max_drawdown'] = dd

    def print_dashboard(self):
        print("\n--- COACH MODE (Main Dashboard) ---")
        # Find best performing strategy
        best = None
        best_equity = -float('inf')
        for name, s in self.stats.items():
            if s['equity'] > best_equity:
                best = name
                best_equity = s['equity']
        if best:
            s = self.stats[best]
            win_pct = (s['wins'] / s['trades'] * 100) if s['trades'] else 0
            avg_pnl = (s['total_pnl'] / s['trades']) if s['trades'] else 0
            print(f"Current Signal: {best}")
            print(f"Win % (past {s['trades']} trades): {win_pct:.1f}%")
            print(f"Avg P/L: ${avg_pnl:.2f}/trade")
            print(f"Max Drawdown: -${s['max_drawdown']:.2f}")
            print(f"Equity: ${s['equity']:.2f}")
        print("\n--- SANDBOX / STRATEGY LAB ---")
        print(f"{'Strategy':<15}{'Win %':<8}{'Avg P/L':<10}{'Max DD':<10}{'Equity':<10}")
        for name, s in self.stats.items():
            win_pct = (s['wins'] / s['trades'] * 100) if s['trades'] else 0
            avg_pnl = (s['total_pnl'] / s['trades']) if s['trades'] else 0
            print(f"{name:<15}{win_pct:<8.1f}{avg_pnl:<10.2f}{-s['max_drawdown']:<10.2f}{s['equity']:<10.2f}")
