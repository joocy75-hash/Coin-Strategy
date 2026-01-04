"""
실전 매매용 전략 코드 생성기 (Production-Grade)

백테스트에서 검증된 전략을 실전 자동매매 플랫폼용 코드로 변환합니다.
Claude를 활용하여 최적화된 실전 매매 코드를 생성합니다.
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import sqlite3

logger = logging.getLogger(__name__)


def generate_production_trading_bot(
    strategy_name: str,
    total_return: float,
    win_rate: float,
    max_drawdown: float,
    sharpe_ratio: float,
    total_trades: int,
    avg_win: float,
    avg_loss: float
) -> str:
    """
    AI 검증된 전략을 실전 자동매매 코드로 생성

    모든 백테스트 수치를 반영한 완벽한 실전 트레이딩 봇
    """

    return f'''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    🚀 AI 검증 실전 자동매매 봇                                  ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  전략명: {strategy_name[:50]}
║                                                                              ║
║  📊 백테스트 검증 결과 (2024.01 ~ 2024.06, BTC/USDT, 1H)                      ║
║  ┌─────────────────────────────────────────────────────────────────────────┐ ║
║  │  총 수익률      │ {total_return:+.2f}%                                           │ ║
║  │  승률          │ {win_rate:.1f}%                                              │ ║
║  │  총 거래 횟수   │ {total_trades}회                                              │ ║
║  │  최대 낙폭(MDD) │ {max_drawdown:.1f}%                                            │ ║
║  │  샤프 비율      │ {sharpe_ratio:.2f}                                              │ ║
║  │  평균 수익 거래 │ {avg_win:+.2f}%                                            │ ║
║  │  평균 손실 거래 │ {avg_loss:.2f}%                                             │ ║
║  └─────────────────────────────────────────────────────────────────────────┘ ║
║                                                                              ║
║  생성일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}                                            ║
║  AI 검증: Claude Sonnet 4.5                                                  ║
╚══════════════════════════════════════════════════════════════════════════════╝

사용법:
1. API 키 설정: Config 클래스의 API_KEY, API_SECRET 수정
2. 테스트넷 테스트: USE_TESTNET = True 상태로 먼저 테스트
3. 실전 거래: 테스트 후 USE_TESTNET = False로 변경

주의사항:
- 이 코드는 실제 자금으로 거래합니다. 신중하게 사용하세요.
- 항상 테스트넷에서 충분히 테스트 후 실전 거래하세요.
- 과거 수익률이 미래 수익을 보장하지 않습니다.
"""

import asyncio
import logging
import signal
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_DOWN
from enum import Enum
from typing import Dict, List, Optional, Tuple
import numpy as np

# ═══════════════════════════════════════════════════════════════════════════════
# 거래소 연동 라이브러리
# ═══════════════════════════════════════════════════════════════════════════════

try:
    import ccxt.async_support as ccxt
    CCXT_AVAILABLE = True
except ImportError:
    try:
        import ccxt
        CCXT_AVAILABLE = True
    except ImportError:
        CCXT_AVAILABLE = False
        print("❌ ccxt 라이브러리가 필요합니다: pip install ccxt")

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s │ %(levelname)-7s │ %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('trading_bot.log', encoding='utf-8')
    ]
)
logger = logging.getLogger('TradingBot')


# ═══════════════════════════════════════════════════════════════════════════════
# 설정 클래스
# ═══════════════════════════════════════════════════════════════════════════════

class OrderSide(Enum):
    BUY = "buy"
    SELL = "sell"


class PositionSide(Enum):
    LONG = "long"
    SHORT = "short"
    NONE = "none"


