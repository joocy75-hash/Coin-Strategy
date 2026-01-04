"""
Momentum Indicators

모멘텀(추세의 속도와 강도)을 측정하는 지표들
- RSI, MACD, Stochastic, CCI, MFI
- Williams %R, ROC, Momentum
"""

import numpy as np
import pandas as pd
from typing import Union


def RSI(data: pd.Series, period: int = 14) -> pd.Series:
    """
    Relative Strength Index (상대강도지수)

    과매수/과매도 측정 (0-100)
    - RSI > 70: 과매수
    - RSI < 30: 과매도

    Args:
        data: 가격 데이터 (일반적으로 Close)
        period: RSI 기간

    Returns:
        RSI 값 (0-100)
    """
    delta = data.diff()

    gain = delta.where(delta > 0, 0)
    loss = (-delta).where(delta < 0, 0)

    avg_gain = gain.ewm(span=period, adjust=False).mean()
    avg_loss = loss.ewm(span=period, adjust=False).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    return rsi


def MACD(
    data: pd.Series,
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9
) -> pd.DataFrame:
    """
    Moving Average Convergence Divergence

    트렌드 추종 모멘텀 지표
    - MACD > Signal: 매수 신호
    - MACD < Signal: 매도 신호

    Args:
        data: 가격 데이터
        fast_period: 빠른 EMA 기간
        slow_period: 느린 EMA 기간
        signal_period: 시그널 라인 기간

    Returns:
        DataFrame with MACD, Signal, Histogram
    """
    fast_ema = data.ewm(span=fast_period, adjust=False).mean()
    slow_ema = data.ewm(span=slow_period, adjust=False).mean()

    macd_line = fast_ema - slow_ema
    signal_line = macd_line.ewm(span=signal_period, adjust=False).mean()
    histogram = macd_line - signal_line

    return pd.DataFrame({
        "MACD": macd_line,
        "Signal": signal_line,
        "Histogram": histogram
    })


def Stochastic(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    k_period: int = 14,
    d_period: int = 3,
    smooth_k: int = 3
) -> pd.DataFrame:
    """
    Stochastic Oscillator (스토캐스틱)

    현재 가격의 최근 범위 내 위치 (0-100)
    - %K > 80: 과매수
    - %K < 20: 과매도

    Args:
        high: 고가
        low: 저가
        close: 종가
        k_period: %K 기간
        d_period: %D 기간
        smooth_k: %K 평활화 기간

    Returns:
        DataFrame with %K, %D
    """
    lowest_low = low.rolling(window=k_period).min()
    highest_high = high.rolling(window=k_period).max()

    # Fast %K
    fast_k = 100 * (close - lowest_low) / (highest_high - lowest_low)

    # Slow %K (smoothed)
    slow_k = fast_k.rolling(window=smooth_k).mean()

    # %D
    slow_d = slow_k.rolling(window=d_period).mean()

    return pd.DataFrame({
        "K": slow_k,
        "D": slow_d
    })


def CCI(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    period: int = 20
) -> pd.Series:
    """
    Commodity Channel Index

    평균 가격으로부터의 편차 측정
    - CCI > 100: 과매수
    - CCI < -100: 과매도

    Args:
        high: 고가
        low: 저가
        close: 종가
        period: CCI 기간

    Returns:
        CCI 값
    """
    typical_price = (high + low + close) / 3
    sma = typical_price.rolling(window=period).mean()
    mad = typical_price.rolling(window=period).apply(
        lambda x: np.abs(x - x.mean()).mean(),
        raw=True
    )

    cci = (typical_price - sma) / (0.015 * mad)
    return cci


def MFI(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    volume: pd.Series,
    period: int = 14
) -> pd.Series:
    """
    Money Flow Index (자금 흐름 지수)

    볼륨 가중 RSI
    - MFI > 80: 과매수
    - MFI < 20: 과매도

    Args:
        high: 고가
        low: 저가
        close: 종가
        volume: 거래량
        period: MFI 기간

    Returns:
        MFI 값 (0-100)
    """
    typical_price = (high + low + close) / 3
    raw_money_flow = typical_price * volume

    # 상승/하락 자금 흐름
    tp_change = typical_price.diff()
    positive_mf = raw_money_flow.where(tp_change > 0, 0)
    negative_mf = raw_money_flow.where(tp_change < 0, 0)

    positive_mf_sum = positive_mf.rolling(window=period).sum()
    negative_mf_sum = negative_mf.rolling(window=period).sum()

    mfi = 100 - (100 / (1 + positive_mf_sum / negative_mf_sum))
    return mfi


def WilliamsR(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    period: int = 14
) -> pd.Series:
    """
    Williams %R

    스토캐스틱과 유사하지만 반전된 스케일 (-100 ~ 0)
    - %R > -20: 과매수
    - %R < -80: 과매도

    Args:
        high: 고가
        low: 저가
        close: 종가
        period: 기간

    Returns:
        Williams %R 값 (-100 ~ 0)
    """
    highest_high = high.rolling(window=period).max()
    lowest_low = low.rolling(window=period).min()

    williams_r = -100 * (highest_high - close) / (highest_high - lowest_low)
    return williams_r


def ROC(data: pd.Series, period: int = 12) -> pd.Series:
    """
    Rate of Change (변화율)

    N일 전 대비 가격 변화율 (%)

    Args:
        data: 가격 데이터
        period: 비교 기간

    Returns:
        ROC 값 (%)
    """
    return ((data - data.shift(period)) / data.shift(period)) * 100


def Momentum(data: pd.Series, period: int = 10) -> pd.Series:
    """
    Momentum Indicator

    N일 전 대비 가격 차이

    Args:
        data: 가격 데이터
        period: 비교 기간

    Returns:
        Momentum 값
    """
    return data - data.shift(period)
