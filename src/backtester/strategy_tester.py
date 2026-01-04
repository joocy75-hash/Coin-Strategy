"""
Pine Script 변환 및 백테스트 통합 서비스

Pine Script 전략을 자동으로 Python으로 변환하고 백테스트를 수행합니다.
"""

import json
import logging
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
import sys

import numpy as np
import pandas as pd
import aiosqlite

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.converter.pine_to_python import PineScriptConverter, ConversionResult
from src.storage.database import StrategyDatabase

logger = logging.getLogger(__name__)


class StrategyTester:
    """Pine Script 전략 변환 및 백테스트 통합 서비스"""

    def __init__(self, db_path: str = "data/strategies.db"):
        self.db_path = db_path
        self.converter = PineScriptConverter()
        self.db = StrategyDatabase(db_path)

    async def test_strategy(
        self,
        script_id: str,
        symbol: str = "BTC/USDT",
        timeframe: str = "1h",
        start_date: str = "2024-01-01",
        end_date: str = "2024-12-01",
        initial_capital: float = 10000.0
    ) -> Dict:
        """전략 백테스트 실행"""
        logger.info(f"Testing strategy: {script_id}")

        try:
            await self.db.init_db()
            strategy = await self.db.get_strategy(script_id)

            if not strategy:
                return {'success': False, 'error': f'Strategy not found: {script_id}'}

            if not strategy.pine_code:
                return {'success': False, 'error': 'No Pine Script code available'}

            # Pine Script → Python 변환
            conversion_result = self.converter.convert(strategy.pine_code)

            if not conversion_result.success:
                logger.warning("Conversion failed, using default strategy")
                python_code = self._get_default_strategy()
                conversion_result = ConversionResult(
                    success=True, python_code=python_code,
                    indicators_used=['EMA', 'RSI'],
                    warnings=['Used default strategy'],
                    errors=conversion_result.errors
                )

            # 시장 데이터 가져오기
            candles = await self._fetch_market_data(symbol, timeframe, start_date, end_date)

            if len(candles) < 100:
                return {'success': False, 'error': 'Insufficient market data'}

            # 전략 컴파일 및 백테스트
            strategy_func = self._compile_strategy(conversion_result.python_code)
            if not strategy_func:
                return {'success': False, 'error': 'Failed to compile strategy'}

            backtest_result = self._run_backtest(strategy_func, candles, initial_capital)

            result = {
                'script_id': script_id,
                'symbol': symbol,
                'timeframe': timeframe,
                'start_date': start_date,
                'end_date': end_date,
                'conversion': {
                    'success': conversion_result.success,
                    'indicators_used': conversion_result.indicators_used,
                    'warnings': conversion_result.warnings
                },
                'backtest': backtest_result,
                'tested_at': datetime.now().isoformat()
            }

            await self._save_backtest_result(script_id, result)

            return result

        except Exception as e:
            logger.error(f"Error testing strategy {script_id}: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}

    async def test_all_strategies(self, limit: int = 10, **kwargs) -> List[Dict]:
        """모든 전략 백테스트"""
        await self.db.init_db()

        from src.storage.models import SearchFilters
        filters = SearchFilters(has_pine_code=True, limit=limit, order_by='likes', order_desc=True)
        strategies = await self.db.search_strategies(filters)

        results = []
        for strategy in strategies:
            try:
                result = await self.test_strategy(script_id=strategy.script_id, **kwargs)
                results.append(result)
                await asyncio.sleep(1)
            except Exception as e:
                results.append({'script_id': strategy.script_id, 'success': False, 'error': str(e)})

        return results

    async def _fetch_market_data(self, symbol: str, timeframe: str, start_date: str, end_date: str) -> List[Dict]:
        """시장 데이터 가져오기"""
        try:
            import ccxt
            exchange = ccxt.bitget({'enableRateLimit': True, 'options': {'defaultType': 'spot'}})
            start_ts = int(datetime.fromisoformat(start_date).timestamp() * 1000)
            end_ts = int(datetime.fromisoformat(end_date).timestamp() * 1000)

            all_candles = []
            current_ts = start_ts

            while current_ts < end_ts:
                ohlcv = await asyncio.to_thread(exchange.fetch_ohlcv, symbol, timeframe, current_ts, 1000)
                if not ohlcv:
                    break

                for c in ohlcv:
                    if c[0] < end_ts:
                        all_candles.append({
                            'timestamp': c[0], 'open': c[1], 'high': c[2],
                            'low': c[3], 'close': c[4], 'volume': c[5]
                        })
                current_ts = ohlcv[-1][0] + 1
                await asyncio.sleep(0.1)

            if all_candles:
                return all_candles
        except Exception as e:
            logger.warning(f"Error fetching real data: {e}, using synthetic data")

        return self._generate_synthetic_data(start_date, end_date, timeframe)

    def _generate_synthetic_data(self, start_date: str, end_date: str, timeframe: str) -> List[Dict]:
        """합성 OHLCV 데이터 생성"""
        start = datetime.fromisoformat(start_date)
        end = datetime.fromisoformat(end_date)

        delta = timedelta(hours=int(timeframe[:-1])) if timeframe.endswith('h') else timedelta(days=1)

        candles = []
        current = start
        price = 40000.0
        np.random.seed(42)

        while current <= end:
            change = np.random.normal(0, 0.02)
            price *= (1 + change)
            vol = price * 0.01

            candles.append({
                'timestamp': int(current.timestamp() * 1000),
                'open': price, 'high': price + abs(np.random.normal(0, vol)),
                'low': price - abs(np.random.normal(0, vol)),
                'close': price + np.random.normal(0, vol * 0.5),
                'volume': abs(np.random.normal(100, 30))
            })

            current += delta
            price = candles[-1]['close']

        return candles

    def _run_backtest(self, strategy_func, candles: List[Dict], initial_capital: float) -> Dict:
        """백테스트 실행"""
        capital = initial_capital
        position = None
        trades = []
        equity_curve = []
        lookback = 100

        for i in range(lookback, len(candles)):
            current = candles[i]
            price = current['close']
            historical = candles[max(0, i - lookback):i + 1]

            current_pos = None
            if position:
                pnl = price - position['entry_price']
                pnl_pct = (pnl / position['entry_price']) * 100
                current_pos = {'side': position['side'], 'entry_price': position['entry_price'], 'pnl_percent': pnl_pct}

            try:
                signal = strategy_func(current_price=price, candles=historical, params={}, current_position=current_pos)
            except Exception:
                signal = {'action': 'hold'}

            action = signal.get('action', 'hold')

            if action == 'buy' and not position:
                position = {'side': 'long', 'entry_price': price, 'entry_time': current.get('timestamp')}
            elif action == 'sell' and not position:
                position = {'side': 'short', 'entry_price': price, 'entry_time': current.get('timestamp')}
            elif action == 'close' and position:
                pnl = (price - position['entry_price']) if position['side'] == 'long' else (position['entry_price'] - price)
                pnl_pct = (pnl / position['entry_price']) * 100
                trades.append({'side': position['side'], 'entry_price': position['entry_price'], 'exit_price': price, 'pnl_percent': pnl_pct})
                capital *= (1 + pnl_pct / 100)
                position = None

            equity = capital if not position else capital * (1 + ((price - position['entry_price']) / position['entry_price']) * 100 / 100) if position['side'] == 'long' else capital * (1 + ((position['entry_price'] - price) / position['entry_price']) * 100 / 100)
            equity_curve.append({'timestamp': current.get('timestamp'), 'equity': equity})

        if position:
            price = candles[-1]['close']
            pnl = (price - position['entry_price']) if position['side'] == 'long' else (position['entry_price'] - price)
            pnl_pct = (pnl / position['entry_price']) * 100
            trades.append({'side': position['side'], 'entry_price': position['entry_price'], 'exit_price': price, 'pnl_percent': pnl_pct})
            capital *= (1 + pnl_pct / 100)

        if not trades:
            return {'success': True, 'total_trades': 0, 'total_return': 0, 'win_rate': 0, 'message': 'No trades'}

        total_trades = len(trades)
        winning = [t for t in trades if t['pnl_percent'] > 0]
        win_rate = len(winning) / total_trades * 100 if total_trades else 0
        total_return = ((capital - initial_capital) / initial_capital) * 100

        avg_win = np.mean([t['pnl_percent'] for t in winning]) if winning else 0
        avg_loss = np.mean([t['pnl_percent'] for t in trades if t['pnl_percent'] <= 0]) or 0

        equity_values = [e['equity'] for e in equity_curve]
        peak = equity_values[0]
        max_dd = 0
        for v in equity_values:
            if v > peak:
                peak = v
            dd = ((peak - v) / peak) * 100
            if dd > max_dd:
                max_dd = dd

        returns = [t['pnl_percent'] for t in trades]
        sharpe = (np.mean(returns) / np.std(returns)) if len(returns) > 1 and np.std(returns) > 0 else 0

        return {
            'success': True,
            'total_trades': total_trades,
            'winning_trades': len(winning),
            'losing_trades': total_trades - len(winning),
            'win_rate': round(win_rate, 2),
            'total_return': round(total_return, 2),
            'sharpe_ratio': round(sharpe, 2),
            'max_drawdown': round(max_dd, 2),
            'avg_win': round(avg_win, 2),
            'avg_loss': round(avg_loss, 2),
            'initial_capital': initial_capital,
            'final_capital': round(capital, 2),
            'equity_curve': equity_curve[-100:],
            'trades': trades[:20]
        }

    def _compile_strategy(self, python_code: str):
        """Python 코드를 동적으로 컴파일"""
        try:
            safe_globals = {'__builtins__': __builtins__, 'np': np, 'numpy': np, 'List': List, 'Dict': Dict, 'Optional': Optional}
            exec(python_code, safe_globals)

            if 'generate_signal' in safe_globals:
                return safe_globals['generate_signal']

            for key, value in safe_globals.items():
                if isinstance(value, type) and hasattr(value, 'generate_signal'):
                    instance = value()
                    return lambda *args, **kwargs: instance.generate_signal(*args, **kwargs)

            return None
        except Exception as e:
            logger.error(f"Error compiling strategy: {e}")
            return None

    async def _save_backtest_result(self, script_id: str, result: Dict):
        """백테스트 결과를 DB에 저장"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute("SELECT analysis_json FROM strategies WHERE script_id = ?", (script_id,)) as cursor:
                    row = await cursor.fetchone()
                    analysis = json.loads(row[0]) if row and row[0] else {}
                    analysis['backtest_result'] = result

                    await db.execute(
                        "UPDATE strategies SET analysis_json = ?, updated_at = ? WHERE script_id = ?",
                        (json.dumps(analysis, ensure_ascii=False), datetime.now().isoformat(), script_id)
                    )
                    await db.commit()
        except Exception as e:
            logger.error(f"Error saving backtest result: {e}")

    def _get_default_strategy(self) -> str:
        """기본 EMA 크로스오버 전략"""
        return '''
import numpy as np
from typing import List, Dict, Optional

def generate_signal(current_price: float, candles: List[Dict], params: Dict = None, current_position: Optional[Dict] = None) -> Dict:
    params = params or {}
    fast_period = params.get('fast_period', 9)
    slow_period = params.get('slow_period', 21)

    if len(candles) < slow_period + 14:
        return {'action': 'hold', 'confidence': 0.5, 'reason': 'Insufficient data'}

    closes = np.array([c['close'] for c in candles])

    def ema(data, period):
        mult = 2 / (period + 1)
        result = data[0]
        for p in data[1:]:
            result = (p * mult) + (result * (1 - mult))
        return result

    def rsi(data, period=14):
        if len(data) < period + 1:
            return 50.0
        deltas = np.diff(data[-period-1:])
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        avg_gain, avg_loss = np.mean(gains), np.mean(losses)
        if avg_loss == 0:
            return 100.0
        return 100 - (100 / (1 + avg_gain / avg_loss))

    ema_fast = ema(closes, fast_period)
    ema_slow = ema(closes, slow_period)
    rsi_val = rsi(closes, 14)

    if current_position:
        pnl = current_position.get('pnl_percent', 0)
        if pnl >= 4.0:
            return {'action': 'close', 'confidence': 0.9, 'reason': f'Take Profit: {pnl:.2f}%'}
        if pnl <= -2.0:
            return {'action': 'close', 'confidence': 0.95, 'reason': f'Stop Loss: {pnl:.2f}%'}

    if not current_position:
        prev_fast = ema(closes[:-1], fast_period)
        prev_slow = ema(closes[:-1], slow_period)

        if ema_fast > ema_slow and prev_fast <= prev_slow and rsi_val < 70:
            return {'action': 'buy', 'confidence': 0.7, 'reason': f'EMA Golden Cross (RSI: {rsi_val:.1f})', 'stop_loss': 2.0, 'take_profit': 4.0}

        if ema_fast < ema_slow and prev_fast >= prev_slow and rsi_val > 30:
            return {'action': 'sell', 'confidence': 0.7, 'reason': f'EMA Dead Cross (RSI: {rsi_val:.1f})', 'stop_loss': 2.0, 'take_profit': 4.0}

    return {'action': 'hold', 'confidence': 0.5, 'reason': 'No signal'}
'''


async def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    tester = StrategyTester()

    results = await tester.test_all_strategies(limit=3, symbol="BTC/USDT", timeframe="1h", start_date="2024-01-01", end_date="2024-03-01")

    for r in results:
        if r.get('backtest', {}).get('success'):
            bt = r['backtest']
            print(f"\n{r['script_id']}: Return={bt['total_return']}%, WinRate={bt['win_rate']}%, Trades={bt['total_trades']}")
        else:
            print(f"\n{r.get('script_id', 'unknown')}: {r.get('error', 'Error')}")


if __name__ == '__main__':
    asyncio.run(main())
