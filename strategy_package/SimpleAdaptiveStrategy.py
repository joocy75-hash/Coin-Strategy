# pragma pylint: disable=missing-docstring, invalid-name, pointless-string-statement
# flake8: noqa: F401
# isort: skip_file
# --- Do not remove these libs ---
import numpy as np
import pandas as pd
from pandas import DataFrame
from datetime import datetime
from typing import Optional, Union

from freqtrade.strategy import (BooleanParameter, CategoricalParameter, DecimalParameter,
                                IntParameter, IStrategy, merge_informative_pair)

# --------------------------------
# Simple Adaptive Strategy (실전 최적화)
# --------------------------------

import talib.abstract as ta


class SimpleAdaptiveStrategy(IStrategy):
    """
    간단하고 효과적인 적응형 전략
    
    특징:
    - EMA 크로스오버 기반
    - ATR 동적 손절
    - RSI 필터링
    - 트레일링 스톱
    """

    # Strategy interface version
    INTERFACE_VERSION = 3

    # Optimal timeframe
    timeframe = '1h'

    # Can this strategy go short?
    can_short: bool = False

    # Minimal ROI
    minimal_roi = {
        "0": 0.10,   # 10% 수익 시 청산
        "60": 0.05,  # 1시간 후 5%
        "120": 0.02  # 2시간 후 2%
    }

    # Optimal stoploss
    stoploss = -0.03  # 3% 손절

    # Trailing stop
    trailing_stop = True
    trailing_stop_positive = 0.01
    trailing_stop_positive_offset = 0.02
    trailing_only_offset_is_reached = True

    # Run "populate_indicators()" only for new candle
    process_only_new_candles = True

    # These values can be overridden in the config
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False

    # Number of candles the strategy requires before producing valid signals
    startup_candle_count: int = 50

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Adds several different TA indicators to the given DataFrame
        """
        
        # EMA
        dataframe['ema_fast'] = ta.EMA(dataframe, timeperiod=9)
        dataframe['ema_slow'] = ta.EMA(dataframe, timeperiod=21)
        
        # ATR
        dataframe['atr'] = ta.ATR(dataframe, timeperiod=14)
        
        # RSI
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        
        # MACD
        macd = ta.MACD(dataframe)
        dataframe['macd'] = macd['macd']
        dataframe['macdsignal'] = macd['macdsignal']
        
        # Volume
        dataframe['volume_mean'] = dataframe['volume'].rolling(window=20).mean()
        
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Based on TA indicators, populates the entry signal for the given dataframe
        """
        dataframe.loc[
            (
                # EMA 크로스오버
                (dataframe['ema_fast'] > dataframe['ema_slow']) &
                
                # RSI 조건
                (dataframe['rsi'] > 40) &
                (dataframe['rsi'] < 70) &
                
                # MACD 상승
                (dataframe['macd'] > dataframe['macdsignal']) &
                
                # 볼륨 확인
                (dataframe['volume'] > dataframe['volume_mean'] * 0.5)
            ),
            'enter_long'] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Based on TA indicators, populates the exit signal for the given dataframe
        """
        dataframe.loc[
            (
                # EMA 크로스다운
                (dataframe['ema_fast'] < dataframe['ema_slow']) &
                (dataframe['ema_fast'].shift(1) >= dataframe['ema_slow'].shift(1))
            ) |
            (
                # RSI 과매수
                (dataframe['rsi'] > 75)
            ) |
            (
                # MACD 하락
                (dataframe['macd'] < dataframe['macdsignal']) &
                (dataframe['macd'].shift(1) >= dataframe['macdsignal'].shift(1))
            ),
            'exit_long'] = 1

        return dataframe
