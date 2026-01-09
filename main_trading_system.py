#!/usr/bin/env python3
"""
AI 검증 자동매매 멀티봇 시스템
- Strategy Research Lab API에서 검증된 B등급 이상 전략 자동 로드
- 다중 심볼 동시 매매 지원
- Binance Testnet/Mainnet 지원
"""

import asyncio
import logging
import os
import signal
import sys
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal, ROUND_DOWN
from enum import Enum
from typing import Dict, List, Optional
import requests
import numpy as np

try:
    import ccxt.async_support as ccxt
    CCXT_AVAILABLE = True
except ImportError:
    CCXT_AVAILABLE = False
    print("ccxt 라이브러리가 필요합니다: pip install ccxt")

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-7s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('multi_trading_bot.log', encoding='utf-8')
    ]
)
logger = logging.getLogger('MultiBotSystem')


class OrderSide(Enum):
    BUY = "buy"
    SELL = "sell"


class PositionSide(Enum):
    LONG = "long"
    SHORT = "short"
    NONE = "none"


@dataclass
class Config:
    """시스템 설정"""
    # API 설정
    STRATEGY_API_URL: str = "http://141.164.55.245/api"
    MIN_GRADE: str = "B"
    MIN_SCORE: float = 70.0

    # Binance API (환경변수에서 로드)
    API_KEY: str = field(default_factory=lambda: os.getenv('BINANCE_API_KEY', ''))
    API_SECRET: str = field(default_factory=lambda: os.getenv('BINANCE_API_SECRET', ''))

    # 거래 설정
    SYMBOLS: List[str] = field(default_factory=lambda: ['BTC/USDT', 'ETH/USDT', 'SOL/USDT'])
    TIMEFRAME: str = "1h"
    USE_TESTNET: bool = field(default_factory=lambda: os.getenv('USE_TESTNET', 'true').lower() == 'true')
    PAPER_TRADING: bool = field(default_factory=lambda: os.getenv('PAPER_TRADING', 'false').lower() == 'true')

    # 리스크 관리
    RISK_PER_TRADE: float = 1.0
    MAX_POSITIONS: int = 3
    STOP_LOSS_PCT: float = 2.0
    TAKE_PROFIT_PCT: float = 4.0
    TRAILING_STOP_PCT: float = 1.5
    MAX_DAILY_LOSS_PCT: float = 5.0
    MAX_DAILY_TRADES: int = 10

    # EMA 전략 파라미터
    EMA_FAST: int = 9
    EMA_SLOW: int = 21
    RSI_PERIOD: int = 14
    RSI_OVERBOUGHT: float = 70.0
    RSI_OVERSOLD: float = 30.0

    # 봇 설정
    CHECK_INTERVAL: int = 60
    CANDLE_LIMIT: int = 100

    # 텔레그램 알림
    TELEGRAM_BOT_TOKEN: str = field(default_factory=lambda: os.getenv('TELEGRAM_BOT_TOKEN', ''))
    TELEGRAM_CHAT_ID: str = field(default_factory=lambda: os.getenv('TELEGRAM_CHAT_ID', ''))


@dataclass
class Position:
    """포지션 정보"""
    symbol: str
    side: PositionSide
    entry_price: float
    size: float
    entry_time: datetime
    stop_loss: float
    take_profit: float
    highest_price: float = 0.0
    lowest_price: float = float('inf')
    strategy_name: str = ""


@dataclass
class DailyStats:
    """일일 통계"""
    date: str = field(default_factory=lambda: datetime.now().strftime('%Y-%m-%d'))
    trades: int = 0
    wins: int = 0
    losses: int = 0
    total_pnl: float = 0.0


