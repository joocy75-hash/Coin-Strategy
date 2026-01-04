"""
Technical Indicators Library

트렌드, 모멘텀, 변동성, 볼륨 지표 20개 이상 구현
backtesting.py와 호환되는 형식으로 제공
"""

from .trend import (
    ADX, Supertrend, Ichimoku, ParabolicSAR,
    EMA, SMA, WMA, HullMA, TEMA, ALMA
)
from .momentum import (
    RSI, MACD, Stochastic, CCI, MFI,
    WilliamsR, ROC, Momentum
)
from .volatility import (
    ATR, BollingerBands, KeltnerChannel, DonchianChannel,
    StandardDeviation
)
from .volume import (
    VWAP, OBV, VolumeProfile, CMF, ADLine
)

__all__ = [
    # Trend
    "ADX", "Supertrend", "Ichimoku", "ParabolicSAR",
    "EMA", "SMA", "WMA", "HullMA", "TEMA", "ALMA",
    # Momentum
    "RSI", "MACD", "Stochastic", "CCI", "MFI",
    "WilliamsR", "ROC", "Momentum",
    # Volatility
    "ATR", "BollingerBands", "KeltnerChannel", "DonchianChannel",
    "StandardDeviation",
    # Volume
    "VWAP", "OBV", "VolumeProfile", "CMF", "ADLine",
]

# 지표 카테고리별 목록
INDICATORS = {
    "trend": ["ADX", "Supertrend", "Ichimoku", "ParabolicSAR", "EMA", "SMA", "WMA", "HullMA", "TEMA", "ALMA"],
    "momentum": ["RSI", "MACD", "Stochastic", "CCI", "MFI", "WilliamsR", "ROC", "Momentum"],
    "volatility": ["ATR", "BollingerBands", "KeltnerChannel", "DonchianChannel", "StandardDeviation"],
    "volume": ["VWAP", "OBV", "VolumeProfile", "CMF", "ADLine"],
}
