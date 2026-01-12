#!/usr/bin/env python3
"""
Notification System - 알림 시스템

텔레그램, 이메일 등 다양한 채널로 알림을 전송합니다.
"""

import os
import asyncio
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


class NotificationType(Enum):
    """알림 유형"""
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    TRADE = "trade"
    SIGNAL = "signal"


@dataclass
class NotificationConfig:
    """알림 설정"""
    telegram_enabled: bool = True
    telegram_bot_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    
    # 알림 필터
    min_level: NotificationType = NotificationType.INFO
    trade_alerts: bool = True
    error_alerts: bool = True
    daily_summary: bool = True
    
    # Rate limiting
    max_messages_per_minute: int = 20
    cooldown_seconds: int = 1


class TelegramNotifier:
    """텔레그램 알림 전송"""
    
    BASE_URL = "https://api.telegram.org/bot{token}"
    
    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.base_url = self.BASE_URL.format(token=bot_token)
        self._message_count = 0
        self._last_reset = datetime.now()
        
    def _check_rate_limit(self, max_per_minute: int = 20) -> bool:
        """Rate limit 체크"""
        now = datetime.now()
        if (now - self._last_reset).seconds >= 60:
            self._message_count = 0
            self._last_reset = now
            
        if self._message_count >= max_per_minute:
            return False
            
        self._message_count += 1
        return True
    
    def _format_message(
        self,
        message: str,
        notification_type: NotificationType = NotificationType.INFO,
        title: Optional[str] = None,
    ) -> str:
        """메시지 포맷팅"""
        emoji_map = {
            NotificationType.INFO: "ℹ️",
            NotificationType.SUCCESS: "✅",
            NotificationType.WARNING: "⚠️",
            NotificationType.ERROR: "❌",
            NotificationType.TRADE: "💰",
            NotificationType.SIGNAL: "📊",
        }
        
        emoji = emoji_map.get(notification_type, "📌")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        formatted = f"{emoji} "
        if title:
            formatted += f"<b>{title}</b>\n\n"
        formatted += f"{message}\n\n"
        formatted += f"<i>🕐 {timestamp}</i>"
        
        return formatted
    
    def send_sync(
        self,
        message: str,
        notification_type: NotificationType = NotificationType.INFO,
        title: Optional[str] = None,
        parse_mode: str = "HTML",
    ) -> bool:
        """동기 메시지 전송"""
        if not REQUESTS_AVAILABLE:
            print("Error: requests not installed")
            return False
            
        if not self._check_rate_limit():
            print("Rate limit exceeded")
            return False
            
        formatted_message = self._format_message(message, notification_type, title)
        
        try:
            response = requests.post(
                f"{self.base_url}/sendMessage",
                data={
                    "chat_id": self.chat_id,
                    "text": formatted_message,
                    "parse_mode": parse_mode,
                },
                timeout=10,
            )
            return response.status_code == 200
        except Exception as e:
            print(f"Telegram send error: {e}")
            return False
    
    async def send_async(
        self,
        message: str,
        notification_type: NotificationType = NotificationType.INFO,
        title: Optional[str] = None,
        parse_mode: str = "HTML",
    ) -> bool:
        """비동기 메시지 전송"""
        if not AIOHTTP_AVAILABLE:
            return self.send_sync(message, notification_type, title, parse_mode)
            
        if not self._check_rate_limit():
            print("Rate limit exceeded")
            return False
            
        formatted_message = self._format_message(message, notification_type, title)
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/sendMessage",
                    data={
                        "chat_id": self.chat_id,
                        "text": formatted_message,
                        "parse_mode": parse_mode,
                    },
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as response:
                    return response.status == 200
        except Exception as e:
            print(f"Telegram send error: {e}")
            return False