class StrategyFetcher:
    """Strategy Research Lab API에서 검증된 전략 가져오기"""

    def __init__(self, config: Config):
        self.config = config
        self.base_url = config.STRATEGY_API_URL

    def fetch_verified_strategies(self, limit: int = 10) -> List[Dict]:
        """B등급 이상 검증된 전략 목록 조회"""
        try:
            url = f"{self.base_url}/strategies"
            params = {
                'grade': self.config.MIN_GRADE,
                'limit': limit,
                'sort': 'total_score',
                'order': 'desc'
            }
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            strategies = response.json()

            # 최소 점수 필터링
            verified = [s for s in strategies if s.get('total_score', 0) >= self.config.MIN_SCORE]
            logger.info(f"검증된 전략 {len(verified)}개 로드 완료")
            return verified

        except Exception as e:
            logger.error(f"전략 조회 실패: {e}")
            return []

    def get_api_stats(self) -> Dict:
        """API 통계 조회"""
        try:
            response = requests.get(f"{self.base_url}/stats", timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"통계 조회 실패: {e}")
            return {}


class TechnicalIndicators:
    """기술적 지표 계산"""

    @staticmethod
    def ema(data: np.ndarray, period: int) -> np.ndarray:
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


class TradingStrategy:
    """EMA 크로스오버 + RSI 필터 전략"""

    def __init__(self, config: Config):
        self.config = config
        self.indicators = TechnicalIndicators()

    def analyze(self, candles: List[Dict], current_position: Optional[Position] = None) -> Dict:
        if len(candles) < self.config.EMA_SLOW + self.config.RSI_PERIOD:
            return {'action': 'hold', 'reason': '데이터 부족', 'confidence': 0}

        closes = np.array([c['close'] for c in candles])
        current_price = closes[-1]

        ema_fast = self.indicators.ema(closes, self.config.EMA_FAST)
        ema_slow = self.indicators.ema(closes, self.config.EMA_SLOW)
        rsi = self.indicators.rsi(closes, self.config.RSI_PERIOD)

        ema_fast_now, ema_slow_now = ema_fast[-1], ema_slow[-1]
        ema_fast_prev, ema_slow_prev = ema_fast[-2], ema_slow[-2]
        trend_strength = abs(ema_fast_now - ema_slow_now) / current_price * 100

        signal = {
            'action': 'hold', 'reason': '시그널 없음', 'confidence': 0,
            'price': current_price, 'rsi': rsi, 'trend_strength': trend_strength
        }

        # 포지션 청산 조건
        if current_position and current_position.side != PositionSide.NONE:
            entry_price = current_position.entry_price

            if current_position.side == PositionSide.LONG:
                pnl_pct = ((current_price - entry_price) / entry_price) * 100

                if pnl_pct >= self.config.TAKE_PROFIT_PCT:
                    return {**signal, 'action': 'close', 'reason': f'익절 +{pnl_pct:.2f}%', 'confidence': 95, 'pnl_percent': pnl_pct}
                if pnl_pct <= -self.config.STOP_LOSS_PCT:
                    return {**signal, 'action': 'close', 'reason': f'손절 {pnl_pct:.2f}%', 'confidence': 98, 'pnl_percent': pnl_pct}
                if ema_fast_now < ema_slow_now and ema_fast_prev >= ema_slow_prev:
                    return {**signal, 'action': 'close', 'reason': f'데드크로스 ({pnl_pct:+.2f}%)', 'confidence': 80, 'pnl_percent': pnl_pct}

            elif current_position.side == PositionSide.SHORT:
                pnl_pct = ((entry_price - current_price) / entry_price) * 100

                if pnl_pct >= self.config.TAKE_PROFIT_PCT:
                    return {**signal, 'action': 'close', 'reason': f'익절 +{pnl_pct:.2f}%', 'confidence': 95, 'pnl_percent': pnl_pct}
                if pnl_pct <= -self.config.STOP_LOSS_PCT:
                    return {**signal, 'action': 'close', 'reason': f'손절 {pnl_pct:.2f}%', 'confidence': 98, 'pnl_percent': pnl_pct}
                if ema_fast_now > ema_slow_now and ema_fast_prev <= ema_slow_prev:
                    return {**signal, 'action': 'close', 'reason': f'골든크로스 ({pnl_pct:+.2f}%)', 'confidence': 80, 'pnl_percent': pnl_pct}

        # 신규 진입 조건
        if not current_position or current_position.side == PositionSide.NONE:
            is_golden_cross = ema_fast_now > ema_slow_now and ema_fast_prev <= ema_slow_prev
            is_dead_cross = ema_fast_now < ema_slow_now and ema_fast_prev >= ema_slow_prev

            if is_golden_cross and rsi < self.config.RSI_OVERBOUGHT:
                confidence = min(90, 50 + trend_strength * 10)
                return {**signal, 'action': 'buy', 'reason': f'골든크로스 (RSI:{rsi:.1f})', 'confidence': confidence}

            if is_dead_cross and rsi > self.config.RSI_OVERSOLD:
                confidence = min(90, 50 + trend_strength * 10)
                return {**signal, 'action': 'sell', 'reason': f'데드크로스 (RSI:{rsi:.1f})', 'confidence': confidence}

        return signal