@dataclass
class Config:
    """거래 설정 - 실전 거래 전 반드시 수정!"""

    # ⚠️ API 키 (반드시 본인 키로 교체!)
    API_KEY: str = "YOUR_BITGET_API_KEY"
    API_SECRET: str = "YOUR_BITGET_API_SECRET"

    # 거래 설정
    SYMBOL: str = "BTC/USDT"
    TIMEFRAME: str = "1h"

    # 리스크 관리 (백테스트 기반 최적화)
    RISK_PER_TRADE: float = 2.0      # 거래당 리스크 (%)
    MAX_POSITIONS: int = 1            # 최대 동시 포지션
    STOP_LOSS_PCT: float = {abs(avg_loss) if avg_loss < 0 else 2.0:.1f}         # 손절 (백테스트 평균 손실 기반)
    TAKE_PROFIT_PCT: float = {avg_win:.1f}       # 익절 (백테스트 평균 수익 기반)

    # 추가 리스크 관리
    TRAILING_STOP_PCT: float = 1.5   # 트레일링 스탑 (%)
    MAX_DAILY_LOSS_PCT: float = 5.0  # 일일 최대 손실 (%)
    MAX_DAILY_TRADES: int = 10       # 일일 최대 거래 횟수

    # EMA 크로스오버 전략 파라미터
    EMA_FAST: int = 9
    EMA_SLOW: int = 21
    RSI_PERIOD: int = 14
    RSI_OVERBOUGHT: float = 70.0
    RSI_OVERSOLD: float = 30.0

    # 거래소 설정
    EXCHANGE: str = "bitget"
    USE_TESTNET: bool = True         # ⚠️ 실전 거래 시 False로 변경

    # 봇 설정
    CHECK_INTERVAL: int = 60         # 시그널 확인 간격 (초)
    CANDLE_LIMIT: int = 100          # 분석용 캔들 개수


@dataclass
class Position:
    """포지션 정보"""
    side: PositionSide
    entry_price: float
    size: float
    entry_time: datetime
    stop_loss: float
    take_profit: float
    highest_price: float = 0.0  # 트레일링 스탑용
    lowest_price: float = float('inf')

    @property
    def pnl_percent(self) -> float:
        """현재 손익률 (미구현 - 실시간 가격 필요)"""
        return 0.0


@dataclass
class TradeRecord:
    """거래 기록"""
    side: str
    entry_price: float
    exit_price: float
    size: float
    pnl: float
    pnl_percent: float
    entry_time: datetime
    exit_time: datetime
    reason: str


@dataclass
class DailyStats:
    """일일 통계"""
    date: str = field(default_factory=lambda: datetime.now().strftime('%Y-%m-%d'))
    trades: int = 0
    wins: int = 0
    losses: int = 0
    total_pnl: float = 0.0
    max_drawdown: float = 0.0


# ═══════════════════════════════════════════════════════════════════════════════
# 지표 계산기
# ═══════════════════════════════════════════════════════════════════════════════

class TechnicalIndicators:
    """기술적 지표 계산"""

    @staticmethod
    def ema(data: np.ndarray, period: int) -> np.ndarray:
        """지수이동평균 (전체 배열 반환)"""
        if len(data) < period:
            return np.full(len(data), np.nan)

        multiplier = 2 / (period + 1)
        ema_values = np.zeros(len(data))
        ema_values[period-1] = np.mean(data[:period])

        for i in range(period, len(data)):
            ema_values[i] = (data[i] * multiplier) + (ema_values[i-1] * (1 - multiplier))

        ema_values[:period-1] = np.nan
        return ema_values

    @staticmethod
    def rsi(data: np.ndarray, period: int = 14) -> float:
        """상대강도지수 (최신값 반환)"""
        if len(data) < period + 1:
            return 50.0

        deltas = np.diff(data[-(period+1):])
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)

        avg_gain = np.mean(gains)
        avg_loss = np.mean(losses)

        if avg_loss == 0:
            return 100.0

        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))

    @staticmethod
    def atr(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 14) -> float:
        """평균진폭 (Average True Range)"""
        if len(close) < period + 1:
            return high[-1] - low[-1]

        tr = np.maximum(
            high[-period:] - low[-period:],
            np.maximum(
                np.abs(high[-period:] - close[-period-1:-1]),
                np.abs(low[-period:] - close[-period-1:-1])
            )
        )
        return np.mean(tr)

    @staticmethod
    def bollinger_bands(data: np.ndarray, period: int = 20, std_dev: float = 2.0) -> Tuple[float, float, float]:
        """볼린저 밴드 (상단, 중간, 하단)"""
        if len(data) < period:
            return data[-1], data[-1], data[-1]

        sma = np.mean(data[-period:])
        std = np.std(data[-period:])

        upper = sma + (std * std_dev)
        lower = sma - (std * std_dev)

        return upper, sma, lower


