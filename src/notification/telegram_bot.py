#!/usr/bin/env python3
"""
Telegram 알림 모듈

전략 수집, 백테스트 결과, 서버 상태 등을 텔레그램으로 알림
"""

import asyncio
import aiohttp
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
import os

logger = logging.getLogger(__name__)


@dataclass
class BacktestResult:
    """백테스트 결과"""
    strategy_name: str
    total_return: float
    win_rate: float
    max_drawdown: float
    sharpe_ratio: float = 0.0
    trades: int = 0


class TelegramNotifier:
    """텔레그램 알림 발송기"""

    def __init__(
        self,
        bot_token: str = None,
        chat_id: str = None
    ):
        self.bot_token = bot_token or os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = chat_id or os.getenv("TELEGRAM_CHAT_ID")
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"

    async def send_message(self, text: str, parse_mode: str = "HTML") -> bool:
        """텔레그램 메시지 발송"""
        if not self.bot_token or not self.chat_id:
            logger.warning("Telegram credentials not configured")
            return False

        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/sendMessage"
                payload = {
                    "chat_id": self.chat_id,
                    "text": text,
                    "parse_mode": parse_mode,
                    "disable_web_page_preview": True
                }
                async with session.post(url, json=payload) as resp:
                    if resp.status == 200:
                        logger.info("Telegram message sent successfully")
                        return True
                    else:
                        error = await resp.text()
                        logger.error(f"Telegram API error: {error}")
                        return False
        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}")
            return False

    # =========================================================================
    # 서비스 시작/종료 알림
    # =========================================================================

    async def notify_service_start(self):
        """서비스 시작 알림"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        message = f"""
🚀 <b>전략 수집 서비스 시작</b>

⏰ 시작 시간: {now}
📊 수집 주기: 6시간마다
🎯 목표: 100개 전략 (500+ 부스트)
📈 백테스트: Binance BTC/USDT 1H

<i>24시간 자동 수집이 시작되었습니다.</i>
"""
        return await self.send_message(message.strip())

    async def notify_service_stop(self, reason: str = "정상 종료"):
        """서비스 종료 알림"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        message = f"""
🛑 <b>전략 수집 서비스 종료</b>

⏰ 종료 시간: {now}
📝 사유: {reason}
"""
        return await self.send_message(message.strip())

    # =========================================================================
    # 수집 결과 알림
    # =========================================================================

    async def notify_collection_start(self, cycle_num: int):
        """수집 사이클 시작 알림"""
        now = datetime.now().strftime("%H:%M:%S")
        message = f"""
📥 <b>수집 사이클 #{cycle_num} 시작</b>

⏰ 시작: {now}
🔍 TradingView 전략 수집 중...
"""
        return await self.send_message(message.strip())

    async def notify_collection_complete(
        self,
        cycle_num: int,
        collected: int,
        with_code: int,
        top_strategies: List[Dict[str, Any]] = None,
        duration_sec: float = 0
    ):
        """수집 완료 알림"""
        now = datetime.now().strftime("%H:%M:%S")

        # 상위 전략 목록
        top_list = ""
        if top_strategies:
            top_list = "\n\n🏆 <b>상위 5개 전략:</b>\n"
            for i, s in enumerate(top_strategies[:5], 1):
                boosts = s.get('boosts', s.get('likes', 0))
                title = s.get('title', '')[:35]
                top_list += f"  {i}. {boosts:,} 부스트 | {title}\n"

        duration_min = duration_sec / 60 if duration_sec else 0

        message = f"""
✅ <b>수집 사이클 #{cycle_num} 완료</b>

📊 <b>수집 결과:</b>
  • 수집된 전략: {collected}개
  • 코드 추출 성공: {with_code}개
  • 소요 시간: {duration_min:.1f}분
{top_list}
⏰ 완료: {now}
"""
        return await self.send_message(message.strip())

    # =========================================================================
    # 백테스트 결과 알림
    # =========================================================================

    async def notify_backtest_complete(
        self,
        total_tested: int,
        successful: int,
        top_performers: List[BacktestResult] = None
    ):
        """백테스트 완료 알림"""

        # 상위 성과 전략
        top_list = ""
        if top_performers:
            top_list = "\n\n🥇 <b>최고 성과 전략:</b>\n"
            for i, result in enumerate(top_performers[:5], 1):
                emoji = "🟢" if result.total_return > 0 else "🔴"
                top_list += (
                    f"  {i}. {result.strategy_name[:30]}\n"
                    f"     {emoji} 수익률: {result.total_return:+.1f}% | "
                    f"승률: {result.win_rate:.0f}% | "
                    f"MDD: {result.max_drawdown:.1f}%\n"
                )

        success_rate = (successful / total_tested * 100) if total_tested > 0 else 0

        message = f"""
