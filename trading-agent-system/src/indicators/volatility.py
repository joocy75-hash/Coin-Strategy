"""
Volatility Indicators

변동성을 측정하는 지표들
- ATR, Bollinger Bands, Keltner Channel, Donchian Channel
- Standard Deviation
"""

import numpy as np
import pandas as pd
from typing import Union


def ATR(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    period: int = 14
) -> pd.Series:
    """
    Average True Range (평균 실제 범위)

    변동성 측정 지표
    높은 ATR = 높은 변동성

    Args:
        high: 고가
        low: 저가
        close: 종가
        period: ATR 기간

    Returns:
        ATR 값
    """
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))

    true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = true_range.ewm(span=period, adjust=False).mean()

    return atr


def BollingerBands(
    data: pd.Series,
    period: int = 20,
    std_dev: float = 2.0
) -> pd.DataFrame:
    """
    Bollinger Bands (볼린저 밴드)

    가격의 상대적 고저 측정
    - 가격 > Upper: 과매수
    - 가격 < Lower: 과매도
    - 밴드 폭: 변동성 측정

    Args:
        data: 가격 데이터 (일반적으로 Close)
        period: 이동평균 기간
        std_dev: 표준편차 배수

    Returns:
        DataFrame with Upper, Middle, Lower, Width, %B
    """
    middle = data.rolling(window=period).mean()
    std = data.rolling(window=period).std()

    upper = middle + (std_dev * std)
    lower = middle - (std_dev * std)

    # 밴드 폭 (변동성)
    width = (upper - lower) / middle * 100

    # %B (0-1 범위, 현재 가격의 밴드 내 위치)
    percent_b = (data - lower) / (upper - lower)

    return pd.DataFrame({
        "Upper": upper,
        "Middle": middle,
        "Lower": lower,
        "Width": width,
        "PercentB": percent_b
    })


def KeltnerChannel(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    ema_period: int = 20,
    atr_period: int = 10,
    multiplier: float = 2.0
) -> pd.DataFrame:
    """
    Keltner Channel (켈트너 채널)

    ATR 기반 변동성 밴드
    볼린저 밴드와 유사하지만 ATR 사용

    Args:
        high: 고가
        low: 저가
        close: 종가
        ema_period: EMA 기간
        atr_period: ATR 기간
        multiplier: ATR 배수

    Returns:
        DataFrame with Upper, Middle, Lower
    """
    # Middle line (EMA)
    middle = close.ewm(span=ema_period, adjust=False).mean()

    # ATR
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = true_range.ewm(span=atr_period, adjust=False).mean()

    # Bands
    upper = middle + (multiplier * atr)
    lower = middle - (multiplier * atr)

    return pd.DataFrame({
        "Upper": upper,
        "Middle": middle,
        "Lower": lower
    })


def DonchianChannel(
    high: pd.Series,
    low: pd.Series,
    period: int = 20
) -> pd.DataFrame:
    """
    Donchian Channel (돈치안 채널)

    N일 최고/최저 기반 채널
    터틀 트레이딩 전략에 사용

    Args:
        high: 고가
        low: 저가
        period: 기간

    Returns:
        DataFrame with Upper, Middle, Lower
    """
    upper = high.rolling(window=period).max()
    lower = low.rolling(window=period).min()
    middle = (upper + lower) / 2

    return pd.DataFrame({
        "Upper": upper,
        "Middle": middle,
        "Lower": lower
    })


def StandardDeviation(
    data: pd.Series,
    period: int = 20
) -> pd.Series:
    """
    Standard Deviation (표준편차)

    가격 변동의 분산 측정

    Args:
        data: 가격 데이터
        period: 기간

    Returns:
        표준편차 값
    """
    return data.rolling(window=period).std()
