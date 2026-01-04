"""
Volume Indicators

거래량 기반 지표들
- VWAP, OBV, Volume Profile, CMF, A/D Line
"""

import numpy as np
import pandas as pd
from typing import Union


def VWAP(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    volume: pd.Series
) -> pd.Series:
    """
    Volume Weighted Average Price (거래량 가중 평균 가격)

    기관 투자자들이 사용하는 공정 가격 지표
    - 가격 > VWAP: 매수자 우위
    - 가격 < VWAP: 매도자 우위

    Args:
        high: 고가
        low: 저가
        close: 종가
        volume: 거래량

    Returns:
        VWAP 값
    """
    typical_price = (high + low + close) / 3
    vwap = (typical_price * volume).cumsum() / volume.cumsum()
    return vwap


def OBV(close: pd.Series, volume: pd.Series) -> pd.Series:
    """
    On Balance Volume (균형 거래량)

    거래량 기반 추세 확인 지표
    - 가격 상승 시 거래량 추가
    - 가격 하락 시 거래량 차감

    Args:
        close: 종가
        volume: 거래량

    Returns:
        OBV 값
    """
    direction = np.sign(close.diff())
    direction.iloc[0] = 0
    obv = (direction * volume).cumsum()
    return obv


def VolumeProfile(
    close: pd.Series,
    volume: pd.Series,
    price_bins: int = 50
) -> pd.DataFrame:
    """
    Volume Profile

    가격대별 거래량 분포
    POC (Point of Control): 가장 많은 거래량이 발생한 가격대

    Args:
        close: 종가
        volume: 거래량
        price_bins: 가격 구간 수

    Returns:
        DataFrame with price levels and volume at each level
    """
    price_min = close.min()
    price_max = close.max()

    bins = np.linspace(price_min, price_max, price_bins + 1)
    price_levels = (bins[:-1] + bins[1:]) / 2

    volume_at_price = []
    for i in range(len(bins) - 1):
        mask = (close >= bins[i]) & (close < bins[i+1])
        volume_at_price.append(volume[mask].sum())

    df = pd.DataFrame({
        "PriceLevel": price_levels,
        "Volume": volume_at_price
    })

    # POC (최대 거래량 가격)
    poc_idx = df["Volume"].idxmax()
    df["IsPOC"] = df.index == poc_idx

    return df


def CMF(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    volume: pd.Series,
    period: int = 20
) -> pd.Series:
    """
    Chaikin Money Flow

    매수/매도 압력 측정 (-1 ~ 1)
    - CMF > 0: 매수 압력 (매집)
    - CMF < 0: 매도 압력 (분산)

    Args:
        high: 고가
        low: 저가
        close: 종가
        volume: 거래량
        period: CMF 기간

    Returns:
        CMF 값 (-1 ~ 1)
    """
    # Money Flow Multiplier
    mfm = ((close - low) - (high - close)) / (high - low)
    mfm = mfm.fillna(0)

    # Money Flow Volume
    mfv = mfm * volume

    # CMF
    cmf = mfv.rolling(window=period).sum() / volume.rolling(window=period).sum()
    return cmf


def ADLine(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    volume: pd.Series
) -> pd.Series:
    """
    Accumulation/Distribution Line

    자금 흐름 추적 지표
    - A/D 상승: 매집 (accumulation)
    - A/D 하락: 분산 (distribution)

    Args:
        high: 고가
        low: 저가
        close: 종가
        volume: 거래량

    Returns:
        A/D Line 값
    """
    # Money Flow Multiplier
    mfm = ((close - low) - (high - close)) / (high - low)
    mfm = mfm.fillna(0)

    # Money Flow Volume
    mfv = mfm * volume

    # Accumulation/Distribution Line
    ad_line = mfv.cumsum()
    return ad_line