🧪 <b>백테스트 완료</b>

📊 <b>결과 요약:</b>
  • 테스트 전략: {total_tested}개
  • 성공: {successful}개 ({success_rate:.0f}%)
{top_list}
"""
        return await self.send_message(message.strip())

    async def notify_profitable_strategy(self, result: BacktestResult):
        """수익성 높은 전략 발견 알림"""
        if result.total_return < 10:  # 10% 미만은 알림 안함
            return False

        emoji = "🚀" if result.total_return > 50 else "📈"

        message = f"""
{emoji} <b>수익성 높은 전략 발견!</b>

📌 <b>{result.strategy_name}</b>

📊 <b>백테스트 결과:</b>
  • 수익률: <b>{result.total_return:+.1f}%</b>
  • 승률: {result.win_rate:.1f}%
  • 최대 손실폭: {result.max_drawdown:.1f}%
  • 샤프 비율: {result.sharpe_ratio:.2f}
  • 거래 횟수: {result.trades}회

<i>자세한 내용은 API에서 확인하세요.</i>
"""
        return await self.send_message(message.strip())

    # =========================================================================
    # 서버 상태 알림
    # =========================================================================

    async def notify_server_status(
        self,
        total_strategies: int,
        analyzed_count: int,
        passed_count: int,
        db_size_mb: float = 0,
        uptime_hours: float = 0
    ):
        """서버 상태 리포트"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        message = f"""
📡 <b>서버 상태 리포트</b>

⏰ 시간: {now}

📊 <b>데이터베이스:</b>
  • 총 전략: {total_strategies:,}개
  • 분석 완료: {analyzed_count:,}개
  • 권장 전략: {passed_count}개
  • DB 크기: {db_size_mb:.1f}MB

⏱ 가동 시간: {uptime_hours:.1f}시간
"""
        return await self.send_message(message.strip())

    async def notify_error(self, error_type: str, error_msg: str, context: str = ""):
        """오류 알림"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        message = f"""
⚠️ <b>오류 발생</b>

⏰ 시간: {now}
🔴 유형: {error_type}
📝 내용: {error_msg}
"""
        if context:
            message += f"📍 컨텍스트: {context}\n"

        return await self.send_message(message.strip())

    # =========================================================================
    # 일일 리포트
    # =========================================================================

    async def notify_daily_report(
        self,
        date: str,
        total_collected: int,
        total_backtested: int,
        new_profitable: int,
        top_strategy: Optional[BacktestResult] = None
    ):
        """일일 리포트"""

        top_info = ""
        if top_strategy:
            top_info = f"""
🥇 <b>오늘의 최고 전략:</b>
  {top_strategy.strategy_name}
  수익률: {top_strategy.total_return:+.1f}% | 승률: {top_strategy.win_rate:.0f}%
"""

        message = f"""
📅 <b>일일 리포트 - {date}</b>

📊 <b>오늘의 수집 현황:</b>
  • 수집된 전략: {total_collected}개
  • 백테스트 완료: {total_backtested}개
  • 수익성 전략 발견: {new_profitable}개
{top_info}
<i>내일도 좋은 전략을 찾아드리겠습니다! 💪</i>
"""
        return await self.send_message(message.strip())

    # =========================================================================
    # 다음 수집 예정 알림
    # =========================================================================

    async def notify_next_collection(self, next_time: datetime, hours_remaining: float):
        """다음 수집 예정 알림"""
        next_str = next_time.strftime("%Y-%m-%d %H:%M:%S")

        message = f"""
⏰ <b>다음 수집 예정</b>

📅 예정 시간: {next_str}
⏳ 남은 시간: {hours_remaining:.1f}시간
"""
        return await self.send_message(message.strip())


# =========================================================================
# 테스트
# =========================================================================

async def test_telegram():
    """텔레그램 연결 테스트"""
    notifier = TelegramNotifier(
        bot_token="8327452496:AAFwrVohBY-9dVoo8D7mXHqGLEDXMOCJK_M",
        chat_id="7980845952"
    )

    # 테스트 메시지
    success = await notifier.send_message(
        "🔔 <b>전략 연구소 알림 테스트</b>\n\n"
        "텔레그램 알림이 정상적으로 설정되었습니다! ✅"
    )

    if success:
        print("✅ 텔레그램 연결 성공!")
    else:
        print("❌ 텔레그램 연결 실패")

    return success


if __name__ == "__main__":
    asyncio.run(test_telegram())