class NotificationSystem:
    """
    통합 알림 시스템
    
    Features:
    - 텔레그램 알림
    - 알림 유형별 필터링
    - Rate limiting
    - 비동기/동기 지원
    """
    
    def __init__(self, config: Optional[NotificationConfig] = None):
        self.config = config or self._load_config_from_env()
        self._telegram: Optional[TelegramNotifier] = None
        self._init_notifiers()
        
    def _load_config_from_env(self) -> NotificationConfig:
        """환경변수에서 설정 로드"""
        return NotificationConfig(
            telegram_enabled=os.getenv("TELEGRAM_ENABLED", "true").lower() == "true",
            telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN"),
            telegram_chat_id=os.getenv("TELEGRAM_CHAT_ID"),
            trade_alerts=os.getenv("TRADE_ALERTS", "true").lower() == "true",
            error_alerts=os.getenv("ERROR_ALERTS", "true").lower() == "true",
        )
    
    def _init_notifiers(self):
        """알림 채널 초기화"""
        if (
            self.config.telegram_enabled
            and self.config.telegram_bot_token
            and self.config.telegram_chat_id
        ):
            self._telegram = TelegramNotifier(
                self.config.telegram_bot_token,
                self.config.telegram_chat_id,
            )
    
    def send(
        self,
        message: str,
        notification_type: NotificationType = NotificationType.INFO,
        title: Optional[str] = None,
    ) -> bool:
        """동기 알림 전송"""
        if self._telegram:
            return self._telegram.send_sync(message, notification_type, title)
        return False
    
    async def send_async(
        self,
        message: str,
        notification_type: NotificationType = NotificationType.INFO,
        title: Optional[str] = None,
    ) -> bool:
        """비동기 알림 전송"""
        if self._telegram:
            return await self._telegram.send_async(message, notification_type, title)
        return False
    
    # 편의 메서드들
    def info(self, message: str, title: Optional[str] = None) -> bool:
        return self.send(message, NotificationType.INFO, title)
    
    def success(self, message: str, title: Optional[str] = None) -> bool:
        return self.send(message, NotificationType.SUCCESS, title)
    
    def warning(self, message: str, title: Optional[str] = None) -> bool:
        return self.send(message, NotificationType.WARNING, title)
    
    def error(self, message: str, title: Optional[str] = None) -> bool:
        if self.config.error_alerts:
            return self.send(message, NotificationType.ERROR, title)
        return False
    
    def trade(self, message: str, title: Optional[str] = None) -> bool:
        if self.config.trade_alerts:
            return self.send(message, NotificationType.TRADE, title)
        return False
    
    def signal(self, message: str, title: Optional[str] = None) -> bool:
        return self.send(message, NotificationType.SIGNAL, title)
    
    def send_trade_alert(
        self,
        action: str,  # "BUY" or "SELL"
        symbol: str,
        price: float,
        amount: float,
        reason: Optional[str] = None,
    ) -> bool:
        """거래 알림 전송"""
        emoji = "🟢" if action.upper() == "BUY" else "🔴"
        
        message = f"{emoji} <b>{action.upper()}</b> {symbol}\n"
        message += f"💵 Price: ${price:,.2f}\n"
        message += f"📊 Amount: {amount:.4f}\n"
        if reason:
            message += f"📝 Reason: {reason}"
            
        return self.trade(message, title="Trade Executed")
    
    def send_daily_summary(
        self,
        total_trades: int,
        win_rate: float,
        pnl: float,
        pnl_percent: float,
    ) -> bool:
        """일일 요약 전송"""
        emoji = "📈" if pnl >= 0 else "📉"
        
        message = f"📊 <b>Daily Trading Summary</b>\n\n"
        message += f"🔢 Total Trades: {total_trades}\n"
        message += f"🎯 Win Rate: {win_rate:.1f}%\n"
        message += f"{emoji} P&L: ${pnl:,.2f} ({pnl_percent:+.2f}%)"
        
        return self.info(message, title="Daily Summary")


# 싱글톤 인스턴스
_notification_system: Optional[NotificationSystem] = None


def get_notification_system() -> NotificationSystem:
    """Notification System 싱글톤 인스턴스 반환"""
    global _notification_system
    if _notification_system is None:
        _notification_system = NotificationSystem()
    return _notification_system


# ============================================================
# Telegram Bot Commands (6.2.4)
# ============================================================

