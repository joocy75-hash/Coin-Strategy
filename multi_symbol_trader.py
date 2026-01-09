#!/usr/bin/env python3
"""
다중 심볼 트레이더 - Strategy Research Lab 연동
API에서 검증된 최고의 전략을 선택하여 자동 매매
"""

import asyncio
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional
import requests

try:
    import ccxt.async_support as ccxt
except ImportError:
    print("pip install ccxt 필요")
    exit(1)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(message)s',
    handlers=[logging.StreamHandler(), logging.FileHandler('trader.log', encoding='utf-8')]
)
logger = logging.getLogger('Trader')


@dataclass
class TraderConfig:
    """트레이더 설정"""
    API_URL: str = "http://141.164.55.245/api"
    SYMBOLS: List[str] = field(default_factory=lambda: ['BTC/USDT', 'ETH/USDT', 'SOL/USDT'])
    TIMEFRAME: str = "1h"

    # Binance
    API_KEY: str = field(default_factory=lambda: os.getenv('BINANCE_API_KEY', ''))
    API_SECRET: str = field(default_factory=lambda: os.getenv('BINANCE_API_SECRET', ''))
    USE_TESTNET: bool = True

    # 리스크
    RISK_PCT: float = 1.0
    STOP_LOSS: float = 2.0
    TAKE_PROFIT: float = 4.0
    MAX_POSITIONS: int = 3

    # 전략 파라미터
    EMA_FAST: int = 9
    EMA_SLOW: int = 21

    # Telegram
    TG_TOKEN: str = field(default_factory=lambda: os.getenv('TELEGRAM_BOT_TOKEN', ''))
    TG_CHAT: str = field(default_factory=lambda: os.getenv('TELEGRAM_CHAT_ID', ''))


class StrategyAPI:
    """Strategy Research Lab API 클라이언트"""

    def __init__(self, base_url: str):
        self.base_url = base_url

    def get_best_strategies(self, min_score: float = 70.0) -> List[Dict]:
        """최고 점수 전략 조회"""
        try:
            resp = requests.get(f"{self.base_url}/strategies",
                              params={'grade': 'B', 'limit': 10, 'sort': 'total_score', 'order': 'desc'},
                              timeout=10)
            resp.raise_for_status()
            return [s for s in resp.json() if s.get('total_score', 0) >= min_score]
        except Exception as e:
            logger.error(f"API 오류: {e}")
            return []

    def get_stats(self) -> Dict:
        """통계 조회"""
        try:
            resp = requests.get(f"{self.base_url}/stats", timeout=10)
            resp.raise_for_status()
            return resp.json()
        except:
            return {}


class Telegram:
    """텔레그램 알림"""

    def __init__(self, token: str, chat_id: str):
        self.token = token
        self.chat_id = chat_id
        self.enabled = bool(token and chat_id)

    def send(self, msg: str):
        if not self.enabled:
            return
        try:
            requests.post(
                f"https://api.telegram.org/bot{self.token}/sendMessage",
                data={'chat_id': self.chat_id, 'text': msg, 'parse_mode': 'HTML'},
                timeout=5
            )
        except:
            pass


