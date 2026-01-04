"""
Indicators Module Tests

기술 지표 모듈 단위 테스트
"""

import numpy as np
import pandas as pd
import pytest

from src.indicators import (
    # Trend
    ADX, Supertrend, Ichimoku, ParabolicSAR,
    EMA, SMA, WMA, HullMA, TEMA,
    # Momentum
    RSI, MACD, Stochastic, CCI, MFI,
    WilliamsR, ROC, Momentum,
    # Volatility
    ATR, BollingerBands, KeltnerChannel, DonchianChannel,
    # Volume
    VWAP, OBV, CMF, VolumeProfile,
)


@pytest.fixture
def sample_ohlcv_data():
    """테스트용 OHLCV 데이터 생성"""
    np.random.seed(42)
    n = 100

    # 현실적인 가격 데이터 생성
    close = 100 + np.cumsum(np.random.randn(n) * 0.5)
    high = close + np.abs(np.random.randn(n) * 0.3)
    low = close - np.abs(np.random.randn(n) * 0.3)
    open_price = low + np.random.rand(n) * (high - low)
    volume = np.abs(np.random.randn(n) * 1000000 + 5000000)

    df = pd.DataFrame({
        "Open": open_price,
        "High": high,
        "Low": low,
        "Close": close,
        "Volume": volume,
    })

    return df


class TestTrendIndicators:
    """추세 지표 테스트"""

    def test_adx(self, sample_ohlcv_data):
        """ADX 계산 테스트"""
        result = ADX(
            sample_ohlcv_data["High"],
            sample_ohlcv_data["Low"],
            sample_ohlcv_data["Close"],
            period=14
        )

        # ADX는 DataFrame 또는 Series 반환 가능
        assert result is not None
        # DataFrame인 경우 ADX 컬럼 확인
        if hasattr(result, 'columns'):
            assert len(result) == len(sample_ohlcv_data)
        else:
            assert len(result) == len(sample_ohlcv_data)

    def test_supertrend(self, sample_ohlcv_data):
        """Supertrend 계산 테스트"""
        result = Supertrend(
            sample_ohlcv_data["High"],
            sample_ohlcv_data["Low"],
            sample_ohlcv_data["Close"],
            period=10,
            multiplier=3.0
        )

        assert len(result) == len(sample_ohlcv_data)

    def test_ema(self, sample_ohlcv_data):
        """EMA 계산 테스트"""
        result = EMA(sample_ohlcv_data["Close"], period=20)

        assert len(result) == len(sample_ohlcv_data)
        assert result.notna().sum() > 0

    def test_sma(self, sample_ohlcv_data):
        """SMA 계산 테스트"""
        result = SMA(sample_ohlcv_data["Close"], period=20)

        assert len(result) == len(sample_ohlcv_data)
        # SMA는 period 이후부터 값이 있어야 함
        assert result.notna().sum() >= len(sample_ohlcv_data) - 20

    def test_ichimoku(self, sample_ohlcv_data):
        """Ichimoku 계산 테스트"""
        result = Ichimoku(
            sample_ohlcv_data["High"],
            sample_ohlcv_data["Low"],
            sample_ohlcv_data["Close"]
        )

        # 딕셔너리 또는 tuple 형태
        assert result is not None

    def test_parabolic_sar(self, sample_ohlcv_data):
        """Parabolic SAR 계산 테스트"""
        result = ParabolicSAR(
            sample_ohlcv_data["High"],
            sample_ohlcv_data["Low"]
        )

        assert len(result) == len(sample_ohlcv_data)

    def test_hull_ma(self, sample_ohlcv_data):
        """Hull MA 계산 테스트"""
        result = HullMA(sample_ohlcv_data["Close"], period=20)

        assert len(result) == len(sample_ohlcv_data)

    def test_tema(self, sample_ohlcv_data):
        """TEMA 계산 테스트"""
        result = TEMA(sample_ohlcv_data["Close"], period=20)

        assert len(result) == len(sample_ohlcv_data)


