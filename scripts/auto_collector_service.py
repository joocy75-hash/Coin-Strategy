#!/usr/bin/env python3
"""
24시간 자동 전략 수집 + 백테스트 서비스 (텔레그램 알림 포함)

원격 서버에서 실행되며 주기적으로 TradingView에서 고품질 전략을 수집합니다.
- 6시간마다 수집 실행 (하루 4회)
- 최소 500 부스트 이상 전략만 수집
- Pine Script 코드 추출
- 자동 백테스트 실행 (Binance 데이터)
- HTML 리포트 생성
- 텔레그램 실시간 알림
"""

import asyncio
import logging
import sys
import os
import time
import traceback
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

# 프로젝트 루트 설정
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.collector.human_like_scraper import HumanLikeScraper, StrategyData
from src.collector.pine_fetcher import PineCodeFetcher
from src.storage.database import StrategyDatabase
from src.backtester.strategy_tester import StrategyTester
from src.notification.telegram_bot import TelegramNotifier, BacktestResult
from scripts.analyze_strategies import StrategyAnalyzer

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

# 텔레그램 설정
# 보안: 환경변수에서만 읽고 기본값 제거 (하드코딩된 토큰 노출 방지)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
    logger.error("❌ TELEGRAM_BOT_TOKEN과 TELEGRAM_CHAT_ID 환경변수가 설정되지 않았습니다.")
    logger.error("   텔레그램 알림이 비활성화됩니다.")
    TELEGRAM_BOT_TOKEN = None
    TELEGRAM_CHAT_ID = None