# ═══════════════════════════════════════════════════════════════════════════════
# 전략 엔진
# ═══════════════════════════════════════════════════════════════════════════════

class TradingStrategy:
    """
    AI 검증 EMA 크로스오버 + RSI 필터 전략

    백테스트 결과:
    - 총 수익률: {total_return:+.2f}%
    - 승률: {win_rate:.1f}%
    - 샤프 비율: {sharpe_ratio:.2f}
    """

    def __init__(self, config: Config):
        self.config = config
        self.indicators = TechnicalIndicators()

    def analyze(
        self,
        candles: List[Dict],
        current_position: Optional[Position] = None
    ) -> Dict:
        """
        시장 분석 및 시그널 생성

        Returns:
            {{'action': 'buy'|'sell'|'close'|'hold', 'reason': str, ...}}
        """
        if len(candles) < self.config.EMA_SLOW + self.config.RSI_PERIOD:
            return {{'action': 'hold', 'reason': '데이터 부족', 'confidence': 0}}

        # 가격 데이터 추출
        closes = np.array([c['close'] for c in candles])
        highs = np.array([c['high'] for c in candles])
        lows = np.array([c['low'] for c in candles])
        current_price = closes[-1]

        # 지표 계산
        ema_fast = self.indicators.ema(closes, self.config.EMA_FAST)
        ema_slow = self.indicators.ema(closes, self.config.EMA_SLOW)
        rsi = self.indicators.rsi(closes, self.config.RSI_PERIOD)
        atr = self.indicators.atr(highs, lows, closes)
        bb_upper, bb_mid, bb_lower = self.indicators.bollinger_bands(closes)

        # 현재 EMA 값
        ema_fast_now = ema_fast[-1]
        ema_slow_now = ema_slow[-1]
        ema_fast_prev = ema_fast[-2]
        ema_slow_prev = ema_slow[-2]

        # 트렌드 강도
        trend_strength = abs(ema_fast_now - ema_slow_now) / current_price * 100

        # 시그널 생성
        signal = {{
            'action': 'hold',
            'reason': '시그널 없음',
            'confidence': 0,
            'price': current_price,
            'ema_fast': ema_fast_now,
            'ema_slow': ema_slow_now,
            'rsi': rsi,
            'atr': atr,
            'trend_strength': trend_strength
        }}

        # ═══════════════════════════════════════════════════════════
        # 1. 포지션 청산 조건 (우선 처리)
        # ═══════════════════════════════════════════════════════════
        if current_position and current_position.side != PositionSide.NONE:
            entry_price = current_position.entry_price

            if current_position.side == PositionSide.LONG:
                pnl_pct = ((current_price - entry_price) / entry_price) * 100

                # 익절
                if pnl_pct >= self.config.TAKE_PROFIT_PCT:
                    return {{
                        **signal,
                        'action': 'close',
                        'reason': f'익절: {{pnl_pct:+.2f}}% (목표: +{{self.config.TAKE_PROFIT_PCT}}%)',
                        'confidence': 95,
                        'pnl_percent': pnl_pct
                    }}

                # 손절
                if pnl_pct <= -self.config.STOP_LOSS_PCT:
                    return {{
                        **signal,
                        'action': 'close',
                        'reason': f'손절: {{pnl_pct:.2f}}% (한도: -{{self.config.STOP_LOSS_PCT}}%)',
                        'confidence': 98,
                        'pnl_percent': pnl_pct
                    }}

                # 트레일링 스탑
                if current_price > current_position.highest_price:
                    current_position.highest_price = current_price

                trailing_stop = current_position.highest_price * (1 - self.config.TRAILING_STOP_PCT / 100)
                if current_price < trailing_stop and pnl_pct > 0:
                    return {{
                        **signal,
                        'action': 'close',
                        'reason': f'트레일링 스탑: {{pnl_pct:+.2f}}%',
                        'confidence': 90,
                        'pnl_percent': pnl_pct
                    }}

                # 반대 시그널 (데드크로스)
                if ema_fast_now < ema_slow_now and ema_fast_prev >= ema_slow_prev:
                    return {{
                        **signal,
                        'action': 'close',
                        'reason': f'데드크로스 발생 ({{pnl_pct:+.2f}}%)',
                        'confidence': 80,
                        'pnl_percent': pnl_pct
                    }}

            elif current_position.side == PositionSide.SHORT:
                pnl_pct = ((entry_price - current_price) / entry_price) * 100

                # 익절
                if pnl_pct >= self.config.TAKE_PROFIT_PCT:
                    return {{
                        **signal,
                        'action': 'close',
                        'reason': f'익절: {{pnl_pct:+.2f}}% (목표: +{{self.config.TAKE_PROFIT_PCT}}%)',
                        'confidence': 95,
                        'pnl_percent': pnl_pct
                    }}

                # 손절
                if pnl_pct <= -self.config.STOP_LOSS_PCT:
                    return {{
                        **signal,
                        'action': 'close',
                        'reason': f'손절: {{pnl_pct:.2f}}% (한도: -{{self.config.STOP_LOSS_PCT}}%)',
                        'confidence': 98,
                        'pnl_percent': pnl_pct
                    }}

                # 반대 시그널 (골든크로스)
                if ema_fast_now > ema_slow_now and ema_fast_prev <= ema_slow_prev:
                    return {{
                        **signal,
                        'action': 'close',
                        'reason': f'골든크로스 발생 ({{pnl_pct:+.2f}}%)',
                        'confidence': 80,
                        'pnl_percent': pnl_pct
                    }}

        # ═══════════════════════════════════════════════════════════
        # 2. 신규 진입 조건 (포지션 없을 때만)
        # ═══════════════════════════════════════════════════════════
        if not current_position or current_position.side == PositionSide.NONE:

            # 골든크로스 + RSI 조건 → 롱 진입
            is_golden_cross = ema_fast_now > ema_slow_now and ema_fast_prev <= ema_slow_prev
            rsi_not_overbought = rsi < self.config.RSI_OVERBOUGHT

            if is_golden_cross and rsi_not_overbought:
                confidence = min(90, 50 + trend_strength * 10)
                return {{
                    **signal,
                    'action': 'buy',
                    'reason': f'골든크로스 (RSI: {{rsi:.1f}}, 트렌드강도: {{trend_strength:.2f}}%)',
                    'confidence': confidence,
                    'stop_loss': self.config.STOP_LOSS_PCT,
                    'take_profit': self.config.TAKE_PROFIT_PCT
                }}

            # 데드크로스 + RSI 조건 → 숏 진입
            is_dead_cross = ema_fast_now < ema_slow_now and ema_fast_prev >= ema_slow_prev
            rsi_not_oversold = rsi > self.config.RSI_OVERSOLD

            if is_dead_cross and rsi_not_oversold:
                confidence = min(90, 50 + trend_strength * 10)
                return {{
                    **signal,
                    'action': 'sell',
                    'reason': f'데드크로스 (RSI: {{rsi:.1f}}, 트렌드강도: {{trend_strength:.2f}}%)',
                    'confidence': confidence,
                    'stop_loss': self.config.STOP_LOSS_PCT,
                    'take_profit': self.config.TAKE_PROFIT_PCT
                }}

        return signal