class TelegramNotifier:
    """텔레그램 알림"""

    def __init__(self, config: Config):
        self.token = config.TELEGRAM_BOT_TOKEN
        self.chat_id = config.TELEGRAM_CHAT_ID
        self.enabled = bool(self.token and self.chat_id)

    async def send(self, message: str):
        if not self.enabled:
            return
        try:
            url = f"https://api.telegram.org/bot{self.token}/sendMessage"
            data = {'chat_id': self.chat_id, 'text': message, 'parse_mode': 'HTML'}
            requests.post(url, data=data, timeout=10)
        except Exception as e:
            logger.error(f"텔레그램 전송 실패: {e}")


class ExchangeConnector:
    """Binance 거래소 연동"""

    def __init__(self, config: Config):
        self.config = config
        self.exchange = None
        self.paper_trading = config.PAPER_TRADING
        self.paper_balance = 10000.0  # 페이퍼 트레이딩 가상 잔고
        self.paper_positions: Dict[str, Dict] = {}
        self._initialize()

    def _initialize(self):
        if not CCXT_AVAILABLE:
            raise ImportError("ccxt 필요: pip install ccxt")

        # Paper Trading 모드: Public API만 사용 (인증 불필요)
        if self.paper_trading:
            exchange_config = {
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'future',
                    'adjustForTimeDifference': True
                }
            }
            logger.info("페이퍼 트레이딩 모드 (Mainnet Public API + 로컬 시뮬레이션)")
        else:
            exchange_config = {
                'apiKey': self.config.API_KEY,
                'secret': self.config.API_SECRET,
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'future',
                    'adjustForTimeDifference': True
                }
            }

            # Testnet URL 설정
            if self.config.USE_TESTNET:
                exchange_config['urls'] = {
                    'api': {
                        'fapiPublic': 'https://demo-fapi.binance.com/fapi/v1',
                        'fapiPrivate': 'https://demo-fapi.binance.com/fapi/v1',
                        'fapiPublicV2': 'https://demo-fapi.binance.com/fapi/v2',
                        'fapiPrivateV2': 'https://demo-fapi.binance.com/fapi/v2',
                    }
                }
                logger.info("Binance Futures Testnet 모드 (demo-fapi.binance.com)")
            else:
                logger.warning("실전 거래 모드!")

        self.exchange = ccxt.binance(exchange_config)

    async def get_balance(self) -> float:
        if self.paper_trading:
            return self.paper_balance
        balance = await self.exchange.fetch_balance()
        return float(balance.get('USDT', {}).get('free', 0))

    async def get_candles(self, symbol: str, limit: int = 100) -> List[Dict]:
        ohlcv = await self.exchange.fetch_ohlcv(symbol, self.config.TIMEFRAME, limit=limit)
        return [{'timestamp': c[0], 'open': float(c[1]), 'high': float(c[2]),
                 'low': float(c[3]), 'close': float(c[4]), 'volume': float(c[5])} for c in ohlcv]

    async def get_position(self, symbol: str) -> Optional[Position]:
        if self.paper_trading:
            pos = self.paper_positions.get(symbol)
            if pos:
                return Position(
                    symbol=symbol,
                    side=PositionSide.LONG if pos['side'] == 'buy' else PositionSide.SHORT,
                    entry_price=pos['entry'], size=pos['size'],
                    entry_time=pos.get('time', datetime.now()),
                    stop_loss=self.config.STOP_LOSS_PCT,
                    take_profit=self.config.TAKE_PROFIT_PCT
                )
            return None
        try:
            positions = await self.exchange.fetch_positions([symbol])
            for pos in positions:
                contracts = float(pos.get('contracts', 0))
                if contracts > 0:
                    side = PositionSide.LONG if pos['side'] == 'long' else PositionSide.SHORT
                    return Position(
                        symbol=symbol, side=side,
                        entry_price=float(pos['entryPrice']), size=contracts,
                        entry_time=datetime.now(),
                        stop_loss=self.config.STOP_LOSS_PCT,
                        take_profit=self.config.TAKE_PROFIT_PCT
                    )
        except Exception as e:
            logger.error(f"포지션 조회 오류: {e}")
        return None

    async def place_order(self, symbol: str, side: OrderSide, amount: float, price: float = 0) -> Optional[Dict]:
        if self.paper_trading:
            # 페이퍼 트레이딩 시뮬레이션
            if price == 0:
                ticker = await self.exchange.fetch_ticker(symbol)
                price = ticker['last']

            if side == OrderSide.BUY:
                cost = amount * price
                if cost <= self.paper_balance:
                    self.paper_balance -= cost
                    self.paper_positions[symbol] = {
                        'side': 'buy', 'size': amount, 'entry': price, 'time': datetime.now()
                    }
                    logger.info(f"[PAPER] 매수: {amount:.4f} {symbol} @ ${price:,.0f}")
                    return {'id': 'paper', 'symbol': symbol, 'side': 'buy', 'amount': amount, 'price': price}
            else:
                pos = self.paper_positions.get(symbol)
                if pos:
                    pnl = (price - pos['entry']) * pos['size'] if pos['side'] == 'buy' else (pos['entry'] - price) * pos['size']
                    self.paper_balance += pos['size'] * price + pnl
                    del self.paper_positions[symbol]
                    logger.info(f"[PAPER] 매도: {amount:.4f} {symbol} @ ${price:,.0f} (PnL: ${pnl:,.2f})")
                    return {'id': 'paper', 'symbol': symbol, 'side': 'sell', 'amount': amount, 'price': price, 'pnl': pnl}
            return None

        try:
            order = await self.exchange.create_market_order(symbol, side.value, amount)
            logger.info(f"주문 체결: {side.value.upper()} {amount:.4f} {symbol}")
            return order
        except Exception as e:
            logger.error(f"주문 실패: {e}")
            return None

    async def close(self):
        if self.exchange:
            await self.exchange.close()


