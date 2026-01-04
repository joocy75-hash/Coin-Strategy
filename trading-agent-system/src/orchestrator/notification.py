"""
Notification System

파이프라인 실행 결과를 다양한 채널로 알림을 보내는 시스템
- Slack, Telegram, Email, Discord, Webhook 지원
- 비동기 처리로 빠른 알림 전송
- 레벨별 필터링 및 채널별 설정
"""

import asyncio
import logging
import smtplib
from dataclasses import dataclass, field, asdict
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from enum import Enum
from typing import Optional

try:
    import aiohttp
except ImportError:
    aiohttp = None

try:
    import aiosmtplib
except ImportError:
    aiosmtplib = None

from ..backtest.engine import BacktestMetrics

logger = logging.getLogger(__name__)


class NotificationChannel(Enum):
    """알림 채널 타입"""
    SLACK = "slack"
    TELEGRAM = "telegram"
    EMAIL = "email"
    DISCORD = "discord"
    WEBHOOK = "webhook"


class NotificationLevel(Enum):
    """알림 레벨"""
    INFO = 1
    SUCCESS = 2
    WARNING = 3
    ERROR = 4
    CRITICAL = 5


@dataclass
class EmailConfig:
    """이메일 설정"""
    smtp_server: str
    smtp_port: int
    username: str
    password: str
    from_email: str
    to_emails: list[str]
    use_tls: bool = True


@dataclass
class NotificationConfig:
    """알림 채널 설정"""
    channel: NotificationChannel
    enabled: bool = True
    webhook_url: Optional[str] = None
    api_token: Optional[str] = None
    chat_id: Optional[str] = None  # Telegram용
    email_config: Optional[EmailConfig] = None
    min_level: NotificationLevel = NotificationLevel.INFO


@dataclass
class NotificationMessage:
    """알림 메시지"""
    title: str
    body: str
    level: NotificationLevel
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: dict = field(default_factory=dict)

    def get_level_emoji(self) -> str:
        """레벨별 이모지 반환"""
        emoji_map = {
            NotificationLevel.INFO: "ℹ️",
            NotificationLevel.SUCCESS: "✅",
            NotificationLevel.WARNING: "⚠️",
            NotificationLevel.ERROR: "❌",
            NotificationLevel.CRITICAL: "🚨",
        }
        return emoji_map.get(self.level, "📢")

    def get_level_color(self) -> str:
        """레벨별 색상 코드 (Slack, Discord용)"""
        color_map = {
            NotificationLevel.INFO: "#0099ff",
            NotificationLevel.SUCCESS: "#00cc66",
            NotificationLevel.WARNING: "#ffcc00",
            NotificationLevel.ERROR: "#ff3333",
            NotificationLevel.CRITICAL: "#990000",
        }
        return color_map.get(self.level, "#808080")