class TestMomentumIndicators:
    """모멘텀 지표 테스트"""

    def test_rsi(self, sample_ohlcv_data):
        """RSI 계산 테스트"""
        result = RSI(sample_ohlcv_data["Close"], period=14)

        assert len(result) == len(sample_ohlcv_data)
        valid_values = result.dropna()
        if len(valid_values) > 0:
            assert (valid_values >= 0).all()
            assert (valid_values <= 100).all()

    def test_macd(self, sample_ohlcv_data):
        """MACD 계산 테스트"""
        result = MACD(sample_ohlcv_data["Close"])

        # MACD는 tuple(macd, signal, histogram) 반환
        assert result is not None

    def test_stochastic(self, sample_ohlcv_data):
        """Stochastic 계산 테스트"""
        result = Stochastic(
            sample_ohlcv_data["High"],
            sample_ohlcv_data["Low"],
            sample_ohlcv_data["Close"]
        )

        assert result is not None

    def test_cci(self, sample_ohlcv_data):
        """CCI 계산 테스트"""
        result = CCI(
            sample_ohlcv_data["High"],
            sample_ohlcv_data["Low"],
            sample_ohlcv_data["Close"],
            period=20
        )

        assert len(result) == len(sample_ohlcv_data)

    def test_mfi(self, sample_ohlcv_data):
        """MFI 계산 테스트"""
        result = MFI(
            sample_ohlcv_data["High"],
            sample_ohlcv_data["Low"],
            sample_ohlcv_data["Close"],
            sample_ohlcv_data["Volume"],
            period=14
        )

        assert len(result) == len(sample_ohlcv_data)
        valid_values = result.dropna()
        if len(valid_values) > 0:
            assert (valid_values >= 0).all()
            assert (valid_values <= 100).all()

    def test_williams_r(self, sample_ohlcv_data):
        """Williams %R 계산 테스트"""
        result = WilliamsR(
            sample_ohlcv_data["High"],
            sample_ohlcv_data["Low"],
            sample_ohlcv_data["Close"],
            period=14
        )

        assert len(result) == len(sample_ohlcv_data)
        valid_values = result.dropna()
        if len(valid_values) > 0:
            assert (valid_values >= -100).all()
            assert (valid_values <= 0).all()

    def test_roc(self, sample_ohlcv_data):
        """ROC 계산 테스트"""
        result = ROC(sample_ohlcv_data["Close"], period=12)

        assert len(result) == len(sample_ohlcv_data)

    def test_momentum(self, sample_ohlcv_data):
        """Momentum 계산 테스트"""
        result = Momentum(sample_ohlcv_data["Close"], period=10)

        assert len(result) == len(sample_ohlcv_data)


class TestVolatilityIndicators:
    """변동성 지표 테스트"""

    def test_atr(self, sample_ohlcv_data):
        """ATR 계산 테스트"""
        result = ATR(
            sample_ohlcv_data["High"],
            sample_ohlcv_data["Low"],
            sample_ohlcv_data["Close"],
            period=14
        )

        assert len(result) == len(sample_ohlcv_data)
        valid_values = result.dropna()
        if len(valid_values) > 0:
            assert (valid_values >= 0).all()

    def test_bollinger_bands(self, sample_ohlcv_data):
        """Bollinger Bands 계산 테스트"""
        result = BollingerBands(sample_ohlcv_data["Close"], period=20, std_dev=2.0)

        # DataFrame 또는 tuple(upper, middle, lower) 반환
        assert result is not None
        # DataFrame인 경우
        if hasattr(result, 'columns'):
            assert len(result) == len(sample_ohlcv_data)
            assert 'Upper' in result.columns or 'upper' in result.columns
        else:
            # tuple인 경우
            assert len(result) == 3

    def test_keltner_channel(self, sample_ohlcv_data):
        """Keltner Channel 계산 테스트"""
        result = KeltnerChannel(
            sample_ohlcv_data["High"],
            sample_ohlcv_data["Low"],
            sample_ohlcv_data["Close"]
        )

        assert result is not None

    def test_donchian_channel(self, sample_ohlcv_data):
        """Donchian Channel 계산 테스트"""
        result = DonchianChannel(
            sample_ohlcv_data["High"],
            sample_ohlcv_data["Low"]
        )

        assert result is not None


class TestVolumeIndicators:
    """거래량 지표 테스트"""

    def test_vwap(self, sample_ohlcv_data):
        """VWAP 계산 테스트"""
        result = VWAP(
            sample_ohlcv_data["High"],
            sample_ohlcv_data["Low"],
            sample_ohlcv_data["Close"],
            sample_ohlcv_data["Volume"]
        )

        assert len(result) == len(sample_ohlcv_data)

    def test_obv(self, sample_ohlcv_data):
        """OBV 계산 테스트"""
        result = OBV(
            sample_ohlcv_data["Close"],
            sample_ohlcv_data["Volume"]
        )

        assert len(result) == len(sample_ohlcv_data)

    def test_cmf(self, sample_ohlcv_data):
        """CMF 계산 테스트"""
        result = CMF(
            sample_ohlcv_data["High"],
            sample_ohlcv_data["Low"],
            sample_ohlcv_data["Close"],
            sample_ohlcv_data["Volume"],
            period=20
        )

        assert len(result) == len(sample_ohlcv_data)
        valid_values = result.dropna()
        if len(valid_values) > 0:
            assert (valid_values >= -1).all()
            assert (valid_values <= 1).all()


class TestEdgeCases:
    """엣지 케이스 테스트"""

    def test_small_dataset(self):
        """작은 데이터셋 처리"""
        small_df = pd.DataFrame({
            "Open": [100.0, 101.0, 99.0],
            "High": [102.0, 103.0, 100.0],
            "Low": [99.0, 100.0, 98.0],
            "Close": [101.0, 100.0, 99.0],
            "Volume": [1000.0, 1100.0, 900.0],
        })

        # 에러 없이 처리되어야 함
        result = RSI(small_df["Close"], period=14)
        assert len(result) == 3

    def test_constant_prices(self):
        """일정한 가격 (변동 없음) 처리"""
        constant_df = pd.DataFrame({
            "Open": [100.0] * 50,
            "High": [100.0] * 50,
            "Low": [100.0] * 50,
            "Close": [100.0] * 50,
            "Volume": [1000000.0] * 50,
        })

        # RSI는 정의되지 않을 수 있음 (변화가 없으므로)
        result = RSI(constant_df["Close"], period=14)
        assert len(result) == 50


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