class MultiBotSystem:
    """멀티봇 자동매매 시스템"""

    def __init__(self, config: Config = None):
        self.config = config or Config()
        self.strategy = TradingStrategy(self.config)
        self.exchange = ExchangeConnector(self.config)
        self.fetcher = StrategyFetcher(self.config)
        self.notifier = TelegramNotifier(self.config)

        self.positions: Dict[str, Position] = {}
        self.daily_stats = DailyStats()
        self.verified_strategies: List[Dict] = []
        self.running = False

    async def initialize(self):
        """시스템 초기화"""
        logger.info("=" * 60)
        logger.info("멀티봇 자동매매 시스템 초기화")
        logger.info("=" * 60)

        # API에서 검증된 전략 로드
        self.verified_strategies = self.fetcher.fetch_verified_strategies()
        if self.verified_strategies:
            logger.info(f"TOP 전략: {self.verified_strategies[0]['title']} ({self.verified_strategies[0]['total_score']}점)")

        # API 통계
        stats = self.fetcher.get_api_stats()
        if stats:
            logger.info(f"전략 통계: 총 {stats.get('total_strategies', 0)}개, "
                       f"합격 {stats.get('passed_count', 0)}개, 평균 {stats.get('avg_score', 0):.1f}점")

        # 잔고 확인
        try:
            balance = await self.exchange.get_balance()
            logger.info(f"USDT 잔고: ${balance:,.2f}")
        except Exception as e:
            logger.warning(f"잔고 조회 실패: {e}")

        await self.notifier.send(
            f"🚀 <b>멀티봇 시작</b>\n\n"
            f"심볼: {', '.join(self.config.SYMBOLS)}\n"
            f"검증 전략: {len(self.verified_strategies)}개\n"
            f"테스트넷: {'✅' if self.config.USE_TESTNET else '❌ 실전'}"
        )

    async def calculate_position_size(self, symbol: str) -> float:
        try:
            balance = await self.exchange.get_balance()
            candles = await self.exchange.get_candles(symbol, limit=1)
            current_price = candles[-1]['close']

            risk_amount = balance * (self.config.RISK_PER_TRADE / 100)
            position_value = risk_amount / (self.config.STOP_LOSS_PCT / 100)
            position_size = position_value / current_price

            return float(Decimal(str(position_size)).quantize(Decimal('0.001'), rounding=ROUND_DOWN))
        except Exception as e:
            logger.error(f"포지션 크기 계산 오류: {e}")
            return 0.001

    def _check_daily_limits(self) -> bool:
        today = datetime.now().strftime('%Y-%m-%d')
        if self.daily_stats.date != today:
            self.daily_stats = DailyStats()

        if self.daily_stats.trades >= self.config.MAX_DAILY_TRADES:
            logger.warning(f"일일 거래 한도 도달: {self.daily_stats.trades}")
            return False
        if self.daily_stats.total_pnl <= -self.config.MAX_DAILY_LOSS_PCT:
            logger.warning(f"일일 손실 한도 도달: {self.daily_stats.total_pnl:.2f}%")
            return False
        return True

    async def process_symbol(self, symbol: str):
        """심볼별 매매 처리"""
        try:
            if not self._check_daily_limits():
                return

            candles = await self.exchange.get_candles(symbol, self.config.CANDLE_LIMIT)
            position = self.positions.get(symbol)
            signal = self.strategy.analyze(candles, position)

            action = signal.get('action', 'hold')
            reason = signal.get('reason', '')
            price = signal.get('price', 0)

            pos_str = "없음"
            if position and position.side != PositionSide.NONE:
                pnl = signal.get('pnl_percent', 0)
                pos_str = f"{position.side.value.upper()} ({pnl:+.2f}%)"

            logger.info(f"[{symbol}] ${price:,.0f} | 포지션: {pos_str} | {action.upper()}: {reason}")

            # 매수 신호
            if action == 'buy' and (not position or position.side == PositionSide.NONE):
                if len(self.positions) < self.config.MAX_POSITIONS:
                    size = await self.calculate_position_size(symbol)
                    if size > 0:
                        order = await self.exchange.place_order(symbol, OrderSide.BUY, size)
                        if order:
                            self.positions[symbol] = Position(
                                symbol=symbol, side=PositionSide.LONG,
                                entry_price=price, size=size,
                                entry_time=datetime.now(),
                                stop_loss=self.config.STOP_LOSS_PCT,
                                take_profit=self.config.TAKE_PROFIT_PCT,
                                highest_price=price
                            )
                            self.daily_stats.trades += 1
                            await self.notifier.send(f"🟢 <b>롱 진입</b>\n{symbol}: {size:.4f} @ ${price:,.0f}")

            # 매도 신호
            elif action == 'sell' and (not position or position.side == PositionSide.NONE):
                if len(self.positions) < self.config.MAX_POSITIONS:
                    size = await self.calculate_position_size(symbol)
                    if size > 0:
                        order = await self.exchange.place_order(symbol, OrderSide.SELL, size)
                        if order:
                            self.positions[symbol] = Position(
                                symbol=symbol, side=PositionSide.SHORT,
                                entry_price=price, size=size,
                                entry_time=datetime.now(),
                                stop_loss=self.config.STOP_LOSS_PCT,
                                take_profit=self.config.TAKE_PROFIT_PCT,
                                lowest_price=price
                            )
                            self.daily_stats.trades += 1
                            await self.notifier.send(f"🔴 <b>숏 진입</b>\n{symbol}: {size:.4f} @ ${price:,.0f}")

            # 청산 신호
            elif action == 'close' and position and position.side != PositionSide.NONE:
                side = OrderSide.SELL if position.side == PositionSide.LONG else OrderSide.BUY
                order = await self.exchange.place_order(symbol, side, position.size)
                if order:
                    pnl = signal.get('pnl_percent', 0)
                    self.daily_stats.total_pnl += pnl
                    if pnl > 0:
                        self.daily_stats.wins += 1
                    else:
                        self.daily_stats.losses += 1

                    emoji = "💚" if pnl > 0 else "💔"
                    del self.positions[symbol]

                    await self.notifier.send(
                        f"{emoji} <b>청산</b>\n{symbol}: {pnl:+.2f}%\n"
                        f"일일: {self.daily_stats.wins}승 {self.daily_stats.losses}패 ({self.daily_stats.total_pnl:+.2f}%)"
                    )

        except Exception as e:
            logger.error(f"[{symbol}] 처리 오류: {e}")

    async def run(self):
        """메인 루프"""
        await self.initialize()

        logger.info("=" * 60)
        logger.info("멀티봇 자동매매 시작")
        logger.info(f"심볼: {', '.join(self.config.SYMBOLS)}")
        logger.info(f"타임프레임: {self.config.TIMEFRAME}")
        logger.info(f"리스크/거래: {self.config.RISK_PER_TRADE}%")
        logger.info(f"테스트넷: {'활성화' if self.config.USE_TESTNET else '비활성화'}")
        logger.info("=" * 60)

        self.running = True

        while self.running:
            try:
                # 모든 심볼 동시 처리
                tasks = [self.process_symbol(symbol) for symbol in self.config.SYMBOLS]
                await asyncio.gather(*tasks)

                await asyncio.sleep(self.config.CHECK_INTERVAL)

            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"루프 오류: {e}")
                await asyncio.sleep(30)

    async def stop(self):
        """시스템 종료"""
        logger.info("시스템 종료 중...")
        self.running = False

        # 열린 포지션 알림
        if self.positions:
            msg = "⚠️ 열린 포지션:\n" + "\n".join([f"- {s}: {p.side.value}" for s, p in self.positions.items()])
            await self.notifier.send(msg)
            logger.warning(msg)

        await self.exchange.close()
        await self.notifier.send("🛑 멀티봇 종료")
        logger.info("시스템 종료 완료")


async def main():
    """메인 함수"""
    config = Config()

    # API 키 확인
    if not config.API_KEY or not config.API_SECRET:
        print("\n" + "=" * 60)
        print("  ⚠️  Binance API 키가 설정되지 않았습니다!")
        print("=" * 60)
        print("\n환경변수 설정:")
        print("  export BINANCE_API_KEY='your_api_key'")
        print("  export BINANCE_API_SECRET='your_api_secret'")
        print("\n또는 .env 파일에 추가:")
        print("  BINANCE_API_KEY=your_api_key")
        print("  BINANCE_API_SECRET=your_api_secret")
        print()
        return

    bot = MultiBotSystem(config)

    # 시그널 핸들러
    def signal_handler(sig, frame):
        asyncio.create_task(bot.stop())

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        await bot.run()
    except KeyboardInterrupt:
        await bot.stop()


if __name__ == "__main__":
    # 환경변수 로드 (.env 파일)
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    asyncio.run(main())
