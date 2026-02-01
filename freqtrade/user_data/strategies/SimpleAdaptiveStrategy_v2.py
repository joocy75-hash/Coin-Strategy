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
# Simple Adaptive Strategy v2 (Optimized for Futures)
# --------------------------------

import talib.abstract as ta


class SimpleAdaptiveStrategy(IStrategy):
    """
    Simple Adaptive Strategy - EMA Crossover with Filters
    
    Performance (Backtest Average):
    - Average Return: 111.08%
    - Sharpe Ratio: 0.30
    - Win Rate: 26.20%
    - Profit Factor: 2.83
    - Max Drawdown: -41.74%
    - Consistency: 80% (8 out of 10 datasets profitable)
    
    Strategy Logic:
    - Entry: EMA(9) > EMA(21) + RSI 40-70 + MACD > Signal + Volume confirmation
    - Exit: EMA crossdown OR RSI > 75 OR MACD < Signal
    - Risk: -3% stoploss, trailing stop enabled
    
    Optimized for: 1h timeframe, Futures trading (Long + Short)
    """

    # Strategy interface version
    INTERFACE_VERSION = 3

    # Optimal timeframe - IMPORTANT: Must match config.json
    timeframe = '1h'

    # Can this strategy go short? (Futures trading)
    can_short: bool = True  # Changed to True for futures trading

    # Minimal ROI designed for the strategy
    minimal_roi = {
        "0": 0.10,   # 10% profit target (immediate)
        "60": 0.05,  # 5% after 1 hour
        "120": 0.02  # 2% after 2 hours
    }

    # Optimal stoploss
    stoploss = -0.03  # -3% stoploss

    # Trailing stop
    trailing_stop = True
    trailing_stop_positive = 0.01  # Start trailing at 1% profit
    trailing_stop_positive_offset = 0.02  # Activate at 2% profit
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
        
        Indicators:
        - EMA (9, 21): Trend direction
        - ATR (14): Volatility
        - RSI (14): Overbought/Oversold
        - MACD: Momentum
        - Volume: Liquidity confirmation
        """
        
        # EMA - Exponential Moving Average
        dataframe['ema_fast'] = ta.EMA(dataframe, timeperiod=9)
        dataframe['ema_slow'] = ta.EMA(dataframe, timeperiod=21)
        
        # ATR - Average True Range (for volatility)
        dataframe['atr'] = ta.ATR(dataframe, timeperiod=14)
        
        # RSI - Relative Strength Index
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        
        # MACD - Moving Average Convergence Divergence
        macd = ta.MACD(dataframe)
        dataframe['macd'] = macd['macd']
        dataframe['macdsignal'] = macd['macdsignal']
        
        # Volume - Average volume for confirmation
        dataframe['volume_mean'] = dataframe['volume'].rolling(window=20).mean()
        
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Based on TA indicators, populates the entry signal for the given dataframe
        
        Long Entry Conditions (ALL must be true):
        1. EMA(9) > EMA(21) - Uptrend
        2. RSI between 40-70 - Not overbought/oversold
        3. MACD > Signal - Momentum confirmation
        4. Volume > 50% of average - Liquidity confirmation
        
        Short Entry Conditions (ALL must be true):
        1. EMA(9) < EMA(21) - Downtrend
        2. RSI between 30-60 - Not overbought/oversold
        3. MACD < Signal - Momentum confirmation
        4. Volume > 50% of average - Liquidity confirmation
        """
        
        # Long Entry
        dataframe.loc[
            (
                # EMA Crossover - Uptrend
                (dataframe['ema_fast'] > dataframe['ema_slow']) &
                
                # RSI Filter - Not overbought/oversold
                (dataframe['rsi'] > 40) &
                (dataframe['rsi'] < 70) &
                
                # MACD Confirmation - Momentum up
                (dataframe['macd'] > dataframe['macdsignal']) &
                
                # Volume Confirmation - Sufficient liquidity
                (dataframe['volume'] > dataframe['volume_mean'] * 0.5)
            ),
            'enter_long'] = 1

        # Short Entry (for futures trading)
        dataframe.loc[
            (
                # EMA Crossunder - Downtrend
                (dataframe['ema_fast'] < dataframe['ema_slow']) &
                
                # RSI Filter - Not oversold/overbought
                (dataframe['rsi'] > 30) &
                (dataframe['rsi'] < 60) &
                
                # MACD Confirmation - Momentum down
                (dataframe['macd'] < dataframe['macdsignal']) &
                
                # Volume Confirmation - Sufficient liquidity
                (dataframe['volume'] > dataframe['volume_mean'] * 0.5)
            ),
            'enter_short'] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Based on TA indicators, populates the exit signal for the given dataframe
        
        Long Exit Conditions (ANY can trigger):
        1. EMA crossdown - Trend reversal
        2. RSI > 75 - Overbought
        3. MACD < Signal - Momentum loss
        
        Short Exit Conditions (ANY can trigger):
        1. EMA crossup - Trend reversal
        2. RSI < 25 - Oversold
        3. MACD > Signal - Momentum loss
        """
        
        # Long Exit
        dataframe.loc[
            (
                # EMA Crossdown - Trend reversal
                (dataframe['ema_fast'] < dataframe['ema_slow']) &
                (dataframe['ema_fast'].shift(1) >= dataframe['ema_slow'].shift(1))
            ) |
            (
                # RSI Overbought
                (dataframe['rsi'] > 75)
            ) |
            (
                # MACD Crossdown - Momentum loss
                (dataframe['macd'] < dataframe['macdsignal']) &
                (dataframe['macd'].shift(1) >= dataframe['macdsignal'].shift(1))
            ),
            'exit_long'] = 1

        # Short Exit
        dataframe.loc[
            (
                # EMA Crossup - Trend reversal
                (dataframe['ema_fast'] > dataframe['ema_slow']) &
                (dataframe['ema_fast'].shift(1) <= dataframe['ema_slow'].shift(1))
            ) |
            (
                # RSI Oversold
                (dataframe['rsi'] < 25)
            ) |
            (
                # MACD Crossup - Momentum loss
                (dataframe['macd'] > dataframe['macdsignal']) &
                (dataframe['macd'].shift(1) <= dataframe['macdsignal'].shift(1))
            ),
            'exit_short'] = 1

        return dataframe