class MultiSymbolTrader:
    """다중 심볼 자동매매 트레이더"""

    def __init__(self, config: TraderConfig = None):
        self.config = config or TraderConfig()
        self.api = StrategyAPI(self.config.API_URL)
        self.telegram = Telegram(self.config.TG_TOKEN, self.config.TG_CHAT)
        self.exchange = None
        self.positions: Dict[str, Dict] = {}
        self.running = False

    async def connect(self):
        """거래소 연결"""
        self.exchange = ccxt.binance({
            'apiKey': self.config.API_KEY,
            'secret': self.config.API_SECRET,
            'enableRateLimit': True,
            'options': {'defaultType': 'future'}
        })

        if self.config.USE_TESTNET:
            self.exchange.set_sandbox_mode(True)
            logger.info("테스트넷 연결")

        # 잔고 확인
        balance = await self.exchange.fetch_balance()
        usdt = balance.get('USDT', {}).get('free', 0)
        logger.info(f"잔고: ${usdt:,.2f} USDT")

        # 검증 전략 로드
        strategies = self.api.get_best_strategies()
        if strategies:
            best = strategies[0]
            logger.info(f"최고 전략: {best['title']} ({best['total_score']}점)")

        self.telegram.send(
            f"<b>트레이더 시작</b>\n"
            f"심볼: {', '.join(self.config.SYMBOLS)}\n"
            f"잔고: ${usdt:,.2f}\n"
            f"테스트넷: {'O' if self.config.USE_TESTNET else 'X'}"
        )

    async def get_signal(self, symbol: str) -> str:
        """매매 신호 생성"""
        try:
            ohlcv = await self.exchange.fetch_ohlcv(symbol, self.config.TIMEFRAME, limit=50)
            closes = [c[4] for c in ohlcv]

            # EMA 계산
            ema_fast = sum(closes[-self.config.EMA_FAST:]) / self.config.EMA_FAST
            ema_slow = sum(closes[-self.config.EMA_SLOW:]) / self.config.EMA_SLOW

            prev_closes = closes[:-1]
            prev_ema_fast = sum(prev_closes[-self.config.EMA_FAST:]) / self.config.EMA_FAST
            prev_ema_slow = sum(prev_closes[-self.config.EMA_SLOW:]) / self.config.EMA_SLOW

            # 크로스오버 감지
            if ema_fast > ema_slow and prev_ema_fast <= prev_ema_slow:
                return 'BUY'
            elif ema_fast < ema_slow and prev_ema_fast >= prev_ema_slow:
                return 'SELL'

            return 'HOLD'

        except Exception as e:
            logger.error(f"신호 오류 [{symbol}]: {e}")
            return 'HOLD'

    async def check_position(self, symbol: str) -> Optional[Dict]:
        """포지션 확인"""
        try:
            positions = await self.exchange.fetch_positions([symbol])
            for pos in positions:
                if float(pos.get('contracts', 0)) > 0:
                    return {
                        'side': pos['side'],
                        'size': float(pos['contracts']),
                        'entry': float(pos['entryPrice']),
                        'pnl': float(pos.get('unrealizedPnl', 0))
                    }
        except:
            pass
        return None

    async def trade(self, symbol: str):
        """심볼 매매 처리"""
        try:
            ticker = await self.exchange.fetch_ticker(symbol)
            price = ticker['last']
            signal = await self.get_signal(symbol)
            position = await self.check_position(symbol)

            # 포지션 관리
            if position:
                entry = position['entry']
                pnl_pct = ((price - entry) / entry * 100) if position['side'] == 'long' else ((entry - price) / entry * 100)

                # 익절/손절
                if pnl_pct >= self.config.TAKE_PROFIT:
                    side = 'sell' if position['side'] == 'long' else 'buy'
                    await self.exchange.create_market_order(symbol, side, position['size'])
                    self.telegram.send(f"익절 {symbol}: +{pnl_pct:.2f}%")
                    logger.info(f"[{symbol}] 익절 +{pnl_pct:.2f}%")
                    return

                if pnl_pct <= -self.config.STOP_LOSS:
                    side = 'sell' if position['side'] == 'long' else 'buy'
                    await self.exchange.create_market_order(symbol, side, position['size'])
                    self.telegram.send(f"손절 {symbol}: {pnl_pct:.2f}%")
                    logger.info(f"[{symbol}] 손절 {pnl_pct:.2f}%")
                    return

                logger.info(f"[{symbol}] ${price:,.0f} | {position['side'].upper()} {pnl_pct:+.2f}%")

            else:
                # 신규 진입
                if signal in ['BUY', 'SELL'] and len(self.positions) < self.config.MAX_POSITIONS:
                    balance = await self.exchange.fetch_balance()
                    usdt = balance.get('USDT', {}).get('free', 0)
                    size = (usdt * self.config.RISK_PCT / 100) / (price * self.config.STOP_LOSS / 100) / price
                    size = round(size, 3)

                    if size > 0.001:
                        side = 'buy' if signal == 'BUY' else 'sell'
                        await self.exchange.create_market_order(symbol, side, size)
                        self.positions[symbol] = {'side': side, 'size': size, 'entry': price}

                        self.telegram.send(f"{signal} {symbol}\n{size:.4f} @ ${price:,.0f}")
                        logger.info(f"[{symbol}] {signal} {size:.4f} @ ${price:,.0f}")
                else:
                    logger.info(f"[{symbol}] ${price:,.0f} | HOLD")

        except Exception as e:
            logger.error(f"매매 오류 [{symbol}]: {e}")

    async def run(self):
        """메인 루프"""
        await self.connect()
        self.running = True

        logger.info("=" * 50)
        logger.info(f"자동매매 시작: {', '.join(self.config.SYMBOLS)}")
        logger.info("=" * 50)

        while self.running:
            try:
                for symbol in self.config.SYMBOLS:
                    await self.trade(symbol)
                    await asyncio.sleep(1)

                await asyncio.sleep(60)

            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"루프 오류: {e}")
                await asyncio.sleep(30)

        await self.exchange.close()
        self.telegram.send("트레이더 종료")


async def main():
    config = TraderConfig()

    if not config.API_KEY:
        print("\nBINANCE_API_KEY 환경변수를 설정하세요")
        print("export BINANCE_API_KEY='your_key'")
        print("export BINANCE_API_SECRET='your_secret'")
        return

    trader = MultiSymbolTrader(config)
    await trader.run()


if __name__ == "__main__":
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except:
        pass

    asyncio.run(main())