class AutoCollectorService:
    """24시간 자동 수집 + 백테스트 서비스 (텔레그램 알림 포함)"""

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
        self.start_time = datetime.now()
        self.last_error: Optional[str] = None
        self.consecutive_errors = 0

        # 데이터베이스 경로
        self.db_path = str(project_root / "data" / "strategies.db")

        # 텔레그램 알림 (환경변수 미설정 시 None으로 비활성화)
        self.telegram = TelegramNotifier(
            bot_token=TELEGRAM_BOT_TOKEN,
            chat_id=TELEGRAM_CHAT_ID
        ) if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID else None

        # 백테스트 결과 저장
        self.backtest_results: List[BacktestResult] = []

    async def run_collection(self) -> int:
        """단일 수집 + 백테스트 실행"""
        cycle_start = time.time()
        self.collection_count += 1

        logger.info("=" * 60)
        logger.info(f"🚀 수집 사이클 시작 #{self.collection_count}")
        logger.info(f"   목표: {self.target_count}개, 최소 부스트: {self.min_boosts}")
        logger.info("=" * 60)

        # 수집 시작 알림
        if self.telegram:
            await self.telegram.notify_collection_start(self.collection_count)

        collected = 0
        backtested = 0
        strategies_with_code = []
        strategies = []

        try:
            # 1단계: 전략 수집
            logger.info("\n📥 1단계: 전략 수집")
            try:
                async with HumanLikeScraper(headless=True) as scraper:
                    strategies = await scraper.collect_strategies(
                        target_count=self.target_count,
                        min_boosts=self.min_boosts,
                        max_pages=self.max_pages
                    )
                    collected = len(strategies)
                    logger.info(f"✅ 수집 완료: {collected}개 전략")
            except Exception as e:
                error_msg = f"전략 수집 실패: {str(e)}"
                logger.error(error_msg, exc_info=True)
                if self.telegram:
                    await self.telegram.notify_error(
                        "수집 오류",
                        error_msg,
                        f"사이클 #{self.collection_count}"
                    )
                raise

            if not strategies:
                logger.warning("⚠️ 수집된 전략 없음")
                if self.telegram:
                    await self.telegram.notify_error(
                        "수집 경고",
                        "수집된 전략이 없습니다. TradingView 접근에 문제가 있을 수 있습니다.",
                        f"사이클 #{self.collection_count}"
                    )
                return 0

            # 2단계: Pine Script 코드 추출
            logger.info(f"\n📜 2단계: Pine Script 코드 추출")
            try:
                strategies_with_code = await self._extract_pine_codes(strategies)
                logger.info(f"✅ 코드 추출 완료: {len(strategies_with_code)}개")
            except Exception as e:
                error_msg = f"코드 추출 실패: {str(e)}"
                logger.error(error_msg, exc_info=True)
                if self.telegram:
                    await self.telegram.notify_error("코드 추출 오류", error_msg)

            # 3단계: DB 저장
            logger.info(f"\n💾 3단계: 데이터베이스 저장")
            try:
                await self._save_to_database(strategies_with_code)
            except Exception as e:
                error_msg = f"DB 저장 실패: {str(e)}"
                logger.error(error_msg, exc_info=True)
                if self.telegram:
                    await self.telegram.notify_error("DB 저장 오류", error_msg)

            # 4단계: AI 분석 (analysis_json 생성)
            logger.info(f"\n🤖 4단계: AI 품질 분석")
            analyzed_count = 0
            try:
                analyzed_count = await self._analyze_strategies(strategies_with_code)
                logger.info(f"✅ AI 분석 완료: {analyzed_count}개")
            except Exception as e:
                error_msg = f"AI 분석 실패: {str(e)}"
                logger.error(error_msg, exc_info=True)
                if self.telegram:
                    await self.telegram.notify_error("AI 분석 오류", error_msg)

            # 5단계: 백테스트 실행 (옵션)
            backtest_results = []
            if self.run_backtest and strategies_with_code:
                logger.info(f"\n🧪 5단계: 백테스트 실행")
                try:
                    backtested, backtest_results = await self._run_backtests(strategies_with_code)
                    self.total_backtested += backtested
                    logger.info(f"✅ 백테스트 완료: {backtested}개")
                except Exception as e:
                    error_msg = f"백테스트 실패: {str(e)}"
                    logger.error(error_msg, exc_info=True)
                    if self.telegram:
                        await self.telegram.notify_error("백테스트 오류", error_msg)

            # 6단계: HTML 리포트 생성
            logger.info(f"\n📊 6단계: HTML 리포트 생성")
            try:
                await self._generate_report()
            except Exception as e:
                logger.error(f"❌ 리포트 생성 실패: {e}")

            # 통계 업데이트
            self.total_collected += collected
            cycle_duration = time.time() - cycle_start

            logger.info("\n" + "=" * 60)
            logger.info(f"📊 사이클 #{self.collection_count} 완료")
            logger.info(f"   수집: {collected}개, 백테스트: {backtested}개")
            logger.info(f"   누적: 총 {self.total_collected}개 수집, {self.total_backtested}개 백테스트")
            logger.info("=" * 60)

            # 상위 전략 정보
            top_strategies = []
            if strategies:
                sorted_strategies = sorted(strategies, key=lambda x: x.boosts, reverse=True)[:5]
                for s in sorted_strategies:
                    top_strategies.append({
                        'title': s.title,
                        'boosts': s.boosts,
                        'author': s.author
                    })
                logger.info("\n🏆 이번 수집 상위 5개:")
                for i, s in enumerate(sorted_strategies, 1):
                    logger.info(f"   {i}. {s.boosts:,} 부스트 | {s.title[:40]}")

            # 수집 완료 알림
            if self.telegram:
                await self.telegram.notify_collection_complete(
                    cycle_num=self.collection_count,
                    collected=collected,
                    with_code=len(strategies_with_code),
                    top_strategies=top_strategies,
                    duration_sec=cycle_duration
                )

            # 백테스트 결과 알림
            if backtest_results and self.telegram:
                # 수익률 순으로 정렬
                sorted_results = sorted(backtest_results, key=lambda x: x.total_return, reverse=True)
                top_performers = sorted_results[:5]

                await self.telegram.notify_backtest_complete(
                    total_tested=len(strategies_with_code),
                    successful=backtested,
                    top_performers=top_performers
                )

                # 수익성 높은 전략 개별 알림 (20% 이상)
                for result in sorted_results:
                    if result.total_return >= 20:
                        await self.telegram.notify_profitable_strategy(result)

            # 연속 오류 카운트 리셋
            self.consecutive_errors = 0
            self.last_error = None

            return collected

        except Exception as e:
            self.consecutive_errors += 1
            self.last_error = str(e)
            error_trace = traceback.format_exc()

            logger.error(f"❌ 수집 사이클 실패: {e}", exc_info=True)

            # 상세 오류 알림
            if self.telegram:
                await self.telegram.notify_error(
                    error_type="수집 사이클 실패",
                    error_msg=str(e),
                    context=f"사이클 #{self.collection_count}\n연속 오류: {self.consecutive_errors}회\n\n{error_trace[:500]}"
                )

                # 연속 오류가 3회 이상이면 심각한 알림
                if self.consecutive_errors >= 3:
                    await self.telegram.send_message(
                        f"🚨 <b>긴급: 연속 {self.consecutive_errors}회 오류 발생!</b>\n\n"
                        f"서비스에 심각한 문제가 있을 수 있습니다.\n"
                        f"마지막 오류: {self.last_error}\n\n"
                        f"<i>서버 상태를 확인해주세요.</i>"
                    )

            return 0

    async def _extract_pine_codes(self, strategies: List[StrategyData]) -> List[StrategyData]:
        """Pine Script 코드 추출"""
        fetcher = PineCodeFetcher()
        strategies_with_code = []
        failed_count = 0

        for i, strategy in enumerate(strategies, 1):
            try:
                logger.info(f"   [{i}/{len(strategies)}] {strategy.title[:40]}...")

                result = await fetcher.fetch_pine_code(strategy.script_url)

                if result.pine_code and not result.is_protected:
                    strategy.pine_code = result.pine_code
                    strategy.pine_version = result.pine_version
                    strategies_with_code.append(strategy)
                    logger.info(f"      ✅ 코드 추출 성공 ({len(result.pine_code)} bytes, v{result.pine_version})")
                else:
                    logger.warning(f"      ⚠️ 코드 없음 (비공개 또는 보호됨)")
                    failed_count += 1

                await asyncio.sleep(1)

            except Exception as e:
                logger.error(f"      ❌ 추출 실패: {e}")
                failed_count += 1

        # 추출 실패율이 높으면 경고
        if len(strategies) > 0 and failed_count / len(strategies) > 0.5:
            if self.telegram:
                await self.telegram.notify_error(
                    "코드 추출 경고",
                    f"추출 성공률이 낮습니다: {len(strategies_with_code)}/{len(strategies)} ({100-failed_count/len(strategies)*100:.0f}%)",
                    "TradingView API 접근에 문제가 있을 수 있습니다."
                )

        return strategies_with_code

    async def _save_to_database(self, strategies: List[StrategyData]):
        """데이터베이스에 저장 (컨텍스트 매니저 사용)"""
        try:
            # 리소스 관리: 컨텍스트 매니저로 자동 정리
            async with StrategyDatabase(self.db_path) as db:
                saved = 0
                failed = 0
                for strategy in strategies:
                    try:
                        await db.upsert_strategy({
                            'script_id': strategy.script_id,
                            'title': strategy.title,
                            'author': strategy.author,
                            'likes': strategy.boosts,
                            'script_url': strategy.script_url,
                            'pine_code': strategy.pine_code,
                            'pine_version': strategy.pine_version,
                            'is_open_source': True
                        })
                        saved += 1
                    except Exception as e:
                        logger.error(f"   ❌ 저장 실패 ({strategy.title}): {e}")
                        failed += 1

                logger.info(f"✅ DB 저장 완료: {saved}개 (실패: {failed}개)")

                if failed > 0 and self.telegram:
                    await self.telegram.notify_error(
                        "DB 저장 경고",
                        f"{failed}개 전략 저장 실패",
                        f"성공: {saved}개"
                    )

        except Exception as e:
            logger.error(f"❌ DB 저장 오류: {e}")
            raise

    async def _analyze_strategies(self, strategies: List[StrategyData]) -> int:
        """AI 품질 분석 및 analysis_json 생성 (컨텍스트 매니저 사용)"""
        import json
        from dataclasses import asdict

        analyzer = StrategyAnalyzer(headless=True)
        analyzed_count = 0

        # 리소스 관리: 컨텍스트 매니저로 자동 정리
        async with StrategyDatabase(self.db_path) as db:
            for i, strategy in enumerate(strategies, 1):
                if not hasattr(strategy, 'pine_code') or not strategy.pine_code:
                    logger.info(f"   [{i}/{len(strategies)}] {strategy.title[:35]}... ⚠️ 코드 없음, 스킵")
                    continue

                try:
                    logger.info(f"   [{i}/{len(strategies)}] {strategy.title[:35]}... 분석 중")

                    # StrategyAnalyzer에 필요한 형식으로 변환
                    strategy_dict = {
                        'scriptId': strategy.script_id,
                        'title': strategy.title,
                        'author': strategy.author,
                        'likes': strategy.boosts,
                        'href': strategy.script_url
                    }

                    # AI 분석 실행
                    analysis = await analyzer.analyze_strategy(strategy_dict)

                    # 등급 계산 (A, B, C, D, F)
                    total_score = analysis.total_score
                    if total_score >= 80:
                        grade = 'A'
                    elif total_score >= 70:
                        grade = 'B'
                    elif total_score >= 60:
                        grade = 'C'
                    elif total_score >= 50:
                        grade = 'D'
                    else:
                        grade = 'F'

                    # analysis_json 생성
                    analysis_json = {
                        'grade': grade,
                        'total_score': round(total_score, 1),
                        'code_score': round(analysis.code_score, 1),
                        'performance_score': round(analysis.performance_score, 1),
                        'quality_score': round(analysis.quality_score, 1),
                        'repainting_score': 100 - len(analysis.repainting_issues) * 10,
                        'overfitting_score': 100 - len(analysis.overfitting_issues) * 10,
                        'repainting_issues': analysis.repainting_issues,
                        'overfitting_issues': analysis.overfitting_issues,
                        'analyzed_at': datetime.now().isoformat()
                    }

                    # DB 업데이트: 필수 필드 포함, analysis는 딕셔너리로 전달 (json.dumps 제거)
                    await db.upsert_strategy({
                        'script_id': strategy.script_id,
                        'title': strategy.title,
                        'author': strategy.author,
                        'likes': strategy.boosts,
                        'script_url': strategy.script_url,
                        'analysis': analysis_json  # json.dumps 제거 (DB 레이어에서 처리)
                    })

                    analyzed_count += 1
                    logger.info(f"      ✅ 등급: {grade} (점수: {total_score:.1f})")

                    await asyncio.sleep(0.5)  # Rate limiting

                except Exception as e:
                    logger.error(f"      ❌ 분석 실패: {e}")

        return analyzed_count

    async def _run_backtests(self, strategies: List[StrategyData]) -> tuple[int, List[BacktestResult]]:
        """백테스트 실행"""
        tester = StrategyTester(self.db_path)
        backtested = 0
        results = []

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
                    total_return = backtest.get('total_return', 0)
                    win_rate = backtest.get('win_rate', 0)
                    max_drawdown = backtest.get('max_drawdown', 0)
                    sharpe = backtest.get('sharpe_ratio', 0)
                    trades = backtest.get('total_trades', 0)

                    logger.info(f"      ✅ 수익률: {total_return:.1f}%, "
                              f"승률: {win_rate:.1f}%, "
                              f"MDD: {max_drawdown:.1f}%")

                    results.append(BacktestResult(
                        strategy_name=strategy.title,
                        total_return=total_return,
                        win_rate=win_rate,
                        max_drawdown=max_drawdown,
                        sharpe_ratio=sharpe,
                        trades=trades
                    ))
                    backtested += 1
                else:
                    logger.warning(f"      ⚠️ 실패: {result.get('error', 'Unknown')}")

                await asyncio.sleep(0.5)

            except Exception as e:
                logger.error(f"      ❌ 백테스트 오류: {e}")

        return backtested, results

    async def _generate_report(self):
        """HTML 리포트 생성"""
        try:
            from scripts.generate_beginner_report import generate_beginner_report

            output_path = project_root / "data" / "beginner_report.html"
            # await 추가: 비동기 함수 호출 누락 수정
            await generate_beginner_report(self.db_path, str(output_path))
            logger.info(f"✅ HTML 리포트 생성: {output_path}")

        except Exception as e:
            logger.error(f"❌ 리포트 생성 실패: {e}")

    async def _send_server_status(self):
        """서버 상태 알림 (컨텍스트 매니저 사용)"""
        try:
            # 리소스 관리: 컨텍스트 매니저로 자동 정리
            async with StrategyDatabase(self.db_path) as db:
                # DB 통계 가져오기 (타입 불일치 수정: 객체 속성 접근)
                stats = await db.get_stats()
                total = stats.total_strategies
                analyzed = stats.analyzed_count
                passed = stats.passed_count

                # DB 파일 크기
                db_file = Path(self.db_path)
                db_size_mb = db_file.stat().st_size / (1024 * 1024) if db_file.exists() else 0

                # 가동 시간
                uptime = datetime.now() - self.start_time
                uptime_hours = uptime.total_seconds() / 3600

                if self.telegram:
                    await self.telegram.notify_server_status(
                        total_strategies=total,
                        analyzed_count=analyzed,
                        passed_count=passed,
                        db_size_mb=db_size_mb,
                        uptime_hours=uptime_hours
                    )
        except Exception as e:
            logger.error(f"서버 상태 알림 실패: {e}")

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

        # 서비스 시작 알림
        if self.telegram:
            await self.telegram.notify_service_start()

        # 매 6시간마다 서버 상태 알림을 위한 카운터
        status_interval = 4  # 4 사이클마다 (24시간)

        while self.running:
            try:
                # 수집 + 백테스트 실행
                await self.run_collection()

                # 주기적으로 서버 상태 알림 (매일 1회)
                if self.collection_count % status_interval == 0:
                    await self._send_server_status()

                # 다음 수집까지 대기
                next_run = datetime.now() + self.collect_interval
                hours_remaining = self.collect_interval.total_seconds() / 3600

                logger.info(f"\n⏰ 다음 수집: {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
                logger.info(f"   {self.collect_interval} 후 재실행\n")

                # 다음 수집 예정 알림
                if self.telegram:
                    await self.telegram.notify_next_collection(next_run, hours_remaining)

                await asyncio.sleep(self.collect_interval.total_seconds())

            except asyncio.CancelledError:
                logger.info("🛑 서비스 중지 요청")
                if self.telegram:
                    await self.telegram.notify_service_stop("사용자 요청으로 중지")
                break
            except Exception as e:
                logger.error(f"❌ 오류 발생: {e}", exc_info=True)

                # 오류 알림
                if self.telegram:
                    await self.telegram.notify_error(
                        "서비스 루프 오류",
                        str(e),
                        f"1시간 후 재시도 예정\n연속 오류: {self.consecutive_errors}회"
                    )

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
    parser.add_argument('--test-telegram', action='store_true', help='텔레그램 연결 테스트')
    args = parser.parse_args()

    # 텔레그램 테스트
    if args.test_telegram:
        if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
            print("❌ 텔레그램 환경변수가 설정되지 않았습니다.")
            print("   TELEGRAM_BOT_TOKEN과 TELEGRAM_CHAT_ID를 설정해주세요.")
            return

        notifier = TelegramNotifier(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)
        await notifier.send_message(
            "🔔 <b>텔레그램 알림 테스트</b>\n\n"
            "연결이 정상적으로 설정되었습니다! ✅"
        )
        print("✅ 텔레그램 테스트 완료")
        return

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
            if service.telegram:
                await service.telegram.notify_service_stop("키보드 인터럽트")
            logger.info("👋 서비스 종료")


if __name__ == '__main__':
    asyncio.run(main())
