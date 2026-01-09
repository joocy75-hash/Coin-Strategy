#!/usr/bin/env python3
"""
TOP 3 전략 멀티봇 시스템
- API에서 상위 3개 전략 자동 선별
- 전략별 독립 봇 인스턴스 운영
- 더 좋은 전략 수집 시 자동 교체
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
from typing import Dict, List, Optional, Callable
import requests
import numpy as np

try:
    import ccxt.async_support as ccxt
    CCXT_AVAILABLE = True
except ImportError:
    CCXT_AVAILABLE = False
    print("ccxt 라이브러리가 필요합니다: pip install ccxt")

# 환경변수 로드
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-7s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('multi_strategy_bot.log', encoding='utf-8')
    ]
)
logger = logging.getLogger('MultiStrategyBot')


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
    TOP_N_STRATEGIES: int = 3
    STRATEGY_CHECK_INTERVAL: int = 3600  # 1시간마다 새 전략 체크

    # Binance API
    API_KEY: str = field(default_factory=lambda: os.getenv('BINANCE_API_KEY', ''))
    API_SECRET: str = field(default_factory=lambda: os.getenv('BINANCE_API_SECRET', ''))

    # 거래 설정
    SYMBOL: str = "BTC/USDT"
    TIMEFRAME: str = "1h"
    USE_TESTNET: bool = field(default_factory=lambda: os.getenv('USE_TESTNET', 'true').lower() == 'true')
    PAPER_TRADING: bool = field(default_factory=lambda: os.getenv('PAPER_TRADING', 'true').lower() == 'true')

    # 리스크 관리 (전략당)
    CAPITAL_PER_STRATEGY: float = 3333.33  # 총 $10,000 / 3 전략
    RISK_PER_TRADE: float = 2.0
    STOP_LOSS_PCT: float = 2.0
    TAKE_PROFIT_PCT: float = 4.0
    MAX_DAILY_TRADES: int = 5  # 전략당

    # 봇 설정
    CHECK_INTERVAL: int = 60
    CANDLE_LIMIT: int = 100

    # 텔레그램
    TELEGRAM_BOT_TOKEN: str = field(default_factory=lambda: os.getenv('TELEGRAM_BOT_TOKEN', ''))
    TELEGRAM_CHAT_ID: str = field(default_factory=lambda: os.getenv('TELEGRAM_CHAT_ID', ''))


@dataclass
class StrategyInfo:
    """전략 정보"""
    script_id: str
    title: str
    score: float
    grade: str
    repainting_score: float
    overfitting_score: float
    generate_signal: Optional[Callable] = None
    activated_at: datetime = field(default_factory=datetime.now)

    def __eq__(self, other):
        if isinstance(other, StrategyInfo):
            return self.script_id == other.script_id
        return False

    def __hash__(self):
        return hash(self.script_id)


@dataclass
class Position:
    """포지션 정보"""
    symbol: str
    side: PositionSide
    entry_price: float
    size: float
    entry_time: datetime
    strategy_id: str
    stop_loss: float
    take_profit: float


@dataclass
class StrategyStats:
    """전략별 통계"""
    strategy_id: str
    trades: int = 0
    wins: int = 0
    losses: int = 0
    total_pnl: float = 0.0
    last_trade: Optional[datetime] = None


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


class StrategyManager:
    """전략 관리자 - API에서 TOP 3 전략 로드 및 교체 관리"""

    def __init__(self, config: Config):
        self.config = config
        self.base_url = config.STRATEGY_API_URL
        self.current_strategies: Dict[str, StrategyInfo] = {}

    def fetch_top_strategies(self) -> List[StrategyInfo]:
        """API에서 상위 N개 전략 조회"""
        try:
            url = f"{self.base_url}/strategies"
            params = {
                'grade': self.config.MIN_GRADE,
                'min_score': self.config.MIN_SCORE,
                'limit': 50,
                'sort_by': 'total_score',
                'sort_order': 'desc'
            }
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            strategies = response.json()

            # 점수 기준 상위 N개 선택
            top_strategies = []
            for s in strategies[:self.config.TOP_N_STRATEGIES]:
                info = StrategyInfo(
                    script_id=s['script_id'],
                    title=s['title'],
                    score=s.get('total_score', 0),
                    grade=s.get('grade', 'C'),
                    repainting_score=s.get('repainting_score', 0),
                    overfitting_score=s.get('overfitting_score', 0)
                )
                top_strategies.append(info)

            logger.info(f"TOP {len(top_strategies)} 전략 조회 완료")
            return top_strategies

        except Exception as e:
            logger.error(f"전략 조회 실패: {e}")
            return []

    def check_for_updates(self) -> Dict[str, List[StrategyInfo]]:
        """새 전략 체크 및 교체 대상 반환"""
        new_top = self.fetch_top_strategies()
        if not new_top:
            return {'added': [], 'removed': [], 'kept': list(self.current_strategies.values())}

        current_ids = set(self.current_strategies.keys())
        new_ids = set(s.script_id for s in new_top)

        # 추가/제거/유지 분류
        added_ids = new_ids - current_ids
        removed_ids = current_ids - new_ids
        kept_ids = current_ids & new_ids

        added = [s for s in new_top if s.script_id in added_ids]
        removed = [self.current_strategies[sid] for sid in removed_ids]
        kept = [self.current_strategies[sid] for sid in kept_ids]

        return {'added': added, 'removed': removed, 'kept': kept}

    def apply_updates(self, updates: Dict[str, List[StrategyInfo]]):
        """전략 업데이트 적용"""
        # 제거
        for strategy in updates['removed']:
            if strategy.script_id in self.current_strategies:
                del self.current_strategies[strategy.script_id]
                logger.info(f"전략 제거: {strategy.title} ({strategy.score}점)")

        # 추가
        for strategy in updates['added']:
            strategy.generate_signal = self._create_signal_generator(strategy)
            self.current_strategies[strategy.script_id] = strategy
            logger.info(f"전략 추가: {strategy.title} ({strategy.score}점)")

    def _create_signal_generator(self, strategy: StrategyInfo) -> Callable:
        """전략별 시그널 생성 함수 생성"""
        # TODO: Pine Script → Python 변환된 코드 로드
        # 현재는 기본 EMA+RSI 전략 사용 (전략별 파라미터 차등화)

        # 전략 특성에 따른 파라미터 조정
        if strategy.overfitting_score >= 90:
            # 과적합 점수가 높으면 보수적
            ema_fast, ema_slow = 12, 26
            rsi_ob, rsi_os = 65, 35
        elif strategy.score >= 76:
            # 고점수 전략은 기본
            ema_fast, ema_slow = 9, 21
            rsi_ob, rsi_os = 70, 30
        else:
            # 중간 점수는 민감하게
            ema_fast, ema_slow = 7, 18
            rsi_ob, rsi_os = 75, 25

        def generate_signal(candles: List[Dict], position: Optional[Position] = None) -> Dict:
            if len(candles) < ema_slow + 14:
                return {'action': 'hold', 'reason': '데이터 부족', 'confidence': 0}

            closes = np.array([c['close'] for c in candles])
            current_price = closes[-1]

            # EMA 계산
            def ema(data, period):
                mult = 2 / (period + 1)
                result = np.zeros(len(data))
                result[period-1] = np.mean(data[:period])
                for i in range(period, len(data)):
                    result[i] = (data[i] * mult) + (result[i-1] * (1 - mult))
                return result

            # RSI 계산
            def rsi(data, period=14):
                if len(data) < period + 1:
                    return 50.0
                deltas = np.diff(data[-(period+1):])
                gains = np.where(deltas > 0, deltas, 0)
                losses = np.where(deltas < 0, -deltas, 0)
                avg_gain, avg_loss = np.mean(gains), np.mean(losses)
                if avg_loss == 0:
                    return 100.0
                return 100 - (100 / (1 + avg_gain / avg_loss))

            ema_f = ema(closes, ema_fast)
            ema_s = ema(closes, ema_slow)
            rsi_val = rsi(closes, 14)

            ema_f_now, ema_s_now = ema_f[-1], ema_s[-1]
            ema_f_prev, ema_s_prev = ema_f[-2], ema_s[-2]

            signal = {
                'action': 'hold', 'reason': '시그널 없음', 'confidence': 0,
                'price': current_price, 'rsi': rsi_val, 'strategy': strategy.title
            }

            # 포지션 청산 조건
            if position and position.side != PositionSide.NONE:
                entry = position.entry_price
                pnl_pct = ((current_price - entry) / entry) * 100 if position.side == PositionSide.LONG else ((entry - current_price) / entry) * 100

                if pnl_pct >= 4.0:
                    return {**signal, 'action': 'close', 'reason': f'익절 +{pnl_pct:.2f}%', 'confidence': 95, 'pnl_percent': pnl_pct}
                if pnl_pct <= -2.0:
                    return {**signal, 'action': 'close', 'reason': f'손절 {pnl_pct:.2f}%', 'confidence': 98, 'pnl_percent': pnl_pct}

            # 신규 진입 조건
            if not position or position.side == PositionSide.NONE:
                golden_cross = ema_f_now > ema_s_now and ema_f_prev <= ema_s_prev
                dead_cross = ema_f_now < ema_s_now and ema_f_prev >= ema_s_prev

                if golden_cross and rsi_val < rsi_ob:
                    return {**signal, 'action': 'buy', 'reason': f'골든크로스 (RSI:{rsi_val:.1f})', 'confidence': 75}
                if dead_cross and rsi_val > rsi_os:
                    return {**signal, 'action': 'sell', 'reason': f'데드크로스 (RSI:{rsi_val:.1f})', 'confidence': 75}

            return signal

        return generate_signal


class ExchangeConnector:
    """거래소 연결 (Paper Trading 지원)"""

    def __init__(self, config: Config):
        self.config = config
        self.exchange = None
        self.paper_trading = config.PAPER_TRADING
        self.paper_balance = 10000.0
        self.paper_positions: Dict[str, Dict] = {}
        self._initialize()

    def _initialize(self):
        if not CCXT_AVAILABLE:
            raise ImportError("ccxt 필요")

        if self.paper_trading:
            exchange_config = {
                'enableRateLimit': True,
                'options': {'defaultType': 'future', 'adjustForTimeDifference': True}
            }
            logger.info("페이퍼 트레이딩 모드")
        else:
            exchange_config = {
                'apiKey': self.config.API_KEY,
                'secret': self.config.API_SECRET,
                'enableRateLimit': True,
                'options': {'defaultType': 'future', 'adjustForTimeDifference': True}
            }
            if self.config.USE_TESTNET:
                logger.info("Binance Testnet 모드")
            else:
                logger.warning("실전 거래 모드!")

        self.exchange = ccxt.binance(exchange_config)

    async def get_candles(self, symbol: str, limit: int = 100) -> List[Dict]:
        ohlcv = await self.exchange.fetch_ohlcv(symbol, self.config.TIMEFRAME, limit=limit)
        return [{'timestamp': c[0], 'open': float(c[1]), 'high': float(c[2]),
                 'low': float(c[3]), 'close': float(c[4]), 'volume': float(c[5])} for c in ohlcv]

    async def get_balance(self) -> float:
        if self.paper_trading:
            return self.paper_balance
        balance = await self.exchange.fetch_balance()
        return float(balance.get('USDT', {}).get('free', 0))

    async def place_order(self, symbol: str, side: OrderSide, amount: float, strategy_id: str, price: float = 0) -> Optional[Dict]:
        if self.paper_trading:
            if price == 0:
                ticker = await self.exchange.fetch_ticker(symbol)
                price = ticker['last']

            key = f"{symbol}_{strategy_id}"

            if side == OrderSide.BUY:
                cost = amount * price
                if cost <= self.paper_balance:
                    self.paper_balance -= cost
                    self.paper_positions[key] = {'side': 'buy', 'size': amount, 'entry': price, 'strategy': strategy_id}
                    logger.info(f"[PAPER-{strategy_id[:8]}] 매수: {amount:.4f} @ ${price:,.0f}")
                    return {'id': 'paper', 'symbol': symbol, 'side': 'buy', 'amount': amount, 'price': price}
            else:
                pos = self.paper_positions.get(key)
                if pos:
                    pnl = (price - pos['entry']) * pos['size'] if pos['side'] == 'buy' else (pos['entry'] - price) * pos['size']
                    self.paper_balance += pos['size'] * price
                    del self.paper_positions[key]
                    logger.info(f"[PAPER-{strategy_id[:8]}] 매도: ${price:,.0f} (PnL: ${pnl:,.2f})")
                    return {'id': 'paper', 'symbol': symbol, 'side': 'sell', 'amount': amount, 'price': price, 'pnl': pnl}
            return None

        try:
            order = await self.exchange.create_market_order(symbol, side.value, amount)
            return order
        except Exception as e:
            logger.error(f"주문 실패: {e}")
            return None

    async def close(self):
        if self.exchange:
            await self.exchange.close()


class MultiStrategyBot:
    """TOP 3 전략 멀티봇 시스템"""

    def __init__(self, config: Config = None):
        self.config = config or Config()
        self.strategy_manager = StrategyManager(self.config)
        self.exchange = ExchangeConnector(self.config)
        self.notifier = TelegramNotifier(self.config)

        self.positions: Dict[str, Position] = {}  # key: strategy_id
        self.stats: Dict[str, StrategyStats] = {}
        self.running = False
        self.last_strategy_check = datetime.now()

    async def initialize(self):
        """시스템 초기화"""
        logger.info("=" * 60)
        logger.info("TOP 3 전략 멀티봇 시스템 초기화")
        logger.info("=" * 60)

        # TOP 3 전략 로드
        top_strategies = self.strategy_manager.fetch_top_strategies()
        if not top_strategies:
            logger.error("전략을 불러올 수 없습니다!")
            return False

        for strategy in top_strategies:
            strategy.generate_signal = self.strategy_manager._create_signal_generator(strategy)
            self.strategy_manager.current_strategies[strategy.script_id] = strategy
            self.stats[strategy.script_id] = StrategyStats(strategy_id=strategy.script_id)

        # 로드된 전략 출력
        logger.info(f"활성 전략 {len(self.strategy_manager.current_strategies)}개:")
        for i, (sid, s) in enumerate(self.strategy_manager.current_strategies.items(), 1):
            logger.info(f"  {i}. {s.title} ({s.score}점, {s.grade}등급)")

        # 잔고 확인
        balance = await self.exchange.get_balance()
        logger.info(f"USDT 잔고: ${balance:,.2f}")
        logger.info(f"전략당 자본: ${self.config.CAPITAL_PER_STRATEGY:,.2f}")

        await self.notifier.send(
            f"🚀 <b>TOP 3 멀티봇 시작</b>\n\n"
            f"활성 전략:\n" +
            "\n".join([f"• {s.title} ({s.score}점)" for s in self.strategy_manager.current_strategies.values()]) +
            f"\n\n잔고: ${balance:,.2f}"
        )

        return True

    async def check_strategy_updates(self):
        """주기적으로 새 전략 체크 및 교체"""
        now = datetime.now()
        elapsed = (now - self.last_strategy_check).total_seconds()

        if elapsed < self.config.STRATEGY_CHECK_INTERVAL:
            return

        self.last_strategy_check = now
        logger.info("새 전략 업데이트 체크 중...")

        updates = self.strategy_manager.check_for_updates()

        if updates['added'] or updates['removed']:
            # 제거될 전략의 포지션 청산
            for strategy in updates['removed']:
                if strategy.script_id in self.positions:
                    await self._close_position(strategy.script_id, "전략 교체")

            # 업데이트 적용
            self.strategy_manager.apply_updates(updates)

            # 알림
            msg = "🔄 <b>전략 교체</b>\n\n"
            if updates['removed']:
                msg += "제거:\n" + "\n".join([f"• {s.title}" for s in updates['removed']]) + "\n\n"
            if updates['added']:
                msg += "추가:\n" + "\n".join([f"• {s.title} ({s.score}점)" for s in updates['added']])

            await self.notifier.send(msg)
            logger.info(f"전략 업데이트 완료: +{len(updates['added'])} -{len(updates['removed'])}")
        else:
            logger.info("전략 변경 없음")

    async def _close_position(self, strategy_id: str, reason: str):
        """특정 전략의 포지션 청산"""
        if strategy_id not in self.positions:
            return

        position = self.positions[strategy_id]
        side = OrderSide.SELL if position.side == PositionSide.LONG else OrderSide.BUY
        order = await self.exchange.place_order(
            position.symbol, side, position.size, strategy_id
        )

        if order:
            del self.positions[strategy_id]
            logger.info(f"[{strategy_id[:8]}] 포지션 청산: {reason}")

    async def process_strategy(self, strategy: StrategyInfo):
        """개별 전략 처리"""
        try:
            candles = await self.exchange.get_candles(self.config.SYMBOL, self.config.CANDLE_LIMIT)
            position = self.positions.get(strategy.script_id)

            # 시그널 생성
            signal = strategy.generate_signal(candles, position)
            action = signal.get('action', 'hold')
            reason = signal.get('reason', '')
            price = signal.get('price', 0)

            # 로그
            pos_str = "없음"
            if position:
                pnl = signal.get('pnl_percent', 0)
                pos_str = f"{position.side.value} ({pnl:+.1f}%)"

            logger.info(f"[{strategy.title[:20]}] ${price:,.0f} | {pos_str} | {action.upper()}: {reason}")

            # 매수
            if action == 'buy' and (not position or position.side == PositionSide.NONE):
                balance = self.config.CAPITAL_PER_STRATEGY
                size = (balance * 0.95) / price  # 95% 사용
                size = float(Decimal(str(size)).quantize(Decimal('0.001'), rounding=ROUND_DOWN))

                if size > 0:
                    order = await self.exchange.place_order(self.config.SYMBOL, OrderSide.BUY, size, strategy.script_id)
                    if order:
                        self.positions[strategy.script_id] = Position(
                            symbol=self.config.SYMBOL,
                            side=PositionSide.LONG,
                            entry_price=price,
                            size=size,
                            entry_time=datetime.now(),
                            strategy_id=strategy.script_id,
                            stop_loss=self.config.STOP_LOSS_PCT,
                            take_profit=self.config.TAKE_PROFIT_PCT
                        )
                        self.stats[strategy.script_id].trades += 1
                        await self.notifier.send(
                            f"🟢 <b>롱 진입</b>\n"
                            f"전략: {strategy.title}\n"
                            f"가격: ${price:,.0f}\n"
                            f"수량: {size:.4f}"
                        )

            # 매도 (숏)
            elif action == 'sell' and (not position or position.side == PositionSide.NONE):
                balance = self.config.CAPITAL_PER_STRATEGY
                size = (balance * 0.95) / price
                size = float(Decimal(str(size)).quantize(Decimal('0.001'), rounding=ROUND_DOWN))

                if size > 0:
                    order = await self.exchange.place_order(self.config.SYMBOL, OrderSide.SELL, size, strategy.script_id)
                    if order:
                        self.positions[strategy.script_id] = Position(
                            symbol=self.config.SYMBOL,
                            side=PositionSide.SHORT,
                            entry_price=price,
                            size=size,
                            entry_time=datetime.now(),
                            strategy_id=strategy.script_id,
                            stop_loss=self.config.STOP_LOSS_PCT,
                            take_profit=self.config.TAKE_PROFIT_PCT
                        )
                        self.stats[strategy.script_id].trades += 1
                        await self.notifier.send(
                            f"🔴 <b>숏 진입</b>\n"
                            f"전략: {strategy.title}\n"
                            f"가격: ${price:,.0f}\n"
                            f"수량: {size:.4f}"
                        )

            # 청산
            elif action == 'close' and position and position.side != PositionSide.NONE:
                side = OrderSide.SELL if position.side == PositionSide.LONG else OrderSide.BUY
                order = await self.exchange.place_order(self.config.SYMBOL, side, position.size, strategy.script_id)

                if order:
                    pnl = signal.get('pnl_percent', 0)
                    stats = self.stats[strategy.script_id]
                    stats.total_pnl += pnl
                    if pnl > 0:
                        stats.wins += 1
                    else:
                        stats.losses += 1
                    stats.last_trade = datetime.now()

                    del self.positions[strategy.script_id]

                    emoji = "💚" if pnl > 0 else "💔"
                    await self.notifier.send(
                        f"{emoji} <b>청산</b>\n"
                        f"전략: {strategy.title}\n"
                        f"PnL: {pnl:+.2f}%\n"
                        f"누적: {stats.wins}승 {stats.losses}패 ({stats.total_pnl:+.2f}%)"
                    )

        except Exception as e:
            logger.error(f"[{strategy.title}] 처리 오류: {e}")

    async def run(self):
        """메인 루프"""
        if not await self.initialize():
            return

        logger.info("=" * 60)
        logger.info("TOP 3 전략 멀티봇 시작")
        logger.info(f"심볼: {self.config.SYMBOL}")
        logger.info(f"타임프레임: {self.config.TIMEFRAME}")
        logger.info(f"전략 체크 주기: {self.config.STRATEGY_CHECK_INTERVAL}초")
        logger.info("=" * 60)

        self.running = True

        while self.running:
            try:
                # 전략 업데이트 체크
                await self.check_strategy_updates()

                # 각 전략 병렬 실행
                tasks = [
                    self.process_strategy(strategy)
                    for strategy in self.strategy_manager.current_strategies.values()
                ]
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

        # 통계 출력
        logger.info("\n=== 전략별 성과 ===")
        for sid, stats in self.stats.items():
            strategy = self.strategy_manager.current_strategies.get(sid)
            name = strategy.title if strategy else sid[:20]
            logger.info(f"{name}: {stats.wins}승 {stats.losses}패, PnL: {stats.total_pnl:+.2f}%")

        # 열린 포지션 알림
        if self.positions:
            msg = "⚠️ 열린 포지션:\n" + "\n".join([
                f"• {p.strategy_id[:8]}: {p.side.value} @ ${p.entry_price:,.0f}"
                for p in self.positions.values()
            ])
            await self.notifier.send(msg)

        await self.exchange.close()
        await self.notifier.send("🛑 TOP 3 멀티봇 종료")
        logger.info("시스템 종료 완료")


async def main():
    """메인 함수"""
    config = Config()

    if not config.API_KEY or not config.API_SECRET:
        if not config.PAPER_TRADING:
            print("\n⚠️ API 키 필요 (또는 PAPER_TRADING=true 설정)")
            return

    bot = MultiStrategyBot(config)

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