class NotificationManager:
    """알림 관리자 - 다중 채널 알림 전송"""

    def __init__(self):
        self.channels: dict[NotificationChannel, NotificationConfig] = {}
        self._session: Optional[aiohttp.ClientSession] = None

    def add_channel(self, config: NotificationConfig) -> None:
        """알림 채널 추가"""
        if not config.enabled:
            logger.info(f"채널 {config.channel.value}는 비활성화 상태로 추가됩니다")

        # 채널별 필수 설정 검증
        if config.channel in [NotificationChannel.SLACK, NotificationChannel.DISCORD, NotificationChannel.WEBHOOK]:
            if not config.webhook_url:
                raise ValueError(f"{config.channel.value} 채널에는 webhook_url이 필요합니다")

        elif config.channel == NotificationChannel.TELEGRAM:
            if not config.api_token or not config.chat_id:
                raise ValueError("Telegram 채널에는 api_token과 chat_id가 필요합니다")

        elif config.channel == NotificationChannel.EMAIL:
            if not config.email_config:
                raise ValueError("Email 채널에는 email_config가 필요합니다")

        self.channels[config.channel] = config
        logger.info(f"알림 채널 추가: {config.channel.value}")

    def remove_channel(self, channel: NotificationChannel) -> None:
        """알림 채널 제거"""
        if channel in self.channels:
            del self.channels[channel]
            logger.info(f"알림 채널 제거: {channel.value}")

    async def send(self, message: NotificationMessage) -> dict[NotificationChannel, bool]:
        """모든 활성화된 채널로 알림 전송"""
        results = {}
        tasks = []

        for channel, config in self.channels.items():
            if not config.enabled:
                logger.debug(f"채널 {channel.value}는 비활성화 상태입니다")
                continue

            # 최소 레벨 필터링
            if message.level.value < config.min_level.value:
                logger.debug(f"메시지 레벨이 채널 {channel.value}의 최소 레벨보다 낮습니다")
                continue

            tasks.append(self._send_to_channel_safe(channel, config, message))

        # 병렬 전송
        if tasks:
            send_results = await asyncio.gather(*tasks)
            for channel, success in send_results:
                results[channel] = success

        return results

    async def send_to_channel(
        self,
        channel: NotificationChannel,
        message: NotificationMessage
    ) -> bool:
        """특정 채널로 알림 전송"""
        if channel not in self.channels:
            logger.error(f"등록되지 않은 채널: {channel.value}")
            return False

        config = self.channels[channel]
        if not config.enabled:
            logger.warning(f"비활성화된 채널: {channel.value}")
            return False

        return await self._send_to_channel_impl(config, message)

    async def _send_to_channel_safe(
        self,
        channel: NotificationChannel,
        config: NotificationConfig,
        message: NotificationMessage
    ) -> tuple[NotificationChannel, bool]:
        """안전한 채널 전송 (예외 처리 포함)"""
        try:
            success = await self._send_to_channel_impl(config, message)
            return channel, success
        except Exception as e:
            logger.error(f"채널 {channel.value} 전송 실패: {e}")
            return channel, False

    async def _send_to_channel_impl(
        self,
        config: NotificationConfig,
        message: NotificationMessage
    ) -> bool:
        """채널별 전송 로직 라우팅"""
        try:
            if config.channel == NotificationChannel.SLACK:
                return await self._send_slack(config, message)
            elif config.channel == NotificationChannel.TELEGRAM:
                return await self._send_telegram(config, message)
            elif config.channel == NotificationChannel.EMAIL:
                return await self._send_email(config, message)
            elif config.channel == NotificationChannel.DISCORD:
                return await self._send_discord(config, message)
            elif config.channel == NotificationChannel.WEBHOOK:
                return await self._send_webhook(config, message)
            else:
                logger.error(f"지원하지 않는 채널: {config.channel}")
                return False
        except Exception as e:
            logger.error(f"채널 {config.channel.value} 전송 중 오류: {e}")
            return False

    async def _send_slack(
        self,
        config: NotificationConfig,
        message: NotificationMessage
    ) -> bool:
        """Slack 웹훅 전송"""
        if not aiohttp:
            logger.error("aiohttp 라이브러리가 설치되지 않았습니다")
            return False

        payload = {
            "attachments": [{
                "color": message.get_level_color(),
                "title": f"{message.get_level_emoji()} {message.title}",
                "text": message.body,
                "footer": f"Level: {message.level.name}",
                "ts": int(message.timestamp.timestamp()),
                "fields": [
                    {"title": key, "value": str(value), "short": True}
                    for key, value in message.metadata.items()
                ]
            }]
        }

        async with self._get_session().post(
            config.webhook_url,
            json=payload,
            timeout=aiohttp.ClientTimeout(total=10)
        ) as response:
            success = response.status == 200
            if not success:
                logger.error(f"Slack 전송 실패: {response.status}")
            return success

    async def _send_telegram(
        self,
        config: NotificationConfig,
        message: NotificationMessage
    ) -> bool:
        """Telegram 봇 전송"""
        if not aiohttp:
            logger.error("aiohttp 라이브러리가 설치되지 않았습니다")
            return False

        # 메시지 포맷팅 (HTML)
        text = f"<b>{message.get_level_emoji()} {message.title}</b>\n\n"
        text += f"{message.body}\n\n"

        if message.metadata:
            text += "<b>상세 정보:</b>\n"
            for key, value in message.metadata.items():
                text += f"• {key}: {value}\n"

        text += f"\n<i>{message.timestamp.strftime('%Y-%m-%d %H:%M:%S')}</i>"

        url = f"https://api.telegram.org/bot{config.api_token}/sendMessage"
        payload = {
            "chat_id": config.chat_id,
            "text": text,
            "parse_mode": "HTML"
        }

        async with self._get_session().post(
            url,
            json=payload,
            timeout=aiohttp.ClientTimeout(total=10)
        ) as response:
            success = response.status == 200
            if not success:
                error_text = await response.text()
                logger.error(f"Telegram 전송 실패: {response.status}, {error_text}")
            return success

    async def _send_email(
        self,
        config: NotificationConfig,
        message: NotificationMessage
    ) -> bool:
        """이메일 전송 (비동기)"""
        if not config.email_config:
            logger.error("Email 설정이 없습니다")
            return False

        email_cfg = config.email_config

        # HTML 이메일 생성
        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                .header {{ background-color: {message.get_level_color()}; color: white; padding: 20px; }}
                .body {{ padding: 20px; }}
                .metadata {{ background-color: #f5f5f5; padding: 15px; margin-top: 20px; }}
                .footer {{ color: #888; font-size: 12px; margin-top: 20px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h2>{message.get_level_emoji()} {message.title}</h2>
            </div>
            <div class="body">
                <p>{message.body.replace(chr(10), '<br>')}</p>
                {self._format_metadata_html(message.metadata)}
            </div>
            <div class="footer">
                <p>Level: {message.level.name} | Time: {message.timestamp.strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
        </body>
        </html>
        """

        # 이메일 메시지 생성
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"[{message.level.name}] {message.title}"
        msg['From'] = email_cfg.from_email
        msg['To'] = ', '.join(email_cfg.to_emails)

        # HTML 파트 추가
        html_part = MIMEText(html, 'html', 'utf-8')
        msg.attach(html_part)

        # 비동기 전송
        try:
            if aiosmtplib:
                # aiosmtplib 사용 (비동기)
                await aiosmtplib.send(
                    msg,
                    hostname=email_cfg.smtp_server,
                    port=email_cfg.smtp_port,
                    username=email_cfg.username,
                    password=email_cfg.password,
                    use_tls=email_cfg.use_tls,
                    timeout=10
                )
                return True
            else:
                # 동기 fallback (별도 스레드에서 실행)
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    None,
                    self._send_email_sync,
                    email_cfg,
                    msg
                )
                return True
        except Exception as e:
            logger.error(f"Email 전송 실패: {e}")
            return False

    def _send_email_sync(self, email_cfg: EmailConfig, msg: MIMEMultipart) -> None:
        """동기 이메일 전송 (fallback)"""
        with smtplib.SMTP(email_cfg.smtp_server, email_cfg.smtp_port, timeout=10) as server:
            if email_cfg.use_tls:
                server.starttls()
            server.login(email_cfg.username, email_cfg.password)
            server.send_message(msg)

    async def _send_discord(
        self,
        config: NotificationConfig,
        message: NotificationMessage
    ) -> bool:
        """Discord 웹훅 전송"""
        if not aiohttp:
            logger.error("aiohttp 라이브러리가 설치되지 않았습니다")
            return False

        # Discord Embed 형식
        embed = {
            "title": f"{message.get_level_emoji()} {message.title}",
            "description": message.body,
            "color": int(message.get_level_color().replace("#", ""), 16),
            "timestamp": message.timestamp.isoformat(),
            "footer": {
                "text": f"Level: {message.level.name}"
            },
            "fields": [
                {"name": key, "value": str(value), "inline": True}
                for key, value in message.metadata.items()
            ]
        }

        payload = {"embeds": [embed]}

        async with self._get_session().post(
            config.webhook_url,
            json=payload,
            timeout=aiohttp.ClientTimeout(total=10)
        ) as response:
            success = response.status == 204
            if not success:
                logger.error(f"Discord 전송 실패: {response.status}")
            return success

    async def _send_webhook(
        self,
        config: NotificationConfig,
        message: NotificationMessage
    ) -> bool:
        """일반 웹훅 전송 (JSON POST)"""
        if not aiohttp:
            logger.error("aiohttp 라이브러리가 설치되지 않았습니다")
            return False

        payload = {
            "title": message.title,
            "body": message.body,
            "level": message.level.name,
            "timestamp": message.timestamp.isoformat(),
            "metadata": message.metadata
        }

        async with self._get_session().post(
            config.webhook_url,
            json=payload,
            timeout=aiohttp.ClientTimeout(total=10)
        ) as response:
            success = 200 <= response.status < 300
            if not success:
                logger.error(f"Webhook 전송 실패: {response.status}")
            return success

    def _format_metadata_html(self, metadata: dict) -> str:
        """메타데이터를 HTML 테이블로 포맷팅"""
        if not metadata:
            return ""

        html = '<div class="metadata"><h3>상세 정보</h3><table style="width:100%">'
        for key, value in metadata.items():
            html += f"<tr><td><strong>{key}</strong></td><td>{value}</td></tr>"
        html += "</table></div>"
        return html

    def _get_session(self) -> aiohttp.ClientSession:
        """aiohttp 세션 반환 (재사용)"""
        if not aiohttp:
            raise RuntimeError("aiohttp 라이브러리가 필요합니다")

        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self) -> None:
        """리소스 정리"""
        if self._session and not self._session.closed:
            await self._session.close()

    async def __aenter__(self):
        """비동기 컨텍스트 매니저 진입"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """비동기 컨텍스트 매니저 종료"""
        await self.close()


# ==================== 헬퍼 함수 ====================

def format_pipeline_result(
    result: dict,
    success: bool = True,
    error: Optional[str] = None
) -> NotificationMessage:
    """
    파이프라인 실행 결과를 알림 메시지로 포맷팅

    Args:
        result: 파이프라인 결과 딕셔너리
        success: 성공 여부
        error: 에러 메시지 (실패 시)

    Returns:
        NotificationMessage
    """
    if success:
        title = "파이프라인 실행 완료"
        body = "전략 백테스트 파이프라인이 성공적으로 완료되었습니다."
        level = NotificationLevel.SUCCESS
        metadata = {
            "총 실행 시간": f"{result.get('duration', 'N/A')}초",
            "처리된 전략 수": result.get('total_strategies', 'N/A'),
            "성공한 전략": result.get('successful_strategies', 'N/A'),
        }
    else:
        title = "파이프라인 실행 실패"
        body = f"전략 백테스트 파이프라인 실행 중 오류가 발생했습니다.\n\n오류: {error}"
        level = NotificationLevel.ERROR
        metadata = {
            "실패 시각": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

    return NotificationMessage(
        title=title,
        body=body,
        level=level,
        metadata=metadata
    )


def format_backtest_summary(metrics_list: list[BacktestMetrics]) -> NotificationMessage:
    """
    백테스트 결과 요약을 알림 메시지로 포맷팅

    Args:
        metrics_list: 백테스트 메트릭 리스트

    Returns:
        NotificationMessage
    """
    if not metrics_list:
        return NotificationMessage(
            title="백테스트 결과 없음",
            body="처리된 백테스트 결과가 없습니다.",
            level=NotificationLevel.WARNING,
            metadata={}
        )

    # 평균 메트릭 계산
    avg_return = sum(m.total_return for m in metrics_list) / len(metrics_list)
    avg_sharpe = sum(m.sharpe_ratio for m in metrics_list) / len(metrics_list)
    avg_drawdown = sum(m.max_drawdown for m in metrics_list) / len(metrics_list)

    # 최고 성과 전략
    best_strategy = max(metrics_list, key=lambda m: m.total_return)

    body = f"""
백테스트 요약 ({len(metrics_list)}개 전략)

평균 수익률: {avg_return:.2f}%
평균 샤프 비율: {avg_sharpe:.2f}
평균 최대 낙폭: {avg_drawdown:.2f}%

최고 성과 전략:
- 이름: {best_strategy.strategy_name}
- 수익률: {best_strategy.total_return:.2f}%
- 샤프 비율: {best_strategy.sharpe_ratio:.2f}
    """.strip()

    # 레벨 결정
    if avg_return > 0 and avg_sharpe > 1.0:
        level = NotificationLevel.SUCCESS
    elif avg_return > 0:
        level = NotificationLevel.INFO
    else:
        level = NotificationLevel.WARNING

    metadata = {
        "전략 수": len(metrics_list),
        "평균 수익률": f"{avg_return:.2f}%",
        "최고 수익률": f"{best_strategy.total_return:.2f}%",
        "최고 전략": best_strategy.strategy_name,
    }

    return NotificationMessage(
        title="백테스트 결과 요약",
        body=body,
        level=level,
        metadata=metadata
    )


def format_error_alert(error: Exception, context: dict) -> NotificationMessage:
    """
    에러를 알림 메시지로 포맷팅

    Args:
        error: 발생한 예외
        context: 에러 컨텍스트 정보

    Returns:
        NotificationMessage
    """
    error_type = type(error).__name__
    error_msg = str(error)

    body = f"""
에러 타입: {error_type}
에러 메시지: {error_msg}

컨텍스트:
{chr(10).join(f'- {k}: {v}' for k, v in context.items())}
    """.strip()

    # 에러 심각도 판단
    critical_errors = ["SystemExit", "MemoryError", "KeyboardInterrupt"]
    if error_type in critical_errors:
        level = NotificationLevel.CRITICAL
    else:
        level = NotificationLevel.ERROR

    metadata = {
        "에러 타입": error_type,
        "발생 시각": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        **context
    }

    return NotificationMessage(
        title=f"시스템 에러 발생: {error_type}",
        body=body,
        level=level,
        metadata=metadata
    )


# ==================== 사용 예제 ====================

async def example_usage():
    """사용 예제"""
    # NotificationManager 생성
    manager = NotificationManager()

    # Slack 채널 추가
    slack_config = NotificationConfig(
        channel=NotificationChannel.SLACK,
        webhook_url="https://hooks.slack.com/services/YOUR/WEBHOOK/URL",
        min_level=NotificationLevel.INFO
    )
    manager.add_channel(slack_config)

    # Telegram 채널 추가
    telegram_config = NotificationConfig(
        channel=NotificationChannel.TELEGRAM,
        api_token="YOUR_BOT_TOKEN",
        chat_id="YOUR_CHAT_ID",
        min_level=NotificationLevel.WARNING
    )
    manager.add_channel(telegram_config)

    # 알림 전송
    message = NotificationMessage(
        title="테스트 알림",
        body="이것은 테스트 알림입니다.",
        level=NotificationLevel.INFO,
        metadata={"테스트": "성공"}
    )

    results = await manager.send(message)
    print(f"전송 결과: {results}")

    await manager.close()


if __name__ == "__main__":
    # 예제 실행
    asyncio.run(example_usage())