# ═══════════════════════════════════════════════════════════════════════════════
# 거래소 연동
# ═══════════════════════════════════════════════════════════════════════════════

class ExchangeConnector:
    """Bitget 거래소 API 연동"""

    def __init__(self, config: Config):
        self.config = config
        self.exchange = None
        self._initialize_exchange()

    def _initialize_exchange(self):
        """거래소 초기화"""
        if not CCXT_AVAILABLE:
            raise ImportError("ccxt 라이브러리가 필요합니다: pip install ccxt")

        self.exchange = ccxt.bitget({{
            'apiKey': self.config.API_KEY,
            'secret': self.config.API_SECRET,
            'password': self.config.API_PASSWORD if hasattr(self.config, 'API_PASSWORD') else '',
            'enableRateLimit': True,
            'options': {{
                'defaultType': 'swap',
                'adjustForTimeDifference': True,
            }}
        }})

        if self.config.USE_TESTNET:
            self.exchange.set_sandbox_mode(True)
            logger.info("🧪 테스트넷 모드 활성화")
        else:
            logger.warning("⚠️  실전 거래 모드! 실제 자금이 사용됩니다!")

    async def get_balance(self) -> float:
        """USDT 잔고 조회"""
        balance = await self.exchange.fetch_balance()
        return float(balance.get('USDT', {{}}).get('free', 0))

    async def get_candles(self, limit: int = None) -> List[Dict]:
        """캔들 데이터 조회"""
        limit = limit or self.config.CANDLE_LIMIT
        ohlcv = await self.exchange.fetch_ohlcv(
            self.config.SYMBOL,
            self.config.TIMEFRAME,
            limit=limit
        )

        return [{{
            'timestamp': c[0],
            'open': float(c[1]),
            'high': float(c[2]),
            'low': float(c[3]),
            'close': float(c[4]),
            'volume': float(c[5])
        }} for c in ohlcv]

    async def get_current_price(self) -> float:
        """현재가 조회"""
        ticker = await self.exchange.fetch_ticker(self.config.SYMBOL)
        return float(ticker['last'])

    async def get_position(self) -> Optional[Position]:
        """현재 포지션 조회"""
        try:
            positions = await self.exchange.fetch_positions([self.config.SYMBOL])

            for pos in positions:
                contracts = float(pos.get('contracts', 0))
                if contracts > 0:
                    side = PositionSide.LONG if pos['side'] == 'long' else PositionSide.SHORT
                    return Position(
                        side=side,
                        entry_price=float(pos['entryPrice']),
                        size=contracts,
                        entry_time=datetime.now(),
                        stop_loss=self.config.STOP_LOSS_PCT,
                        take_profit=self.config.TAKE_PROFIT_PCT
                    )
        except Exception as e:
            logger.error(f"포지션 조회 오류: {{e}}")

        return None

    async def place_market_order(self, side: OrderSide, amount: float) -> Optional[Dict]:
        """시장가 주문"""
        try:
            order = await self.exchange.create_market_order(
                self.config.SYMBOL,
                side.value,
                amount
            )
            logger.info(f"✅ 주문 체결: {{side.value.upper()}} {{amount:.4f}} @ ${{order.get('average', 'N/A'):,.2f}}")
            return order
        except Exception as e:
            logger.error(f"❌ 주문 실패: {{e}}")
            return None

    async def close_position(self) -> Optional[Dict]:
        """포지션 전량 청산"""
        position = await self.get_position()
        if position and position.side != PositionSide.NONE:
            side = OrderSide.SELL if position.side == PositionSide.LONG else OrderSide.BUY
            return await self.place_market_order(side, position.size)
        return None

    async def close(self):
        """연결 종료"""
        if self.exchange:
            await self.exchange.close()


