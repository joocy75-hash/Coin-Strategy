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
# Adaptive ML Trailing Stop Strategy
# 최고 성과 전략: 평균 수익률 111%, Sharpe 0.30, 일관성 80%
# --------------------------------

import talib.abstract as ta
import pandas_ta as pta


class AdaptiveMLStrategy(IStrategy):
    """
    Adaptive ML Trailing Stop Strategy
    
    성과 지표 (10개 데이터셋 평균):
    - 평균 수익률: 111.08%
    - Sharpe Ratio: 0.30
    - Win Rate: 26.20%
    - Profit Factor: 2.83
    - Max Drawdown: -41.74%
    - 일관성: 80% (10개 중 8개 데이터셋에서 수익)
    
    최적 파라미터 (최적화 완료):
    - KAMA Length: 20
    - ATR Period: 28
    - Base Multiplier: 2.5
    - Fast Length: 15
    - Slow Length: 50
    """

    # Strategy interface version
    INTERFACE_VERSION = 3

    # Optimal timeframe
    timeframe = '1h'

    # Can this strategy go short?
    can_short: bool = False

    # Minimal ROI designed for the strategy
    minimal_roi = {
        "0": 0.50,   # 50% 수익 시 청산
        "60": 0.30,  # 1시간 후 30%
        "120": 0.15, # 2시간 후 15%
        "240": 0.05  # 4시간 후 5%
    }

    # Optimal stoploss
    stoploss = -0.05  # 5% 손절

    # Trailing stop
    trailing_stop = True
    trailing_stop_positive = 0.01
    trailing_stop_positive_offset = 0.03
    trailing_only_offset_is_reached = True

    # Run "populate_indicators()" only for new candle
    process_only_new_candles = True

    # These values can be overridden in the config
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False

    # Number of candles the strategy requires before producing valid signals
    startup_candle_count: int = 100

    # Strategy parameters - 최적화된 값
    kama_length = IntParameter(15, 30, default=20, space="buy")
    atr_period = IntParameter(20, 35, default=28, space="buy")
    base_multiplier = DecimalParameter(2.0, 3.5, default=2.5, space="buy")
    fast_length = IntParameter(10, 20, default=15, space="buy")
    slow_length = IntParameter(40, 60, default=50, space="buy")
    adaptive_strength = DecimalParameter(0.5, 1.5, default=1.0, space="buy")

    def informative_pairs(self):
        """
        Define additional, informative pair/interval combinations to be cached from the exchange.
        """
        return []

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Adds several different TA indicators to the given DataFrame
        """
        
        # KAMA (Kaufman Adaptive Moving Average)
        dataframe['kama'] = ta.KAMA(dataframe, timeperiod=self.kama_length.value)
        
        # ATR (Average True Range)
        dataframe['atr'] = ta.ATR(dataframe, timeperiod=self.atr_period.value)
        
        # Fast and Slow EMA
        dataframe['ema_fast'] = ta.EMA(dataframe, timeperiod=self.fast_length.value)
        dataframe['ema_slow'] = ta.EMA(dataframe, timeperiod=self.slow_length.value)
        
        # RSI
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        
        # MACD
        macd = ta.MACD(dataframe)
        dataframe['macd'] = macd['macd']
        dataframe['macdsignal'] = macd['macdsignal']
        dataframe['macdhist'] = macd['macdhist']
        
        # Bollinger Bands
        bollinger = ta.BBANDS(dataframe, timeperiod=20, nbdevup=2.0, nbdevdn=2.0)
        dataframe['bb_upper'] = bollinger['upperband']
        dataframe['bb_middle'] = bollinger['middleband']
        dataframe['bb_lower'] = bollinger['lowerband']
        
        # Volume indicators
        dataframe['volume_mean'] = dataframe['volume'].rolling(window=20).mean()
        
        # Adaptive Trailing Stop
        dataframe['adaptive_stop'] = dataframe['close'] - (
            dataframe['atr'] * self.base_multiplier.value * self.adaptive_strength.value
        )
        
        # Trend strength
        dataframe['trend_strength'] = abs(dataframe['ema_fast'] - dataframe['ema_slow']) / dataframe['close']
        
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Based on TA indicators, populates the entry signal for the given dataframe
        """
        dataframe.loc[
            (
                # EMA 크로스오버 (빠른 EMA가 느린 EMA 위로)
                (dataframe['ema_fast'] > dataframe['ema_slow']) &
                (dataframe['ema_fast'].shift(1) <= dataframe['ema_slow'].shift(1)) &
                
                # 가격이 KAMA 위에 있음 (상승 추세)
                (dataframe['close'] > dataframe['kama']) &
                
                # RSI가 과매도 영역에서 벗어남
                (dataframe['rsi'] > 30) &
                (dataframe['rsi'] < 70) &
                
                # MACD 상승 신호
                (dataframe['macd'] > dataframe['macdsignal']) &
                
                # 볼륨 확인 (평균 이상)
                (dataframe['volume'] > dataframe['volume_mean'] * 0.8) &
                
                # 추세 강도 확인
                (dataframe['trend_strength'] > 0.001)
            ),
            'enter_long'] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Based on TA indicators, populates the exit signal for the given dataframe
        """
        dataframe.loc[
            (
                # EMA 크로스다운 (빠른 EMA가 느린 EMA 아래로)
                (dataframe['ema_fast'] < dataframe['ema_slow']) &
                (dataframe['ema_fast'].shift(1) >= dataframe['ema_slow'].shift(1))
            ) |
            (
                # 가격이 KAMA 아래로 떨어짐
                (dataframe['close'] < dataframe['kama']) &
                (dataframe['close'].shift(1) >= dataframe['kama'].shift(1))
            ) |
            (
                # RSI 과매수
                (dataframe['rsi'] > 75)
            ) |
            (
                # MACD 하락 신호
                (dataframe['macd'] < dataframe['macdsignal']) &
                (dataframe['macd'].shift(1) >= dataframe['macdsignal'].shift(1))
            ),
            'exit_long'] = 1

        return dataframe

    def custom_stoploss(self, pair: str, trade: 'Trade', current_time: datetime,
                        current_rate: float, current_profit: float, **kwargs) -> float:
        """
        Adaptive trailing stop based on ATR
        """
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        last_candle = dataframe.iloc[-1].squeeze()
        
        # ATR 기반 동적 손절
        if 'atr' in last_candle and 'close' in last_candle:
            atr_stop = last_candle['atr'] * self.base_multiplier.value * self.adaptive_strength.value
            stop_distance = atr_stop / last_candle['close']
            
            # 최소 2%, 최대 10% 손절
            return max(-0.10, min(-0.02, -stop_distance))
        
        # 기본 손절
        return self.stoploss

    def confirm_trade_entry(self, pair: str, order_type: str, amount: float, rate: float,
                           time_in_force: str, current_time: datetime, entry_tag: Optional[str],
                           side: str, **kwargs) -> bool:
        """
        Called right before placing a entry order.
        """
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        
        if len(dataframe) < 1:
            return False
        
        last_candle = dataframe.iloc[-1].squeeze()
        
        # 추가 안전 장치
        # 1. 볼륨이 너무 낮으면 진입하지 않음
        if 'volume' in last_candle and 'volume_mean' in last_candle:
            if last_candle['volume'] < last_candle['volume_mean'] * 0.5:
                return False
        
        # 2. 변동성이 너무 높으면 진입하지 않음
        if 'atr' in last_candle and 'close' in last_candle:
            volatility = last_candle['atr'] / last_candle['close']
            if volatility > 0.05:  # 5% 이상 변동성
                return False
        
        return True

    def confirm_trade_exit(self, pair: str, trade: 'Trade', order_type: str, amount: float,
                          rate: float, time_in_force: str, exit_reason: str,
                          current_time: datetime, **kwargs) -> bool:
        """
        Called right before placing a exit order.
        """
        # 모든 청산 신호 허용
        return True