class TelegramBotCommands:
    """
    텔레그램 봇 명령어 처리
    
    지원 명령어:
    - /status: 트레이딩 상태 조회
    - /stop: 긴급 정지
    - /start: 트레이딩 시작
    - /stats: 거래 통계
    - /help: 도움말
    """
    
    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
        self._last_update_id = 0
        self._running = False
        
    def _send_message(self, text: str, parse_mode: str = "HTML") -> bool:
        """메시지 전송"""
        if not REQUESTS_AVAILABLE:
            return False
            
        try:
            response = requests.post(
                f"{self.base_url}/sendMessage",
                data={
                    "chat_id": self.chat_id,
                    "text": text,
                    "parse_mode": parse_mode,
                },
                timeout=10,
            )
            return response.status_code == 200
        except Exception as e:
            print(f"Telegram send error: {e}")
            return False
    
    def _get_updates(self) -> List[Dict[str, Any]]:
        """업데이트 가져오기"""
        if not REQUESTS_AVAILABLE:
            return []
            
        try:
            response = requests.get(
                f"{self.base_url}/getUpdates",
                params={
                    "offset": self._last_update_id + 1,
                    "timeout": 30,
                },
                timeout=35,
            )
            if response.status_code == 200:
                data = response.json()
                return data.get("result", [])
        except Exception as e:
            print(f"Telegram get updates error: {e}")
        return []
    
    def _handle_command(self, command: str, message_text: str) -> str:
        """명령어 처리"""
        try:
            if command == "/status":
                return self._cmd_status()
            elif command == "/stop":
                return self._cmd_stop(message_text)
            elif command == "/start":
                return self._cmd_start()
            elif command == "/stats":
                return self._cmd_stats()
            elif command == "/help":
                return self._cmd_help()
            else:
                return f"❓ 알 수 없는 명령어: {command}\n\n/help 로 도움말을 확인하세요."
        except Exception as e:
            return f"❌ 명령어 처리 오류: {str(e)}"
    
    def _cmd_status(self) -> str:
        """상태 조회 명령어"""
        try:
            from src.trading.live_safeguards import get_safeguards
            
            safeguards = get_safeguards()
            status = safeguards.get_status()
            
            state_emoji = {
                "running": "🟢",
                "paused": "🟡",
                "stopped": "🔴",
                "emergency_stop": "🚨",
            }
            
            emoji = state_emoji.get(status["state"], "❓")
            
            msg = f"{emoji} <b>트레이딩 상태</b>\n\n"
            msg += f"📊 상태: {status['state'].upper()}\n"
            msg += f"🔄 거래 가능: {'예' if status['can_trade'] else '아니오'}\n"
            
            if not status['can_trade']:
                msg += f"📝 사유: {status['reason']}\n"
            
            metrics = status.get("metrics", {})
            msg += f"\n📈 <b>오늘 통계</b>\n"
            msg += f"• 총 거래: {metrics.get('total_trades', 0)}회\n"
            msg += f"• 승률: {metrics.get('win_rate', 0):.1f}%\n"
            msg += f"• 일일 PnL: ${metrics.get('daily_pnl', 0):,.2f}\n"
            msg += f"• 잔고: ${metrics.get('current_balance', 0):,.2f}\n"
            
            return msg
            
        except ImportError:
            return "❌ 트레이딩 시스템을 사용할 수 없습니다."
        except Exception as e:
            return f"❌ 상태 조회 오류: {str(e)}"
    
    def _cmd_stop(self, message_text: str) -> str:
        """긴급 정지 명령어"""
        try:
            from src.trading.live_safeguards import get_safeguards
            
            # 사유 추출
            parts = message_text.split(maxsplit=1)
            reason = parts[1] if len(parts) > 1 else "Telegram 긴급 정지"
            
            safeguards = get_safeguards()
            safeguards.emergency_stop(reason)
            
            return f"🚨 <b>긴급 정지 활성화</b>\n\n📝 사유: {reason}\n\n⚠️ 모든 거래가 중지되었습니다.\n재시작: /start"
            
        except ImportError:
            return "❌ 트레이딩 시스템을 사용할 수 없습니다."
        except Exception as e:
            return f"❌ 긴급 정지 오류: {str(e)}"
    
    def _cmd_start(self) -> str:
        """트레이딩 시작 명령어"""
        try:
            from src.trading.live_safeguards import get_safeguards
            
            safeguards = get_safeguards()
            
            # 긴급 정지 상태면 먼저 해제
            if safeguards._emergency_stop_flag:
                safeguards.reset_emergency_stop()
            
            if safeguards.start():
                return "🟢 <b>트레이딩 시작</b>\n\n✅ 거래가 활성화되었습니다.\n상태 확인: /status"
            else:
                return "❌ 트레이딩을 시작할 수 없습니다.\n상태 확인: /status"
            
        except ImportError:
            return "❌ 트레이딩 시스템을 사용할 수 없습니다."
        except Exception as e:
            return f"❌ 시작 오류: {str(e)}"
    
    def _cmd_stats(self) -> str:
        """거래 통계 명령어"""
        try:
            from src.logging.trade_logger import get_trade_logger
            
            trade_logger = get_trade_logger()
            stats = trade_logger.get_statistics()
            
            msg = "📊 <b>거래 통계</b>\n\n"
            msg += f"🔢 총 거래: {stats.get('total_trades', 0)}회\n"
            msg += f"✅ 승리: {stats.get('winning_trades', 0)}회\n"
            msg += f"❌ 패배: {stats.get('losing_trades', 0)}회\n"
            msg += f"🎯 승률: {stats.get('win_rate', 0):.1f}%\n"
            msg += f"\n💰 <b>손익</b>\n"
            msg += f"• 총 PnL: ${stats.get('total_pnl', 0):,.2f}\n"
            msg += f"• 평균 PnL: ${stats.get('avg_pnl', 0):,.2f}\n"
            msg += f"• 최대 수익: ${stats.get('max_win', 0):,.2f}\n"
            msg += f"• 최대 손실: ${stats.get('max_loss', 0):,.2f}\n"
            msg += f"• Profit Factor: {stats.get('profit_factor', 0):.2f}\n"
            
            return msg
            
        except ImportError:
            return "❌ 거래 로거를 사용할 수 없습니다."
        except Exception as e:
            return f"❌ 통계 조회 오류: {str(e)}"
    
    def _cmd_help(self) -> str:
        """도움말 명령어"""
        return """📖 <b>Strategy Research Lab 봇 명령어</b>

🔹 <b>트레이딩 제어</b>
/status - 현재 트레이딩 상태 조회
/start - 트레이딩 시작
/stop [사유] - 긴급 정지

🔹 <b>통계</b>
/stats - 거래 통계 조회

🔹 <b>기타</b>
/help - 이 도움말 표시

⚠️ <b>주의</b>: /stop 명령어는 즉시 모든 거래를 중지합니다."""
    
    def process_updates(self):
        """업데이트 처리 (한 번 실행)"""
        updates = self._get_updates()
        
        for update in updates:
            self._last_update_id = update.get("update_id", self._last_update_id)
            
            message = update.get("message", {})
            text = message.get("text", "")
            chat_id = message.get("chat", {}).get("id")
            
            # 허용된 채팅 ID만 처리
            if str(chat_id) != str(self.chat_id):
                continue
            
            # 명령어 처리
            if text.startswith("/"):
                command = text.split()[0].lower()
                response = self._handle_command(command, text)
                self._send_message(response)
    
    def run_polling(self, interval: int = 1):
        """폴링 모드로 실행"""
        import time
        
        self._running = True
        print(f"Telegram bot polling started (interval: {interval}s)")
        
        while self._running:
            try:
                self.process_updates()
                time.sleep(interval)
            except KeyboardInterrupt:
                print("Telegram bot polling stopped")
                break
            except Exception as e:
                print(f"Polling error: {e}")
                time.sleep(5)
    
    def stop_polling(self):
        """폴링 중지"""
        self._running = False


