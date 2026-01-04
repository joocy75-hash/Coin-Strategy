"""
Orchestrator Module

strategy-research-lab과 trading-agent-system을 통합하는
파이프라인 오케스트레이션 모듈

Components:
- Pipeline: 전체 워크플로우 자동화
- Scheduler: 정기적 파이프라인 실행
- Notification: 다채널 알림 시스템
"""

from .pipeline import (
    PipelineStage,
    PipelineConfig,
    PipelineResult,
    TradingPipeline,
    run_pipeline,
)

from .scheduler import (
    ScheduleType,
    ScheduleConfig,
    ScheduledTask,
    PipelineScheduler,
)

from .notification import (
    NotificationChannel,
    NotificationLevel,
    NotificationConfig,
    EmailConfig,
    NotificationMessage,
    NotificationManager,
    format_pipeline_result,
    format_backtest_summary,
    format_error_alert,
)

__all__ = [
    # Pipeline
    "PipelineStage",
    "PipelineConfig",
    "PipelineResult",
    "TradingPipeline",
    "run_pipeline",
    # Scheduler
    "ScheduleType",
    "ScheduleConfig",
    "ScheduledTask",
    "PipelineScheduler",
    # Notification
    "NotificationChannel",
    "NotificationLevel",
    "NotificationConfig",
    "EmailConfig",
    "NotificationMessage",
    "NotificationManager",
    "format_pipeline_result",
    "format_backtest_summary",
    "format_error_alert",
]