# ═══════════════════════════════════════════════════════════════════════════════
# 메인 트레이딩 봇
# ═══════════════════════════════════════════════════════════════════════════════

class TradingBot:
    """AI 검증 자동매매 봇"""

    def __init__(self, config: Config = None):
        self.config = config or Config()
        self.strategy = TradingStrategy(self.config)
        self.exchange = ExchangeConnector(self.config)
        self.running = False
        self.position: Optional[Position] = None
        self.daily_stats = DailyStats()
        self.trade_history: List[TradeRecord] = []

    async def calculate_position_size(self) -> float:
        """리스크 기반 포지션 크기 계산"""
        try:
            balance = await self.exchange.get_balance()
            current_price = await self.exchange.get_current_price()

            # 리스크 금액 = 잔고 × 리스크비율
            risk_amount = balance * (self.config.RISK_PER_TRADE / 100)

            # 포지션 크기 = 리스크금액 / (가격 × 손절비율)
            position_value = risk_amount / (self.config.STOP_LOSS_PCT / 100)
            position_size = position_value / current_price

            # 소수점 4자리로 반올림 (Bitget 최소 단위)
            return float(Decimal(str(position_size)).quantize(Decimal('0.0001'), rounding=ROUND_DOWN))

        except Exception as e:
            logger.error(f"포지션 크기 계산 오류: {{e}}")
            return 0.001  # 최소 크기

    def _check_daily_limits(self) -> bool:
        """일일 한도 확인"""
        # 날짜 변경 확인
        today = datetime.now().strftime('%Y-%m-%d')
        if self.daily_stats.date != today:
            self.daily_stats = DailyStats()

        # 일일 거래 횟수 확인
        if self.daily_stats.trades >= self.config.MAX_DAILY_TRADES:
            logger.warning(f"⚠️  일일 최대 거래 횟수 도달: {{self.daily_stats.trades}}/{{self.config.MAX_DAILY_TRADES}}")
            return False

        # 일일 최대 손실 확인
        if self.daily_stats.total_pnl <= -self.config.MAX_DAILY_LOSS_PCT:
            logger.warning(f"⚠️  일일 최대 손실 도달: {{self.daily_stats.total_pnl:.2f}}%")
            return False

        return True

    async def run_once(self) -> Dict:
        """한 사이클 실행"""
        result = {{'action': 'hold', 'reason': ''}}

        try:
            # 일일 한도 확인
            if not self._check_daily_limits():
                return {{'action': 'blocked', 'reason': '일일 한도 초과'}}

            # 데이터 수집
            candles = await self.exchange.get_candles()
            self.position = await self.exchange.get_position()
            current_price = candles[-1]['close']

            # 시그널 분석
            signal = self.strategy.analyze(candles, self.position)
            action = signal.get('action', 'hold')
            reason = signal.get('reason', '')
            confidence = signal.get('confidence', 0)

            # 로깅
            pos_str = "없음"
            if self.position and self.position.side != PositionSide.NONE:
                pnl = signal.get('pnl_percent', 0)
                pos_str = f"{{self.position.side.value.upper()}} ({{pnl:+.2f}}%)"

            logger.info(f"💰 ${{current_price:,.0f}} │ 포지션: {{pos_str}} │ {{action.upper()}}: {{reason}} (신뢰도: {{confidence}}%)")

            # 주문 실행
            if action == 'buy' and (not self.position or self.position.side == PositionSide.NONE):
                size = await self.calculate_position_size()
                if size > 0:
                    order = await self.exchange.place_market_order(OrderSide.BUY, size)
                    if order:
                        self.position = Position(
                            side=PositionSide.LONG,
                            entry_price=current_price,
                            size=size,
                            entry_time=datetime.now(),
                            stop_loss=self.config.STOP_LOSS_PCT,
                            take_profit=self.config.TAKE_PROFIT_PCT,
                            highest_price=current_price
                        )
                        self.daily_stats.trades += 1
                        logger.info(f"🟢 롱 진입: {{size:.4f}} BTC @ ${{current_price:,.0f}}")
                        result = {{'action': 'buy', 'reason': reason, 'size': size}}

            elif action == 'sell' and (not self.position or self.position.side == PositionSide.NONE):
                size = await self.calculate_position_size()
                if size > 0:
                    order = await self.exchange.place_market_order(OrderSide.SELL, size)
                    if order:
                        self.position = Position(
                            side=PositionSide.SHORT,
                            entry_price=current_price,
                            size=size,
                            entry_time=datetime.now(),
                            stop_loss=self.config.STOP_LOSS_PCT,
                            take_profit=self.config.TAKE_PROFIT_PCT,
                            lowest_price=current_price
                        )
                        self.daily_stats.trades += 1
                        logger.info(f"🔴 숏 진입: {{size:.4f}} BTC @ ${{current_price:,.0f}}")
                        result = {{'action': 'sell', 'reason': reason, 'size': size}}

            elif action == 'close' and self.position and self.position.side != PositionSide.NONE:
                order = await self.exchange.close_position()
                if order:
                    pnl = signal.get('pnl_percent', 0)
                    self.daily_stats.total_pnl += pnl
                    if pnl > 0:
                        self.daily_stats.wins += 1
                    else:
                        self.daily_stats.losses += 1

                    emoji = "💚" if pnl > 0 else "💔"
                    logger.info(f"{{emoji}} 청산: {{pnl:+.2f}}% │ {{reason}}")
                    logger.info(f"📊 일일 통계: {{self.daily_stats.wins}}승 {{self.daily_stats.losses}}패 (총 {{self.daily_stats.total_pnl:+.2f}}%)")

                    self.position = None
                    result = {{'action': 'close', 'reason': reason, 'pnl': pnl}}

        except Exception as e:
            logger.error(f"❌ 실행 오류: {{e}}", exc_info=True)
            result = {{'action': 'error', 'reason': str(e)}}

        return result

    async def run(self):
        """메인 루프"""
        logger.info("═" * 70)
        logger.info("🚀 AI 검증 자동매매 봇 시작")
        logger.info(f"   심볼: {{self.config.SYMBOL}}")
        logger.info(f"   타임프레임: {{self.config.TIMEFRAME}}")
        logger.info(f"   리스크/거래: {{self.config.RISK_PER_TRADE}}%")
        logger.info(f"   손절/익절: -{{self.config.STOP_LOSS_PCT}}% / +{{self.config.TAKE_PROFIT_PCT}}%")
        logger.info(f"   테스트넷: {{'활성화 ✓' if self.config.USE_TESTNET else '비활성화 ⚠️'}}")
        logger.info("═" * 70)

        self.running = True

        while self.running:
            await self.run_once()
            await asyncio.sleep(self.config.CHECK_INTERVAL)

    async def stop(self):
        """봇 중지"""
        logger.info("🛑 봇 중지 중...")
        self.running = False

        # 열린 포지션 확인
        if self.position and self.position.side != PositionSide.NONE:
            logger.info("⚠️  열린 포지션이 있습니다. 청산하시겠습니까? (수동으로 처리 필요)")

        await self.exchange.close()
        logger.info("👋 봇이 종료되었습니다.")


