"""
Bitget OHLCV data collector for backtesting.
(Changed from Binance due to US region restrictions)
"""

import ccxt
import pandas as pd
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List
import logging
import json

logger = logging.getLogger(__name__)


class BitgetDataCollector:
    """Collects and caches OHLCV data from Bitget exchange."""

    SUPPORTED_TIMEFRAMES = ["1m", "5m", "15m", "30m", "1h", "4h", "1d", "1w"]
    MAX_CANDLES_PER_REQUEST = 1000

    def __init__(self, cache_dir: str = "data/market_data"):
        """Initialize Bitget data collector."""
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.exchange = ccxt.bitget({
            'enableRateLimit': True,
            'options': {'defaultType': 'spot'}
        })

        logger.info(f"BitgetDataCollector initialized with cache dir: {self.cache_dir}")

    async def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        start_date: str,
        end_date: str,
        force_refresh: bool = False
    ) -> pd.DataFrame:
        """Fetch OHLCV data for a symbol and timeframe within a date range."""
        if timeframe not in self.SUPPORTED_TIMEFRAMES:
            raise ValueError(f"Timeframe {timeframe} not supported.")

        if not force_refresh:
            cached_data = self.get_cached_data(symbol, timeframe, start_date, end_date)
            if cached_data is not None:
                logger.info(f"Using cached data for {symbol} {timeframe}")
                return cached_data

        logger.info(f"Fetching {symbol} {timeframe} data from {start_date} to {end_date}")

        start_ts = self._date_to_timestamp(start_date)
        end_ts = self._date_to_timestamp(end_date)

        all_candles = []
        current_ts = start_ts

        while current_ts < end_ts:
            try:
                candles = await asyncio.to_thread(
                    self.exchange.fetch_ohlcv,
                    symbol, timeframe, current_ts, self.MAX_CANDLES_PER_REQUEST
                )

                if not candles:
                    break

                all_candles.extend(candles)
                current_ts = candles[-1][0] + 1

                if candles[-1][0] >= end_ts:
                    break

                await asyncio.sleep(0.1)

            except ccxt.NetworkError as e:
                logger.error(f"Network error fetching data: {e}")
                raise
            except ccxt.ExchangeError as e:
                logger.error(f"Exchange error: {e}")
                raise

        df = self._candles_to_dataframe(all_candles)

        df = df[
            (df['timestamp'] >= pd.to_datetime(start_date)) &
            (df['timestamp'] <= pd.to_datetime(end_date))
        ]

        self.save_to_cache(df, symbol, timeframe, start_date, end_date)

        logger.info(f"Fetched {len(df)} candles for {symbol} {timeframe}")
        return df

    def get_cached_data(
        self, symbol: str, timeframe: str, start_date: str, end_date: str
    ) -> Optional[pd.DataFrame]:
        """Retrieve cached data if available and valid."""
        cache_file = self._get_cache_filepath(symbol, timeframe, start_date, end_date)

        if not cache_file.exists():
            return None

        try:
            cache_age = datetime.now() - datetime.fromtimestamp(cache_file.stat().st_mtime)
            if cache_age > timedelta(days=1):
                return None

            df = pd.read_parquet(cache_file)
            return df
        except Exception as e:
            logger.warning(f"Error reading cache: {e}")
            return None

    def save_to_cache(
        self, df: pd.DataFrame, symbol: str, timeframe: str, start_date: str, end_date: str
    ) -> None:
        """Save DataFrame to cache."""
        cache_file = self._get_cache_filepath(symbol, timeframe, start_date, end_date)
        cache_file.parent.mkdir(parents=True, exist_ok=True)

        try:
            df.to_parquet(cache_file, index=False)

            metadata = {
                'symbol': symbol, 'timeframe': timeframe,
                'start_date': start_date, 'end_date': end_date,
                'rows': len(df), 'cached_at': datetime.now().isoformat()
            }

            with open(cache_file.with_suffix('.json'), 'w') as f:
                json.dump(metadata, f, indent=2)

        except Exception as e:
            logger.error(f"Error saving to cache: {e}")

    def list_cached_data(self) -> List[dict]:
        """List all cached datasets."""
        cached = []
        for f in self.cache_dir.rglob("*.json"):
            try:
                with open(f, 'r') as file:
                    cached.append(json.load(file))
            except Exception:
                pass
        return cached

    def clear_cache(self, symbol: Optional[str] = None, timeframe: Optional[str] = None) -> int:
        """Clear cached data."""
        deleted = 0
        for f in self.cache_dir.rglob("*.parquet"):
            should_delete = True
            if symbol and symbol.replace('/', '_') not in f.name:
                should_delete = False
            if timeframe and timeframe not in f.name:
                should_delete = False
            if should_delete:
                try:
                    f.unlink()
                    f.with_suffix('.json').unlink(missing_ok=True)
                    deleted += 1
                except Exception:
                    pass
        return deleted

    async def get_available_symbols(self) -> List[str]:
        """Get list of available trading symbols from Binance."""
        try:
            markets = await asyncio.to_thread(self.exchange.load_markets)
            return sorted([s for s, m in markets.items() if m['quote'] == 'USDT' and m['active']])
        except Exception as e:
            logger.error(f"Error fetching symbols: {e}")
            return []

    def _get_cache_filepath(self, symbol: str, timeframe: str, start_date: str, end_date: str) -> Path:
        safe_symbol = symbol.replace('/', '_')
        return self.cache_dir / safe_symbol / f"{safe_symbol}_{timeframe}_{start_date}_{end_date}.parquet"

    def _date_to_timestamp(self, date_str: str) -> int:
        return int(datetime.strptime(date_str, '%Y-%m-%d').timestamp() * 1000)

    def _candles_to_dataframe(self, candles: List[list]) -> pd.DataFrame:
        df = pd.DataFrame(candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = df[col].astype(float)
        return df.sort_values('timestamp').reset_index(drop=True)

    async def close(self):
        """Close exchange connection if supported."""
        if hasattr(self.exchange, 'close'):
            try:
                await asyncio.to_thread(self.exchange.close)
            except Exception:
                pass  # Some exchanges don't support close


class SyncBitgetDataCollector:
    """Synchronous wrapper for BitgetDataCollector."""

    def __init__(self, cache_dir: str = "data/market_data"):
        self.collector = BitgetDataCollector(cache_dir)

    def fetch_ohlcv(self, symbol: str, timeframe: str, start_date: str, end_date: str, force_refresh: bool = False) -> pd.DataFrame:
        return asyncio.run(self.collector.fetch_ohlcv(symbol, timeframe, start_date, end_date, force_refresh))

    def get_available_symbols(self) -> List[str]:
        return asyncio.run(self.collector.get_available_symbols())

    def get_cached_data(self, symbol: str, timeframe: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        return self.collector.get_cached_data(symbol, timeframe, start_date, end_date)

    def list_cached_data(self) -> List[dict]:
        return self.collector.list_cached_data()

    def clear_cache(self, symbol: Optional[str] = None, timeframe: Optional[str] = None) -> int:
        return self.collector.clear_cache(symbol, timeframe)


# Backward compatibility aliases
BinanceDataCollector = BitgetDataCollector
SyncBinanceDataCollector = SyncBitgetDataCollector
