"""
Binance Data Collector

Binance API를 통해 히스토리컬 OHLCV 데이터를 수집하는 모듈
"""

import os
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from dataclasses import dataclass

import pandas as pd


@dataclass
class DatasetInfo:
    """데이터셋 정보"""
    symbol: str
    interval: str
    start_date: str
    end_date: str
    rows: int
    file_path: str


class BinanceDataCollector:
    """Binance 히스토리컬 데이터 수집기"""

    # 지원하는 심볼 목록
    DEFAULT_SYMBOLS = [
        "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
        "ADAUSDT", "DOGEUSDT", "DOTUSDT", "MATICUSDT", "AVAXUSDT",
        "LINKUSDT", "ATOMUSDT", "UNIUSDT", "LTCUSDT", "NEARUSDT",
    ]

    # 지원하는 타임프레임
    INTERVALS = {
        "1m": "1 minute",
        "5m": "5 minutes",
        "15m": "15 minutes",
        "30m": "30 minutes",
        "1h": "1 hour",
        "4h": "4 hours",
        "1d": "1 day",
        "1w": "1 week",
    }

    def __init__(
        self,
        api_key: str | None = None,
        api_secret: str | None = None,
        data_dir: str = "data/datasets"
    ):
        """
        Args:
            api_key: Binance API 키 (공개 데이터는 불필요)
            api_secret: Binance API 시크릿
            data_dir: 데이터 저장 디렉토리
        """
        self.api_key = api_key or os.getenv("BINANCE_API_KEY", "")
        self.api_secret = api_secret or os.getenv("BINANCE_API_SECRET", "")
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

    async def fetch_klines(
        self,
        symbol: str,
        interval: str,
        start_date: str,
        end_date: str | None = None
    ) -> pd.DataFrame:
        """
        Binance에서 캔들 데이터 수집

        Args:
            symbol: 심볼 (예: BTCUSDT)
            interval: 타임프레임 (예: 1h, 4h, 1d)
            start_date: 시작일 (YYYY-MM-DD)
            end_date: 종료일 (YYYY-MM-DD)

        Returns:
            OHLCV DataFrame
        """
        try:
            from binance.client import Client
        except ImportError:
            raise ImportError("python-binance 패키지를 설치하세요: pip install python-binance")

        client = Client(self.api_key, self.api_secret)

        # 타임프레임 매핑
        interval_map = {
            "1m": Client.KLINE_INTERVAL_1MINUTE,
            "5m": Client.KLINE_INTERVAL_5MINUTE,
            "15m": Client.KLINE_INTERVAL_15MINUTE,
            "30m": Client.KLINE_INTERVAL_30MINUTE,
            "1h": Client.KLINE_INTERVAL_1HOUR,
            "4h": Client.KLINE_INTERVAL_4HOUR,
            "1d": Client.KLINE_INTERVAL_1DAY,
            "1w": Client.KLINE_INTERVAL_1WEEK,
        }

        binance_interval = interval_map.get(interval, Client.KLINE_INTERVAL_1HOUR)
        end_date = end_date or datetime.now().strftime("%Y-%m-%d")

        # 데이터 수집 (동기 API를 비동기로 실행)
        klines = await asyncio.to_thread(
            client.get_historical_klines,
            symbol,
            binance_interval,
            start_date,
            end_date
        )

        if not klines:
            return pd.DataFrame()

        # DataFrame 변환
        df = pd.DataFrame(klines, columns=[
            "timestamp", "Open", "High", "Low", "Close", "Volume",
            "close_time", "quote_volume", "trades", "taker_buy_base",
            "taker_buy_quote", "ignore"
        ])

        # 타입 변환
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df = df[["timestamp", "Open", "High", "Low", "Close", "Volume"]]

        for col in ["Open", "High", "Low", "Close", "Volume"]:
            df[col] = df[col].astype(float)

        df.set_index("timestamp", inplace=True)

        return df

    async def download_dataset(
        self,
        symbol: str,
        interval: str,
        start_date: str,
        end_date: str | None = None,
        save_format: str = "parquet"
    ) -> DatasetInfo:
        """
        데이터셋 다운로드 및 저장

        Args:
            symbol: 심볼
            interval: 타임프레임
            start_date: 시작일
            end_date: 종료일
            save_format: 저장 형식 (parquet 또는 csv)

        Returns:
            DatasetInfo
        """
        df = await self.fetch_klines(symbol, interval, start_date, end_date)

        if df.empty:
            raise ValueError(f"No data found for {symbol}")

        # 파일 저장
        filename = f"{symbol}_{interval}.{save_format}"
        file_path = self.data_dir / filename

        if save_format == "parquet":
            df.to_parquet(file_path)
        else:
            df.to_csv(file_path)

        return DatasetInfo(
            symbol=symbol,
            interval=interval,
            start_date=str(df.index.min()),
            end_date=str(df.index.max()),
            rows=len(df),
            file_path=str(file_path)
        )

    async def download_all_datasets(
        self,
        symbols: list[str] | None = None,
        intervals: list[str] | None = None,
        start_date: str = "2023-01-01",
        end_date: str | None = None
    ) -> list[DatasetInfo]:
        """
        여러 심볼/타임프레임 조합 다운로드

        Args:
            symbols: 심볼 목록 (기본: DEFAULT_SYMBOLS)
            intervals: 타임프레임 목록 (기본: ["1h", "4h", "1d"])
            start_date: 시작일
            end_date: 종료일

        Returns:
            DatasetInfo 목록
        """
        symbols = symbols or self.DEFAULT_SYMBOLS[:5]  # 기본 5개
        intervals = intervals or ["1h", "4h", "1d"]

        results = []
        total = len(symbols) * len(intervals)
        count = 0

        for symbol in symbols:
            for interval in intervals:
                count += 1
                print(f"[{count}/{total}] Downloading {symbol} {interval}...")

                try:
                    info = await self.download_dataset(
                        symbol=symbol,
                        interval=interval,
                        start_date=start_date,
                        end_date=end_date
                    )
                    results.append(info)
                    print(f"  ✓ {info.rows} rows saved to {info.file_path}")

                    # Rate limiting
                    await asyncio.sleep(0.5)

                except Exception as e:
                    print(f"  ✗ Error: {e}")

        return results

    def load_dataset(self, symbol: str, interval: str) -> pd.DataFrame:
        """
        저장된 데이터셋 로드

        Args:
            symbol: 심볼
            interval: 타임프레임

        Returns:
            OHLCV DataFrame
        """
        # parquet 먼저 시도
        parquet_path = self.data_dir / f"{symbol}_{interval}.parquet"
        if parquet_path.exists():
            return pd.read_parquet(parquet_path)

        # csv 시도
        csv_path = self.data_dir / f"{symbol}_{interval}.csv"
        if csv_path.exists():
            df = pd.read_csv(csv_path, index_col=0, parse_dates=True)
            return df

        raise FileNotFoundError(f"Dataset not found: {symbol}_{interval}")

    def list_datasets(self) -> list[dict[str, Any]]:
        """저장된 데이터셋 목록 반환"""
        datasets = []

        for file_path in self.data_dir.glob("*.parquet"):
            name = file_path.stem
            parts = name.rsplit("_", 1)
            if len(parts) == 2:
                datasets.append({
                    "symbol": parts[0],
                    "interval": parts[1],
                    "format": "parquet",
                    "path": str(file_path)
                })

        for file_path in self.data_dir.glob("*.csv"):
            name = file_path.stem
            parts = name.rsplit("_", 1)
            if len(parts) == 2:
                datasets.append({
                    "symbol": parts[0],
                    "interval": parts[1],
                    "format": "csv",
                    "path": str(file_path)
                })

        return datasets