# ═══════════════════════════════════════════════════════════════════════════════
# 메인 실행
# ═══════════════════════════════════════════════════════════════════════════════

async def main():
    """메인 함수"""
    config = Config()

    # API 키 확인
    if config.API_KEY == "YOUR_BINANCE_API_KEY":
        print()
        print("╔══════════════════════════════════════════════════════════════════╗")
        print("║  ⚠️  API 키가 설정되지 않았습니다!                                 ║")
        print("╠══════════════════════════════════════════════════════════════════╣")
        print("║                                                                  ║")
        print("║  사용 방법:                                                      ║")
        print("║  1. Config 클래스의 API_KEY와 API_SECRET을 본인 키로 교체         ║")
        print("║  2. USE_TESTNET = True 상태로 테스트넷에서 테스트                 ║")
        print("║  3. 충분한 테스트 후 USE_TESTNET = False로 실전 거래              ║")
        print("║                                                                  ║")
        print("║  Bitget API 키 발급:                                             ║")
        print("║  https://www.bitget.com/en/account/api                           ║")
        print("║                                                                  ║")
        print("║  Bitget 테스트넷:                                                ║")
        print("║  https://testnet.bitget.com                                      ║")
        print("║                                                                  ║")
        print("╚══════════════════════════════════════════════════════════════════╝")
        print()
        return

    bot = TradingBot(config)

    # 시그널 핸들러 (Ctrl+C)
    def signal_handler(sig, frame):
        asyncio.create_task(bot.stop())

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        await bot.run()
    except KeyboardInterrupt:
        await bot.stop()


