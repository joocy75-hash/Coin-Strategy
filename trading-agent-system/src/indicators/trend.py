"""
Trend Indicators

트렌드 방향과 강도를 측정하는 지표들
- ADX, Supertrend, Ichimoku, Parabolic SAR
- 이동평균: EMA, SMA, WMA, Hull MA, TEMA, ALMA
"""

import numpy as np
import pandas as pd
from typing import Union


def SMA(data: pd.Series, period: int = 20) -> pd.Series:
    """
    Simple Moving Average (단순 이동평균)

    Args:
        data: 가격 데이터 (일반적으로 Close)
        period: 이동평균 기간

    Returns:
        SMA 값
    """
    return data.rolling(window=period).mean()


def EMA(data: pd.Series, period: int = 20) -> pd.Series:
    """
    Exponential Moving Average (지수 이동평균)

    최근 가격에 더 많은 가중치를 부여

    Args:
        data: 가격 데이터
        period: 이동평균 기간

    Returns:
        EMA 값
    """
    return data.ewm(span=period, adjust=False).mean()


def WMA(data: pd.Series, period: int = 20) -> pd.Series:
    """
    Weighted Moving Average (가중 이동평균)

    선형적으로 증가하는 가중치 적용

    Args:
        data: 가격 데이터
        period: 이동평균 기간

    Returns:
        WMA 값
    """
    weights = np.arange(1, period + 1)
    return data.rolling(window=period).apply(
        lambda x: np.dot(x, weights) / weights.sum(),
        raw=True
    )


def HullMA(data: pd.Series, period: int = 20) -> pd.Series:
    """
    Hull Moving Average

    빠른 반응과 낮은 지연을 가진 이동평균
    HMA = WMA(2 * WMA(n/2) - WMA(n), sqrt(n))

    Args:
        data: 가격 데이터
        period: 이동평균 기간

    Returns:
        Hull MA 값
    """
    half_period = int(period / 2)
    sqrt_period = int(np.sqrt(period))

    wma_half = WMA(data, half_period)
    wma_full = WMA(data, period)

    return WMA(2 * wma_half - wma_full, sqrt_period)


def TEMA(data: pd.Series, period: int = 20) -> pd.Series:
    """
    Triple Exponential Moving Average

    3중 지수 이동평균으로 지연 최소화
    TEMA = 3*EMA1 - 3*EMA2 + EMA3

    Args:
        data: 가격 데이터
        period: 이동평균 기간

    Returns:
        TEMA 값
    """
    ema1 = EMA(data, period)
    ema2 = EMA(ema1, period)
    ema3 = EMA(ema2, period)

    return 3 * ema1 - 3 * ema2 + ema3


def ALMA(
    data: pd.Series,
    period: int = 20,
    offset: float = 0.85,
    sigma: float = 6
) -> pd.Series:
    """
    Arnaud Legoux Moving Average

    가우시안 분포 기반 가중치를 사용하는 이동평균

    Args:
        data: 가격 데이터
        period: 이동평균 기간
        offset: 가중치 중심 위치 (0-1, 높을수록 최근에 집중)
        sigma: 가중치 분포 너비 (높을수록 더 넓게 분포)

    Returns:
        ALMA 값
    """
    m = offset * (period - 1)
    s = period / sigma

    weights = np.exp(-((np.arange(period) - m) ** 2) / (2 * s * s))
    weights = weights / weights.sum()

    return data.rolling(window=period).apply(
        lambda x: np.dot(x, weights),
        raw=True
    )


def ADX(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    period: int = 14
) -> pd.DataFrame:
    """
    Average Directional Index (평균 방향성 지수)

    트렌드의 강도를 측정 (0-100)
    - ADX > 25: 트렌드 존재
    - ADX < 20: 횡보

    Args:
        high: 고가
        low: 저가
        close: 종가
        period: 기간

    Returns:
        DataFrame with ADX, +DI, -DI
    """
    # True Range
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    # Directional Movement
    up_move = high - high.shift(1)
    down_move = low.shift(1) - low

    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)

    # Smoothed values
    atr = pd.Series(tr).ewm(span=period, adjust=False).mean()
    plus_di = 100 * pd.Series(plus_dm).ewm(span=period, adjust=False).mean() / atr
    minus_di = 100 * pd.Series(minus_dm).ewm(span=period, adjust=False).mean() / atr

    # ADX
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
    adx = dx.ewm(span=period, adjust=False).mean()

    return pd.DataFrame({
        "ADX": adx,
        "+DI": plus_di,
        "-DI": minus_di
    })


