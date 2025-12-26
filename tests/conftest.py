"""
Pytest Configuration and Fixtures

TradingView Strategy Research Lab 테스트를 위한 공통 설정과 픽스처
"""

import pytest
import sys
from pathlib import Path

# 프로젝트 루트 경로 추가
sys.path.insert(0, str(Path(__file__).parent.parent))


# ============================================================
# Sample Pine Script Fixtures
# ============================================================

@pytest.fixture
def sample_pine_script_safe():
    """리페인팅 위험이 없는 안전한 Pine Script"""
    return '''
//@version=5
strategy("Safe Strategy", overlay=true)

// 이전 봉 데이터만 사용
fast_ma = ta.sma(close[1], 10)
slow_ma = ta.sma(close[1], 20)

// 봉 완성 확인 후 신호
if barstate.isconfirmed
    if ta.crossover(fast_ma, slow_ma)
        strategy.entry("Long", strategy.long)
    if ta.crossunder(fast_ma, slow_ma)
        strategy.close("Long")

// 리스크 관리
strategy.exit("Exit", "Long", stop=close * 0.98, limit=close * 1.04)
'''


@pytest.fixture
def sample_pine_script_repainting():
    """리페인팅 위험이 높은 Pine Script"""
    return '''
//@version=5
strategy("Repainting Strategy", overlay=true)

// lookahead_on 사용 (치명적)
higher_tf_close = request.security(syminfo.tickerid, "D", close, lookahead=barmerge.lookahead_on)

// 실시간 바 상태 의존
if barstate.isrealtime
    plot(close, color=color.red)

// varip 사용
varip float last_signal = 0

// 현재 봉 종가 직접 사용
signal = close > ta.sma(close, 20)
'''


@pytest.fixture
def sample_pine_script_overfitting():
    """과적합 위험이 높은 Pine Script"""
    return '''
//@version=5
strategy("Overfitting Strategy", overlay=true)

// 과도한 파라미터 (21개)
len1 = input.int(14, "Length 1")
len2 = input.int(21, "Length 2")
len3 = input.int(7, "Length 3")
mult1 = input.float(2.0, "Multiplier 1")
mult2 = input.float(1.5, "Multiplier 2")
thresh1 = input.float(0.5, "Threshold 1")
thresh2 = input.float(0.3, "Threshold 2")
src = input.source(close, "Source")
tf = input.timeframe("", "Timeframe")
use_filter1 = input.bool(true, "Use Filter 1")
use_filter2 = input.bool(false, "Use Filter 2")
param11 = input.int(50, "Param 11")
param12 = input.int(100, "Param 12")
param13 = input.float(0.618, "Param 13")
param14 = input.float(1.272, "Param 14")
param15 = input.int(8, "Param 15")
param16 = input.int(13, "Param 16")
param17 = input.int(21, "Param 17")
param18 = input.float(2.618, "Param 18")
param19 = input.bool(true, "Param 19")
param20 = input.string("default", "Param 20")
param21 = input.int(34, "Param 21")

// 매직 넘버
magic_value = 1.23456789
special_ratio = 0.786543

// 하드코딩된 날짜
start_date = timestamp(2020, 3, 15)
if time > start_date
    if year == 2021 and month == 6
        strategy.entry("Long", strategy.long)
'''


@pytest.fixture
def sample_pine_script_no_risk_management():
    """리스크 관리가 없는 Pine Script"""
    return '''
//@version=5
strategy("No Risk Strategy", overlay=true)

ma = ta.sma(close[1], 20)

if barstate.isconfirmed
    if close[1] > ma
        strategy.entry("Long", strategy.long)
    else
        strategy.entry("Short", strategy.short)

// 스탑로스, 테이크프로핏 없음
'''


@pytest.fixture
def sample_pine_script_good_risk():
    """좋은 리스크 관리가 있는 Pine Script"""
    return '''
//@version=5
strategy("Good Risk Strategy", overlay=true)

// ATR 기반 동적 스탑
atr = ta.atr(14)
stop_loss = 2 * atr
take_profit = 3 * atr

ma = ta.sma(close[1], 20)

if barstate.isconfirmed and ta.crossover(close[1], ma)
    strategy.entry("Long", strategy.long)
    strategy.exit("Exit", "Long",
                  stop=close - stop_loss,
                  limit=close + take_profit,
                  trailing=atr)

// 포지션 사이징
position_size = strategy.equity * 0.02 / stop_loss
'''


@pytest.fixture
def sample_pine_script_simple():
    """간단한 Pine Script"""
    return '''
//@version=5
indicator("Simple MA", overlay=true)

length = input.int(20, "Length")
ma = ta.sma(close, length)
plot(ma)
'''


# ============================================================
# Mock Data Fixtures
# ============================================================

@pytest.fixture
def mock_strategy_meta():
    """전략 메타데이터 모킹"""
    return {
        "script_id": "test_123",
        "title": "Test Strategy",
        "author": "test_author",
        "script_url": "https://www.tradingview.com/script/test123/",
        "likes": 1500,
        "views": 50000,
        "description": "A test strategy for unit testing"
    }


@pytest.fixture
def mock_performance_good():
    """좋은 성과 지표"""
    return {
        "profit_factor": 1.8,
        "win_rate": 55,
        "total_trades": 500,
        "max_drawdown": 15.0,
        "net_profit": 25.5
    }


@pytest.fixture
def mock_performance_suspicious():
    """의심스러운 성과 지표 (과적합 의심)"""
    return {
        "profit_factor": 8.5,
        "win_rate": 92,
        "total_trades": 30,
        "max_drawdown": 2.0,
        "net_profit": 150.0
    }


# ============================================================
# Database Fixtures
# ============================================================

@pytest.fixture
def temp_db_path(tmp_path):
    """임시 데이터베이스 경로"""
    return str(tmp_path / "test_strategies.db")


# ============================================================
# Configuration Fixtures
# ============================================================

@pytest.fixture
def test_config():
    """테스트용 설정"""
    from src.config import Config

    return Config(
        db_path=":memory:",
        max_strategies=10,
        min_likes=100,
        headless=True,
        skip_llm=True,
        rate_limit_delay=0.1
    )
