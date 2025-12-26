#!/usr/bin/env python3
"""
24시간 자동 전략 수집 + 백테스트 서비스

원격 서버에서 실행되며 주기적으로 TradingView에서 고품질 전략을 수집합니다.
- 6시간마다 수집 실행 (하루 4회)
- 최소 500 부스트 이상 전략만 수집
- Pine Script 코드 추출
- 자동 백테스트 실행
- HTML 리포트 생성
"""

import asyncio
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import List

# 프로젝트 루트 설정
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.collector.human_like_scraper import HumanLikeScraper, StrategyData
from src.collector.pine_fetcher import PineCodeFetcher
from src.storage.database import StrategyDatabase
from src.backtester.strategy_tester import StrategyTester

# 로깅 설정
LOG_DIR = project_root / "logs"
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-7s | %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / "auto_collector.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class AutoCollectorService:
    """24시간 자동 수집 + 백테스트 서비스"""

    def __init__(
        self,
        collect_interval_hours: int = 6,
        target_count: int = 100,
        min_boosts: int = 500,
        max_pages: int = 100,
        run_backtest: bool = True,
        backtest_symbol: str = "BTC/USDT",
        backtest_timeframe: str = "1h"
    ):
        self.collect_interval = timedelta(hours=collect_interval_hours)
        self.target_count = target_count
        self.min_boosts = min_boosts
        self.max_pages = max_pages
        self.run_backtest = run_backtest
        self.backtest_symbol = backtest_symbol
        self.backtest_timeframe = backtest_timeframe
        self.running = True
        self.total_collected = 0
        self.total_backtested = 0
        self.collection_count = 0

        # 데이터베이스 경로
        self.db_path = str(project_root / "data" / "strategies.db")

    async def run_collection(self) -> int:
        """단일 수집 + 백테스트 실행"""
        logger.info("=" * 60)
        logger.info(f"🚀 수집 사이클 시작 #{self.collection_count + 1}")
        logger.info(f"   목표: {self.target_count}개, 최소 부스트: {self.min_boosts}")
        logger.info("=" * 60)

        collected = 0
        backtested = 0

        try:
            # 1단계: 전략 수집
            logger.info("\n📥 1단계: 전략 수집")
            async with HumanLikeScraper(headless=False) as scraper:
                strategies = await scraper.collect_strategies(
                    target_count=self.target_count,
                    min_boosts=self.min_boosts,
                    max_pages=self.max_pages
                )
                collected = len(strategies)
                logger.info(f"✅ 수집 완료: {collected}개 전략")

            if not strategies:
                logger.warning("⚠️ 수집된 전략 없음")
                return 0

            # 2단계: Pine Script 코드 추출
            logger.info(f"\n📜 2단계: Pine Script 코드 추출")
            strategies_with_code = await self._extract_pine_codes(strategies)
            logger.info(f"✅ 코드 추출 완료: {len(strategies_with_code)}개")

            # 3단계: DB 저장
            logger.info(f"\n💾 3단계: 데이터베이스 저장")
            await self._save_to_database(strategies_with_code)

            # 4단계: 백테스트 실행 (옵션)
            if self.run_backtest and strategies_with_code:
                logger.info(f"\n🧪 4단계: 백테스트 실행")
                backtested = await self._run_backtests(strategies_with_code)
                self.total_backtested += backtested
                logger.info(f"✅ 백테스트 완료: {backtested}개")

            # 5단계: HTML 리포트 생성
            logger.info(f"\n📊 5단계: HTML 리포트 생성")
            await self._generate_report()

            # 통계 업데이트
            self.total_collected += collected
            self.collection_count += 1

            logger.info("\n" + "=" * 60)
            logger.info(f"📊 사이클 #{self.collection_count} 완료")
            logger.info(f"   수집: {collected}개, 백테스트: {backtested}개")
            logger.info(f"   누적: 총 {self.total_collected}개 수집, {self.total_backtested}개 백테스트")
            logger.info("=" * 60)

            # 상위 5개 전략 로그
            if strategies:
                logger.info("\n🏆 이번 수집 상위 5개:")
                sorted_strategies = sorted(strategies, key=lambda x: x.boosts, reverse=True)[:5]
                for i, s in enumerate(sorted_strategies, 1):
                    logger.info(f"   {i}. {s.boosts:,} 부스트 | {s.title[:40]}")

            return collected

        except Exception as e:
            logger.error(f"❌ 수집 실패: {e}", exc_info=True)
            return 0

    async def _extract_pine_codes(self, strategies: List[StrategyData]) -> List[StrategyData]:
        """Pine Script 코드 추출"""
        fetcher = PineCodeFetcher()
        strategies_with_code = []

        for i, strategy in enumerate(strategies, 1):
            try:
                logger.info(f"   [{i}/{len(strategies)}] {strategy.title[:40]}...")

                # script_url을 사용하여 Pine 코드 추출
                result = await fetcher.fetch_pine_code(strategy.script_url)

                if result.pine_code and not result.is_protected:
                    strategy.pine_code = result.pine_code
                    strategies_with_code.append(strategy)
                    logger.info(f"      ✅ 코드 추출 성공 ({len(result.pine_code)} bytes)")
                else:
                    logger.warning(f"      ⚠️ 코드 없음 (비공개 또는 보호됨)")

                await asyncio.sleep(1)  # Rate limiting

            except Exception as e:
                logger.error(f"      ❌ 추출 실패: {e}")

        return strategies_with_code

    async def _save_to_database(self, strategies: List[StrategyData]):
        """데이터베이스에 저장"""
        try:
            db = StrategyDatabase(self.db_path)
            await db.init_db()

            saved = 0
            for strategy in strategies:
                try:
                    await db.upsert_strategy({
                        'script_id': strategy.script_id,
                        'title': strategy.title,
                        'author': strategy.author,
                        'likes': strategy.boosts,
                        'script_url': strategy.script_url,
                        'pine_code': getattr(strategy, 'pine_code', None),
                        'is_open_source': True,
                        'collected_at': datetime.now().isoformat()
                    })
                    saved += 1
                except Exception as e:
                    logger.error(f"   ❌ 저장 실패 ({strategy.title}): {e}")

            logger.info(f"✅ DB 저장 완료: {saved}개")

        except Exception as e:
            logger.error(f"❌ DB 저장 오류: {e}")

    async def _run_backtests(self, strategies: List[StrategyData]) -> int:
        """백테스트 실행"""
        tester = StrategyTester(self.db_path)
        backtested = 0

        # 최근 6개월 데이터로 백테스트
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=180)).strftime("%Y-%m-%d")

        for i, strategy in enumerate(strategies, 1):
            if not hasattr(strategy, 'pine_code') or not strategy.pine_code:
                continue

            try:
                logger.info(f"   [{i}/{len(strategies)}] 백테스트: {strategy.title[:35]}...")

                result = await tester.test_strategy(
                    script_id=strategy.script_id,
                    symbol=self.backtest_symbol,
                    timeframe=self.backtest_timeframe,
                    start_date=start_date,
                    end_date=end_date
                )

                if result.get('success'):
                    backtest = result.get('backtest', {})
                    logger.info(f"      ✅ 수익률: {backtest.get('total_return', 0):.1f}%, "
                              f"승률: {backtest.get('win_rate', 0):.1f}%, "
                              f"MDD: {backtest.get('max_drawdown', 0):.1f}%")
                    backtested += 1
                else:
                    logger.warning(f"      ⚠️ 실패: {result.get('error', 'Unknown')}")

                await asyncio.sleep(0.5)  # Rate limiting

            except Exception as e:
                logger.error(f"      ❌ 백테스트 오류: {e}")

        return backtested

    async def _generate_report(self):
        """HTML 리포트 생성"""
        try:
            from scripts.generate_beginner_report import generate_beginner_report

            output_path = project_root / "data" / "beginner_report.html"
            generate_beginner_report(self.db_path, str(output_path))
            logger.info(f"✅ HTML 리포트 생성: {output_path}")

        except Exception as e:
            logger.error(f"❌ 리포트 생성 실패: {e}")

    async def run_forever(self):
        """무한 루프로 주기적 수집 실행"""
        logger.info("=" * 60)
        logger.info("🤖 24시간 자동 수집 + 백테스트 서비스 시작")
        logger.info(f"   수집 주기: {self.collect_interval}")
        logger.info(f"   목표 수량: {self.target_count}개")
        logger.info(f"   최소 부스트: {self.min_boosts}")
        logger.info(f"   백테스트: {'활성화' if self.run_backtest else '비활성화'}")
        if self.run_backtest:
            logger.info(f"   백테스트 설정: {self.backtest_symbol} / {self.backtest_timeframe}")
        logger.info("=" * 60)

        while self.running:
            try:
                # 수집 + 백테스트 실행
                await self.run_collection()

                # 다음 수집까지 대기
                next_run = datetime.now() + self.collect_interval
                logger.info(f"\n⏰ 다음 수집: {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
                logger.info(f"   {self.collect_interval} 후 재실행\n")

                await asyncio.sleep(self.collect_interval.total_seconds())

            except asyncio.CancelledError:
                logger.info("🛑 서비스 중지 요청")
                break
            except Exception as e:
                logger.error(f"❌ 오류 발생: {e}", exc_info=True)
                # 오류 발생 시 1시간 후 재시도
                logger.info("⏳ 1시간 후 재시도...")
                await asyncio.sleep(3600)

    def stop(self):
        """서비스 중지"""
        self.running = False
        logger.info("🛑 서비스 중지 신호 수신")


async def main():
    """메인 함수"""
    import argparse

    parser = argparse.ArgumentParser(description='24시간 자동 전략 수집 + 백테스트 서비스')
    parser.add_argument('--interval', type=int, default=6, help='수집 주기 (시간, 기본: 6)')
    parser.add_argument('--count', type=int, default=100, help='목표 수집 수량 (기본: 100)')
    parser.add_argument('--min-boost', type=int, default=500, help='최소 부스트 (기본: 500)')
    parser.add_argument('--max-pages', type=int, default=100, help='최대 페이지 수 (기본: 100)')
    parser.add_argument('--once', action='store_true', help='1회만 수집 후 종료')
    parser.add_argument('--no-backtest', action='store_true', help='백테스트 비활성화')
    parser.add_argument('--symbol', type=str, default='BTC/USDT', help='백테스트 심볼 (기본: BTC/USDT)')
    parser.add_argument('--timeframe', type=str, default='1h', help='백테스트 타임프레임 (기본: 1h)')
    args = parser.parse_args()

    service = AutoCollectorService(
        collect_interval_hours=args.interval,
        target_count=args.count,
        min_boosts=args.min_boost,
        max_pages=args.max_pages,
        run_backtest=not args.no_backtest,
        backtest_symbol=args.symbol,
        backtest_timeframe=args.timeframe
    )

    if args.once:
        # 1회 수집
        await service.run_collection()
    else:
        # 무한 루프
        try:
            await service.run_forever()
        except KeyboardInterrupt:
            service.stop()
            logger.info("👋 서비스 종료")


if __name__ == '__main__':
    asyncio.run(main())