def Supertrend(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    period: int = 10,
    multiplier: float = 3.0
) -> pd.DataFrame:
    """
    Supertrend Indicator

    트렌드 방향 및 지지/저항 레벨
    - 가격 > Supertrend: 상승 트렌드
    - 가격 < Supertrend: 하락 트렌드

    Args:
        high: 고가
        low: 저가
        close: 종가
        period: ATR 기간
        multiplier: ATR 배수

    Returns:
        DataFrame with Supertrend, Direction
    """
    # ATR
    tr = pd.concat([
        high - low,
        abs(high - close.shift(1)),
        abs(low - close.shift(1))
    ], axis=1).max(axis=1)
    atr = tr.ewm(span=period, adjust=False).mean()

    # Basic bands
    hl2 = (high + low) / 2
    upper_band = hl2 + (multiplier * atr)
    lower_band = hl2 - (multiplier * atr)

    # Supertrend calculation
    supertrend = pd.Series(index=close.index, dtype=float)
    direction = pd.Series(index=close.index, dtype=int)

    supertrend.iloc[0] = upper_band.iloc[0]
    direction.iloc[0] = -1

    for i in range(1, len(close)):
        if close.iloc[i] > supertrend.iloc[i-1]:
            supertrend.iloc[i] = lower_band.iloc[i]
            direction.iloc[i] = 1
        elif close.iloc[i] < supertrend.iloc[i-1]:
            supertrend.iloc[i] = upper_band.iloc[i]
            direction.iloc[i] = -1
        else:
            supertrend.iloc[i] = supertrend.iloc[i-1]
            direction.iloc[i] = direction.iloc[i-1]

            if direction.iloc[i] == 1 and lower_band.iloc[i] > supertrend.iloc[i]:
                supertrend.iloc[i] = lower_band.iloc[i]
            elif direction.iloc[i] == -1 and upper_band.iloc[i] < supertrend.iloc[i]:
                supertrend.iloc[i] = upper_band.iloc[i]

    return pd.DataFrame({
        "Supertrend": supertrend,
        "Direction": direction
    })


def Ichimoku(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    tenkan_period: int = 9,
    kijun_period: int = 26,
    senkou_b_period: int = 52
) -> pd.DataFrame:
    """
    Ichimoku Cloud (일목균형표)

    - Tenkan-sen (전환선): 단기 추세
    - Kijun-sen (기준선): 중기 추세
    - Senkou Span A/B: 구름대
    - Chikou Span (후행스팬): 현재가 26일 전 이동

    Args:
        high: 고가
        low: 저가
        close: 종가
        tenkan_period: 전환선 기간 (기본 9)
        kijun_period: 기준선 기간 (기본 26)
        senkou_b_period: 선행스팬 B 기간 (기본 52)

    Returns:
        DataFrame with all Ichimoku components
    """
    # Tenkan-sen (전환선)
    tenkan_high = high.rolling(window=tenkan_period).max()
    tenkan_low = low.rolling(window=tenkan_period).min()
    tenkan = (tenkan_high + tenkan_low) / 2

    # Kijun-sen (기준선)
    kijun_high = high.rolling(window=kijun_period).max()
    kijun_low = low.rolling(window=kijun_period).min()
    kijun = (kijun_high + kijun_low) / 2

    # Senkou Span A (선행스팬 A) - 26일 후 이동
    senkou_a = ((tenkan + kijun) / 2).shift(kijun_period)

    # Senkou Span B (선행스팬 B) - 26일 후 이동
    senkou_b_high = high.rolling(window=senkou_b_period).max()
    senkou_b_low = low.rolling(window=senkou_b_period).min()
    senkou_b = ((senkou_b_high + senkou_b_low) / 2).shift(kijun_period)

    # Chikou Span (후행스팬) - 26일 전 이동
    chikou = close.shift(-kijun_period)

    return pd.DataFrame({
        "Tenkan": tenkan,
        "Kijun": kijun,
        "SenkouA": senkou_a,
        "SenkouB": senkou_b,
        "Chikou": chikou
    })


def ParabolicSAR(
    high: pd.Series,
    low: pd.Series,
    af_start: float = 0.02,
    af_increment: float = 0.02,
    af_max: float = 0.2
) -> pd.DataFrame:
    """
    Parabolic SAR (Stop and Reverse)

    추세 전환점 및 추적 손절 레벨

    Args:
        high: 고가
        low: 저가
        af_start: 초기 가속 계수
        af_increment: 가속 계수 증가분
        af_max: 최대 가속 계수

    Returns:
        DataFrame with SAR, Trend (1: 상승, -1: 하락)
    """
    length = len(high)
    sar = pd.Series(index=high.index, dtype=float)
    trend = pd.Series(index=high.index, dtype=int)
    af = af_start
    ep = low.iloc[0]

    # 초기화
    sar.iloc[0] = high.iloc[0]
    trend.iloc[0] = -1

    for i in range(1, length):
        if trend.iloc[i-1] == 1:  # 상승 추세
            sar.iloc[i] = sar.iloc[i-1] + af * (ep - sar.iloc[i-1])
            sar.iloc[i] = min(sar.iloc[i], low.iloc[i-1], low.iloc[i-2] if i > 1 else low.iloc[i-1])

            if low.iloc[i] < sar.iloc[i]:
                trend.iloc[i] = -1
                sar.iloc[i] = ep
                ep = low.iloc[i]
                af = af_start
            else:
                trend.iloc[i] = 1
                if high.iloc[i] > ep:
                    ep = high.iloc[i]
                    af = min(af + af_increment, af_max)
        else:  # 하락 추세
            sar.iloc[i] = sar.iloc[i-1] + af * (ep - sar.iloc[i-1])
            sar.iloc[i] = max(sar.iloc[i], high.iloc[i-1], high.iloc[i-2] if i > 1 else high.iloc[i-1])

            if high.iloc[i] > sar.iloc[i]:
                trend.iloc[i] = 1
                sar.iloc[i] = ep
                ep = high.iloc[i]
                af = af_start
            else:
                trend.iloc[i] = -1
                if low.iloc[i] < ep:
                    ep = low.iloc[i]
                    af = min(af + af_increment, af_max)

    return pd.DataFrame({
        "SAR": sar,
        "Trend": trend
    })