# 텔레그램 봇 싱글톤
_telegram_bot: Optional[TelegramBotCommands] = None


def get_telegram_bot() -> Optional[TelegramBotCommands]:
    """Telegram Bot 싱글톤 인스턴스 반환"""
    global _telegram_bot
    if _telegram_bot is None:
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        chat_id = os.getenv("TELEGRAM_CHAT_ID")
        if bot_token and chat_id:
            _telegram_bot = TelegramBotCommands(bot_token, chat_id)
    return _telegram_bot


if __name__ == "__main__":
    # 테스트
    notifier = get_notification_system()
    
    print("Testing notification system...")
    
    # 기본 알림 테스트
    if notifier._telegram:
        print("Telegram configured, sending test message...")
        result = notifier.info("This is a test message from NotificationSystem", title="Test")
        print(f"Send result: {result}")
    else:
        print("Telegram not configured. Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID")
        
    # 거래 알림 테스트
    print("\nTrade alert format:")
    print(notifier._telegram._format_message(
        "🟢 BUY BTC/USDT\n💵 Price: $45,000.00\n📊 Amount: 0.1000",
        NotificationType.TRADE,
        "Trade Executed"
    ) if notifier._telegram else "Telegram not configured")
    
    # 텔레그램 봇 명령어 테스트
    print("\n" + "="*50)
    print("Testing Telegram Bot Commands...")
    
    bot = get_telegram_bot()
    if bot:
        print("Telegram bot configured!")
        print("Available commands: /status, /stop, /start, /stats, /help")
        
        # 폴링 모드 실행 (테스트용)
        import sys
        if len(sys.argv) > 1 and sys.argv[1] == "--polling":
            print("\nStarting polling mode (Ctrl+C to stop)...")
            bot.run_polling()
    else:
        print("Telegram bot not configured. Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID")
