#!/usr/bin/env python3
"""
전략연구소 통합 시스템 테스트
- Strategy Research Lab API 연동
- Binance Paper Trading / Testnet / Mainnet
- Telegram 알림
- 멀티봇 자동매매
"""

import asyncio
import os
import sys
from datetime import datetime

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# 컬러 출력
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'


def print_header(title: str):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}  {title}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 60}{Colors.END}\n")


def print_success(msg: str):
    print(f"  {Colors.GREEN}✓{Colors.END} {msg}")


def print_error(msg: str):
    print(f"  {Colors.RED}✗{Colors.END} {msg}")


def print_warning(msg: str):
    print(f"  {Colors.YELLOW}⚠{Colors.END} {msg}")


async def test_strategy_api():
    """Strategy Research Lab API 테스트"""
    print_header("1. Strategy Research Lab API")

    try:
        from main_trading_system import Config, StrategyFetcher
        config = Config()
        fetcher = StrategyFetcher(config)

        # 통계 조회
        stats = fetcher.get_api_stats()
        if stats:
            print_success(f"API 연결 성공: {config.STRATEGY_API_URL}")
            print_success(f"전체 전략: {stats.get('total_strategies', 0)}개")
            print_success(f"합격 전략: {stats.get('passed_count', 0)}개")
            print_success(f"평균 점수: {stats.get('avg_score', 0):.1f}점")
        else:
            print_error("API 통계 조회 실패")
            return False

        # 검증된 전략 조회
        strategies = fetcher.fetch_verified_strategies(limit=5)
        if strategies:
            print_success(f"검증된 전략 {len(strategies)}개 로드")
            for i, s in enumerate(strategies[:3], 1):
                print(f"      {i}. {s['title']} ({s['total_score']}점, {s['grade']}등급)")
        else:
            print_warning("검증된 전략 없음")

        return True

    except Exception as e:
        print_error(f"API 테스트 실패: {e}")
        return False


async def test_exchange_connection():
    """거래소 연결 테스트"""
    print_header("2. 거래소 연결 (Paper Trading)")

    try:
        from main_trading_system import Config, ExchangeConnector

        config = Config()
        connector = ExchangeConnector(config)

        # 잔고 확인
        balance = await connector.get_balance()
        print_success(f"Paper Trading 모드: {config.PAPER_TRADING}")
        print_success(f"가상 잔고: ${balance:,.2f} USDT")

        # 캔들 데이터 확인
        for symbol in config.SYMBOLS[:2]:
            candles = await connector.get_candles(symbol, limit=10)
            if candles:
                last_price = candles[-1]['close']
                print_success(f"{symbol} 가격: ${last_price:,.2f}")
            else:
                print_error(f"{symbol} 데이터 조회 실패")

        await connector.close()
        return True

    except Exception as e:
        print_error(f"거래소 연결 실패: {e}")
        return False


async def test_trading_strategy():
    """트레이딩 전략 테스트"""
    print_header("3. 트레이딩 전략 분석")

    try:
        from main_trading_system import Config, ExchangeConnector, TradingStrategy

        config = Config()
        connector = ExchangeConnector(config)
        strategy = TradingStrategy(config)

        for symbol in config.SYMBOLS:
            candles = await connector.get_candles(symbol, limit=100)
            if candles:
                signal = strategy.analyze(candles)
                action = signal.get('action', 'hold').upper()
                reason = signal.get('reason', '')
                price = signal.get('price', 0)
                rsi = signal.get('rsi', 0)

                color = Colors.GREEN if action == 'BUY' else Colors.RED if action == 'SELL' else Colors.YELLOW
                print_success(f"{symbol}: ${price:,.0f} | RSI: {rsi:.1f} | {color}{action}{Colors.END}: {reason}")

        await connector.close()
        return True

    except Exception as e:
        print_error(f"전략 분석 실패: {e}")
        return False


async def test_telegram():
    """텔레그램 알림 테스트"""
    print_header("4. Telegram 알림")

    try:
        from main_trading_system import Config, TelegramNotifier

        config = Config()
        notifier = TelegramNotifier(config)

        if notifier.enabled:
            await notifier.send(
                f"🔔 <b>통합 테스트 완료</b>\n\n"
                f"시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"모드: Paper Trading\n"
                f"심볼: {', '.join(config.SYMBOLS)}"
            )
            print_success("Telegram 알림 전송 완료")
            print_success(f"Chat ID: {config.TELEGRAM_CHAT_ID}")
        else:
            print_warning("Telegram 미설정 (TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID 필요)")

        return True

    except Exception as e:
        print_error(f"Telegram 테스트 실패: {e}")
        return False


async def test_multibot_cycle():
    """멀티봇 1사이클 테스트"""
    print_header("5. 멀티봇 1사이클 실행")

    try:
        from main_trading_system import Config, MultiBotSystem

        config = Config()
        bot = MultiBotSystem(config)

        # 초기화
        await bot.initialize()
        print_success("멀티봇 초기화 완료")

        # 각 심볼 처리
        for symbol in config.SYMBOLS:
            await bot.process_symbol(symbol)
            await asyncio.sleep(0.5)

        print_success(f"심볼 처리 완료: {', '.join(config.SYMBOLS)}")
        print_success(f"현재 포지션: {len(bot.positions)}개")
        print_success(f"일일 거래: {bot.daily_stats.trades}회")
        print_success(f"Paper 잔고: ${bot.exchange.paper_balance:,.2f}")

        await bot.exchange.close()
        return True

    except Exception as e:
        print_error(f"멀티봇 테스트 실패: {e}")
        return False


async def main():
    """메인 통합 테스트"""
    print(f"\n{Colors.BOLD}{'=' * 60}{Colors.END}")
    print(f"{Colors.BOLD}   전략연구소 통합 시스템 테스트{Colors.END}")
    print(f"{Colors.BOLD}   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{Colors.END}")
    print(f"{Colors.BOLD}{'=' * 60}{Colors.END}")

    results = {}

    # 테스트 실행
    results['Strategy API'] = await test_strategy_api()
    results['Exchange'] = await test_exchange_connection()
    results['Strategy'] = await test_trading_strategy()
    results['Telegram'] = await test_telegram()
    results['MultiBotCycle'] = await test_multibot_cycle()

    # 결과 요약
    print_header("테스트 결과 요약")

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for name, result in results.items():
        if result:
            print_success(f"{name}: 통과")
        else:
            print_error(f"{name}: 실패")

    print()
    if passed == total:
        print(f"{Colors.GREEN}{Colors.BOLD}  ✓ 모든 테스트 통과! ({passed}/{total}){Colors.END}")
        print(f"\n  {Colors.BLUE}시스템 실행 방법:{Colors.END}")
        print(f"    python main_trading_system.py")
    else:
        print(f"{Colors.RED}{Colors.BOLD}  ✗ 일부 테스트 실패 ({passed}/{total}){Colors.END}")

    print()


if __name__ == "__main__":
    asyncio.run(main())
