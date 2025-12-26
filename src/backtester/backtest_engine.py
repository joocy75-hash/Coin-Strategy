"""
VectorBT-based Backtesting Engine

Falls back to numpy-based implementation if VectorBT is not available.
"""

from dataclasses import dataclass, asdict
from typing import Dict, Optional
import numpy as np
import pandas as pd
import warnings

try:
    import vectorbt as vbt
    VECTORBT_AVAILABLE = True
except ImportError:
    VECTORBT_AVAILABLE = False
    warnings.warn("VectorBT not installed. Using fallback numpy-based backtesting.")


@dataclass
class BacktestResult:
    """Container for backtest results."""
    total_return: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    total_trades: int
    profit_factor: float
    equity_curve: pd.Series
    avg_trade_return: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    best_trade: float = 0.0
    worst_trade: float = 0.0
    max_consecutive_wins: int = 0
    max_consecutive_losses: int = 0

    def to_dict(self) -> Dict:
        """Convert result to JSON-serializable dictionary."""
        result = asdict(self)
        if isinstance(self.equity_curve, pd.Series):
            result['equity_curve'] = {
                'values': self.equity_curve.tolist(),
                'index': self.equity_curve.index.astype(str).tolist()
            }
        return result


class BacktestEngine:
    """Backtesting engine using VectorBT or numpy fallback."""

    def __init__(
        self,
        initial_capital: float = 10000.0,
        fees: float = 0.001,
        slippage: float = 0.0005,
        use_vectorbt: bool = True
    ):
        self.initial_capital = initial_capital
        self.fees = fees
        self.slippage = slippage
        self.use_vectorbt = use_vectorbt and VECTORBT_AVAILABLE

    def run_backtest(
        self,
        df: pd.DataFrame,
        entries: pd.Series,
        exits: pd.Series,
        direction: str = "long",
        price_column: str = "close"
    ) -> BacktestResult:
        """Run backtest with given entry/exit signals."""
        if direction not in ["long", "short"]:
            raise ValueError(f"Direction must be 'long' or 'short'")

        df = df.copy()
        entries = entries.reindex(df.index, fill_value=False)
        exits = exits.reindex(df.index, fill_value=False)

        if price_column not in df.columns:
            raise ValueError(f"Price column '{price_column}' not found")

        prices = df[price_column]

        if self.use_vectorbt:
            return self._run_vectorbt_backtest(prices, entries, exits, direction)
        else:
            return self._run_numpy_backtest(prices, entries, exits, direction)

    def _run_vectorbt_backtest(self, prices, entries, exits, direction) -> BacktestResult:
        """Run backtest using VectorBT."""
        if direction == "short":
            entries, exits = exits, entries

        portfolio = vbt.Portfolio.from_signals(
            close=prices, entries=entries, exits=exits,
            direction=direction, init_cash=self.initial_capital,
            fees=self.fees, slippage=self.slippage, freq='1D'
        )

        total_return = portfolio.total_return() * 100
        sharpe_ratio = portfolio.sharpe_ratio()
        max_drawdown = portfolio.max_drawdown() * 100

        trades = portfolio.trades.records_readable
        total_trades = len(trades)

        if total_trades > 0:
            win_rate = (trades['PnL'] > 0).sum() / total_trades * 100
            gross_profit = trades[trades['PnL'] > 0]['PnL'].sum()
            gross_loss = abs(trades[trades['PnL'] < 0]['PnL'].sum())
            profit_factor = gross_profit / gross_loss if gross_loss > 0 else np.inf
            avg_trade_return = trades['Return'].mean() * 100
            avg_win = trades[trades['PnL'] > 0]['Return'].mean() * 100 if len(trades[trades['PnL'] > 0]) > 0 else 0
            avg_loss = trades[trades['PnL'] < 0]['Return'].mean() * 100 if len(trades[trades['PnL'] < 0]) > 0 else 0
            best_trade = trades['Return'].max() * 100
            worst_trade = trades['Return'].min() * 100
            win_streak = self._calculate_max_consecutive(trades['PnL'] > 0)
            loss_streak = self._calculate_max_consecutive(trades['PnL'] < 0)
        else:
            win_rate = profit_factor = avg_trade_return = avg_win = avg_loss = 0
            best_trade = worst_trade = 0
            win_streak = loss_streak = 0

        return BacktestResult(
            total_return=total_return, sharpe_ratio=sharpe_ratio, max_drawdown=max_drawdown,
            win_rate=win_rate, total_trades=total_trades, profit_factor=profit_factor,
            equity_curve=portfolio.value(), avg_trade_return=avg_trade_return,
            avg_win=avg_win, avg_loss=avg_loss, best_trade=best_trade, worst_trade=worst_trade,
            max_consecutive_wins=win_streak, max_consecutive_losses=loss_streak
        )

    def _run_numpy_backtest(self, prices, entries, exits, direction) -> BacktestResult:
        """Run backtest using numpy (fallback)."""
        prices_arr = prices.values
        entries_arr = entries.values.astype(bool)
        exits_arr = exits.values.astype(bool)

        position = 0
        equity = np.zeros(len(prices_arr))
        equity[0] = self.initial_capital
        trades = []
        entry_price = entry_idx = 0

        for i in range(len(prices_arr)):
            current_price = prices_arr[i]

            if position == 0 and entries_arr[i]:
                exec_price = current_price * (1 + self.slippage if direction == "long" else 1 - self.slippage)
                entry_price, entry_idx, position = exec_price, i, 1
                equity[i] = (equity[i-1] if i > 0 else self.initial_capital) * (1 - self.fees)

            elif position == 1 and exits_arr[i]:
                exec_price = current_price * (1 - self.slippage if direction == "long" else 1 + self.slippage)
                trade_return = (exec_price - entry_price) / entry_price if direction == "long" else (entry_price - exec_price) / entry_price
                prev_equity = equity[i-1] if i > 0 else self.initial_capital
                equity[i] = prev_equity * (1 + trade_return) * (1 - self.fees)
                trades.append({'entry_price': entry_price, 'exit_price': exec_price, 'return': trade_return, 'pnl': prev_equity * trade_return})
                position = 0
            else:
                equity[i] = equity[i-1] if i > 0 else self.initial_capital

        if position == 1:
            exec_price = prices_arr[-1] * (1 - self.slippage if direction == "long" else 1 + self.slippage)
            trade_return = (exec_price - entry_price) / entry_price if direction == "long" else (entry_price - exec_price) / entry_price
            equity[-1] = equity[-2] * (1 + trade_return) * (1 - self.fees)
            trades.append({'entry_price': entry_price, 'exit_price': exec_price, 'return': trade_return, 'pnl': equity[-2] * trade_return})

        equity_series = pd.Series(equity, index=prices.index)
        total_return = ((equity[-1] - self.initial_capital) / self.initial_capital) * 100

        returns = equity_series.pct_change().dropna()
        sharpe_ratio = (returns.mean() / returns.std() * np.sqrt(252)) if returns.std() > 0 else 0.0

        cummax = equity_series.expanding().max()
        max_drawdown = abs(((equity_series - cummax) / cummax).min()) * 100

        total_trades = len(trades)
        if total_trades > 0:
            trade_pnls = np.array([t['pnl'] for t in trades])
            trade_returns = np.array([t['return'] for t in trades])
            win_rate = (trade_pnls > 0).sum() / total_trades * 100
            profit_factor = trade_pnls[trade_pnls > 0].sum() / abs(trade_pnls[trade_pnls < 0].sum()) if trade_pnls[trade_pnls < 0].sum() != 0 else np.inf
            avg_trade_return = trade_returns.mean() * 100
            avg_win = trade_returns[trade_pnls > 0].mean() * 100 if len(trade_returns[trade_pnls > 0]) > 0 else 0
            avg_loss = trade_returns[trade_pnls < 0].mean() * 100 if len(trade_returns[trade_pnls < 0]) > 0 else 0
            best_trade, worst_trade = trade_returns.max() * 100, trade_returns.min() * 100
            win_streak = self._calculate_max_consecutive(trade_pnls > 0)
            loss_streak = self._calculate_max_consecutive(trade_pnls < 0)
        else:
            win_rate = profit_factor = avg_trade_return = avg_win = avg_loss = 0
            best_trade = worst_trade = 0
            win_streak = loss_streak = 0

        return BacktestResult(
            total_return=total_return, sharpe_ratio=sharpe_ratio, max_drawdown=max_drawdown,
            win_rate=win_rate, total_trades=total_trades, profit_factor=profit_factor,
            equity_curve=equity_series, avg_trade_return=avg_trade_return,
            avg_win=avg_win, avg_loss=avg_loss, best_trade=best_trade, worst_trade=worst_trade,
            max_consecutive_wins=win_streak, max_consecutive_losses=loss_streak
        )

    @staticmethod
    def _calculate_max_consecutive(boolean_series) -> int:
        if len(boolean_series) == 0:
            return 0
        max_streak = current_streak = 0
        for val in boolean_series:
            if val:
                current_streak += 1
                max_streak = max(max_streak, current_streak)
            else:
                current_streak = 0
        return max_streak

    def generate_report(self, result: BacktestResult) -> Dict:
        """Generate a comprehensive report from backtest results."""
        return {
            'performance_metrics': {
                'total_return': f"{result.total_return:.2f}%",
                'sharpe_ratio': f"{result.sharpe_ratio:.2f}",
                'max_drawdown': f"{result.max_drawdown:.2f}%",
                'profit_factor': f"{result.profit_factor:.2f}" if not np.isinf(result.profit_factor) else "∞"
            },
            'trade_statistics': {
                'total_trades': result.total_trades,
                'win_rate': f"{result.win_rate:.2f}%",
                'avg_trade_return': f"{result.avg_trade_return:.2f}%",
                'best_trade': f"{result.best_trade:.2f}%",
                'worst_trade': f"{result.worst_trade:.2f}%"
            },
            'configuration': {
                'initial_capital': self.initial_capital,
                'fees': f"{self.fees * 100:.3f}%",
                'engine': 'VectorBT' if self.use_vectorbt else 'NumPy'
            }
        }


def quick_backtest(
    prices: pd.Series,
    entries: pd.Series,
    exits: pd.Series,
    direction: str = "long",
    initial_capital: float = 10000.0,
    fees: float = 0.001
) -> BacktestResult:
    """Quick backtest function for simple use cases."""
    engine = BacktestEngine(initial_capital=initial_capital, fees=fees)
    df = pd.DataFrame({'close': prices})
    return engine.run_backtest(df, entries, exits, direction)