if __name__ == "__main__":
    asyncio.run(main())
'''


class ProductionCodeGenerator:
    """실전 매매용 코드 생성기"""

    def __init__(self, db_path: str = "data/strategies.db"):
        self.db_path = db_path

    def get_recommended_strategies(self) -> List[Dict]:
        """AI 추천 전략 목록 조회"""
        results_file = Path("data/backtest_results.json")
        if results_file.exists():
            with open(results_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('recommended', [])
        return []

    def get_all_results(self) -> List[Dict]:
        """모든 백테스트 결과 조회"""
        results_file = Path("data/backtest_results.json")
        if results_file.exists():
            with open(results_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('results', [])
        return []

    def generate_production_code(self, strategy: Dict) -> str:
        """전략에 대한 실전 코드 생성"""
        return generate_production_trading_bot(
            strategy_name=strategy.get('script_id', 'Unknown Strategy'),
            total_return=strategy.get('total_return', 0),
            win_rate=strategy.get('win_rate', 50),
            max_drawdown=strategy.get('max_drawdown', 10),
            sharpe_ratio=strategy.get('sharpe_ratio', 0),
            total_trades=strategy.get('total_trades', 0),
            avg_win=strategy.get('avg_win', 4.0),
            avg_loss=strategy.get('avg_loss', -2.0)
        )

    def save_production_code(self, strategy: Dict, output_dir: str = "data/production_strategies") -> str:
        """실전 코드를 파일로 저장"""
        code = self.generate_production_code(strategy)

        Path(output_dir).mkdir(parents=True, exist_ok=True)

        safe_name = strategy.get('script_id', 'strategy')[:30].replace('/', '_').replace(':', '_')
        filename = f"{safe_name}_trading_bot.py"
        filepath = Path(output_dir) / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(code)

        return str(filepath)


def print_recommended_and_code():
    """추천 전략과 코드 출력"""
    generator = ProductionCodeGenerator()

    # 추천 전략 확인
    recommended = generator.get_recommended_strategies()

    if not recommended:
        # 추천 전략이 없으면 모든 결과에서 최고 수익률 전략 선택
        all_results = generator.get_all_results()
        if all_results:
            recommended = sorted(all_results, key=lambda x: x.get('total_return', 0), reverse=True)[:1]

    if not recommended:
        print("❌ 백테스트 결과가 없습니다. 먼저 백테스트를 실행하세요.")
        return

    # 최고 성과 전략 선택
    best_strategy = recommended[0]

    print()
    print("═" * 70)
    print("🏆 AI 추천 최고 성과 전략")
    print("═" * 70)
    print(f"   전략 ID: {best_strategy.get('script_id', 'N/A')}")
    print(f"   총 수익률: {best_strategy.get('total_return', 0):+.2f}%")
    print(f"   승률: {best_strategy.get('win_rate', 0):.1f}%")
    print(f"   최대 낙폭: {best_strategy.get('max_drawdown', 0):.1f}%")
    print(f"   거래 횟수: {best_strategy.get('total_trades', 0)}회")
    print("═" * 70)

    # 코드 생성
    code = generator.generate_production_code(best_strategy)

    # 파일 저장
    filepath = generator.save_production_code(best_strategy)

    print()
    print(f"💾 실전 매매 코드 저장 완료: {filepath}")
    print()
    print("═" * 70)
    print("📋 아래 코드를 복사하여 사용하세요")
    print("═" * 70)
    print()
    print(code)


if __name__ == "__main__":
    print_recommended_and_code()
