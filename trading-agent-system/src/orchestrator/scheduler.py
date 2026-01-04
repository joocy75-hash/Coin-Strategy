"""
Pipeline Scheduler

파이프라인을 정기적으로 실행하는 스케줄러 시스템
- Cron 표현식 지원
- 비동기 스케줄링
- 작업 상태 관리
- 실패 시 재시도
"""

import asyncio
import json
import logging
import uuid
from dataclasses import dataclass, asdict, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Optional, Callable, Any
from zoneinfo import ZoneInfo

from croniter import croniter


# 로깅 설정
logger = logging.getLogger(__name__)


class ScheduleType(Enum):
    """스케줄 타입"""
    ONCE = "once"           # 1회 실행
    HOURLY = "hourly"       # 매시간
    DAILY = "daily"         # 매일
    WEEKLY = "weekly"       # 매주
    CRON = "cron"          # Cron 표현식


@dataclass
class ScheduleConfig:
    """스케줄 설정"""
    schedule_type: ScheduleType
    cron_expression: Optional[str] = None  # CRON 타입일 때 사용
    timezone: str = "Asia/Seoul"
    enabled: bool = True
    max_retries: int = 3                   # 최대 재시도 횟수
    retry_delay: int = 60                  # 재시도 대기 시간(초)

    def __post_init__(self):
        """검증"""
        if self.schedule_type == ScheduleType.CRON and not self.cron_expression:
            raise ValueError("CRON 타입은 cron_expression이 필요합니다")

        if self.cron_expression:
            # Cron 표현식 유효성 검증
            try:
                croniter(self.cron_expression)
            except Exception as e:
                raise ValueError(f"잘못된 cron 표현식: {e}")


@dataclass
class PipelineConfig:
    """파이프라인 설정 (예시)"""
    name: str
    description: str = ""
    parameters: dict[str, Any] = field(default_factory=dict)


@dataclass
class PipelineResult:
    """파이프라인 실행 결과"""
    task_id: str
    success: bool
    start_time: datetime
    end_time: datetime
    duration_seconds: float
    error_message: Optional[str] = None
    result_data: Optional[dict[str, Any]] = None


@dataclass
class ScheduledTask:
    """스케줄된 작업"""
    task_id: str
    name: str
    pipeline_config: PipelineConfig
    schedule_config: ScheduleConfig
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    run_count: int = 0
    failure_count: int = 0
    last_error: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        """딕셔너리로 변환 (JSON 직렬화용)"""
        data = asdict(self)
        # Enum을 문자열로 변환
        data["schedule_config"]["schedule_type"] = self.schedule_config.schedule_type.value
        # datetime을 문자열로 변환
        if self.last_run:
            data["last_run"] = self.last_run.isoformat()
        if self.next_run:
            data["next_run"] = self.next_run.isoformat()
        data["created_at"] = self.created_at.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "ScheduledTask":
        """딕셔너리에서 생성"""
        # ScheduleType 변환
        schedule_data = data["schedule_config"]
        schedule_data["schedule_type"] = ScheduleType(schedule_data["schedule_type"])

        # PipelineConfig 변환
        pipeline_config = PipelineConfig(**data["pipeline_config"])
        schedule_config = ScheduleConfig(**schedule_data)

        # datetime 변환
        if data.get("last_run"):
            data["last_run"] = datetime.fromisoformat(data["last_run"])
        if data.get("next_run"):
            data["next_run"] = datetime.fromisoformat(data["next_run"])
        data["created_at"] = datetime.fromisoformat(data["created_at"])

        return cls(
            task_id=data["task_id"],
            name=data["name"],
            pipeline_config=pipeline_config,
            schedule_config=schedule_config,
            last_run=data.get("last_run"),
            next_run=data.get("next_run"),
            run_count=data["run_count"],
            failure_count=data.get("failure_count", 0),
            last_error=data.get("last_error"),
            created_at=data["created_at"],
        )


class PipelineScheduler:
    """파이프라인 스케줄러"""

    def __init__(
        self,
        state_file: str = "scheduler_state.json",
        max_concurrent_tasks: int = 3,
        check_interval: int = 10,  # 스케줄 체크 간격(초)
    ):
        """
        Args:
            state_file: 작업 상태 저장 파일
            max_concurrent_tasks: 최대 동시 실행 작업 수
            check_interval: 스케줄 체크 간격(초)
        """
        self.state_file = Path(state_file)
        self.max_concurrent_tasks = max_concurrent_tasks
        self.check_interval = check_interval

        self.tasks: dict[str, ScheduledTask] = {}
        self.running = False
        self._scheduler_task: Optional[asyncio.Task] = None
        self._running_tasks: set[asyncio.Task] = set()

        # 이벤트 콜백
        self.on_task_start: Optional[Callable[[ScheduledTask], None]] = None
        self.on_task_complete: Optional[Callable[[ScheduledTask, PipelineResult], None]] = None
        self.on_task_error: Optional[Callable[[ScheduledTask, Exception], None]] = None

        # 상태 파일에서 작업 로드
        self._load_state()

    def add_task(self, task: ScheduledTask) -> str:
        """
        작업 추가

        Args:
            task: 스케줄된 작업

        Returns:
            task_id
        """
        if not task.task_id:
            task.task_id = str(uuid.uuid4())

        # 다음 실행 시간 계산
        if task.next_run is None:
            task.next_run = self._calculate_next_run(task.schedule_config)

        self.tasks[task.task_id] = task
        self._save_state()

        logger.info(f"작업 추가됨: {task.name} (ID: {task.task_id})")
        logger.info(f"  다음 실행: {task.next_run}")

        return task.task_id

    def remove_task(self, task_id: str) -> bool:
        """
        작업 제거

        Args:
            task_id: 작업 ID

        Returns:
            성공 여부
        """
        if task_id in self.tasks:
            task = self.tasks.pop(task_id)
            self._save_state()
            logger.info(f"작업 제거됨: {task.name} (ID: {task_id})")
            return True
        return False

    def update_task(self, task_id: str, config: ScheduleConfig) -> bool:
        """
        작업 스케줄 업데이트

        Args:
            task_id: 작업 ID
            config: 새로운 스케줄 설정

        Returns:
            성공 여부
        """
        if task_id not in self.tasks:
            return False

        task = self.tasks[task_id]
        task.schedule_config = config
        task.next_run = self._calculate_next_run(config)
        self._save_state()

        logger.info(f"작업 스케줄 업데이트됨: {task.name}")
        logger.info(f"  다음 실행: {task.next_run}")

        return True

    def get_task(self, task_id: str) -> Optional[ScheduledTask]:
        """작업 조회"""
        return self.tasks.get(task_id)

    def list_tasks(self) -> list[ScheduledTask]:
        """모든 작업 목록"""
        return list(self.tasks.values())

    async def start(self) -> None:
        """스케줄러 시작"""
        if self.running:
            logger.warning("스케줄러가 이미 실행 중입니다")
            return

        self.running = True
        logger.info("스케줄러 시작됨")
        logger.info(f"  등록된 작업: {len(self.tasks)}개")
        logger.info(f"  체크 간격: {self.check_interval}초")
        logger.info(f"  최대 동시 실행: {self.max_concurrent_tasks}개")

        # 스케줄러 루프 시작
        self._scheduler_task = asyncio.create_task(self._scheduler_loop())

    async def stop(self) -> None:
        """스케줄러 중지"""
        if not self.running:
            return

        logger.info("스케줄러 중지 중...")
        self.running = False

        # 스케줄러 태스크 취소
        if self._scheduler_task:
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass

        # 실행 중인 작업들이 완료될 때까지 대기
        if self._running_tasks:
            logger.info(f"실행 중인 작업 {len(self._running_tasks)}개 완료 대기 중...")
            await asyncio.gather(*self._running_tasks, return_exceptions=True)

        logger.info("스케줄러 중지됨")

    async def run_task_now(self, task_id: str) -> PipelineResult:
        """
        작업을 즉시 실행 (스케줄 무시)

        Args:
            task_id: 작업 ID

        Returns:
            PipelineResult
        """
        task = self.tasks.get(task_id)
        if not task:
            raise ValueError(f"작업을 찾을 수 없습니다: {task_id}")

        logger.info(f"작업 수동 실행: {task.name}")
        return await self._execute_task(task)

    async def _scheduler_loop(self) -> None:
        """스케줄러 메인 루프"""
        while self.running:
            try:
                # 실행할 작업 확인
                tasks_to_run = [
                    task for task in self.tasks.values()
                    if self._should_run(task)
                ]

                # 동시 실행 제한 확인
                available_slots = self.max_concurrent_tasks - len(self._running_tasks)
                tasks_to_run = tasks_to_run[:available_slots]

                # 작업 실행
                for task in tasks_to_run:
                    asyncio_task = asyncio.create_task(self._execute_task(task))
                    self._running_tasks.add(asyncio_task)
                    asyncio_task.add_done_callback(self._running_tasks.discard)

                # 완료된 작업 정리
                self._running_tasks = {t for t in self._running_tasks if not t.done()}

                # 대기
                await asyncio.sleep(self.check_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"스케줄러 루프 오류: {e}")
                await asyncio.sleep(self.check_interval)

    def _should_run(self, task: ScheduledTask) -> bool:
        """
        작업 실행 여부 판단

        Args:
            task: 작업

        Returns:
            실행 여부
        """
        if not task.schedule_config.enabled:
            return False

        if task.next_run is None:
            return False

        now = datetime.now(ZoneInfo(task.schedule_config.timezone))
        return task.next_run <= now

    async def _execute_task(self, task: ScheduledTask) -> PipelineResult:
        """
        작업 실행 (재시도 로직 포함)

        Args:
            task: 작업

        Returns:
            PipelineResult
        """
        start_time = datetime.now()
        retry_count = 0
        last_error = None

        # 콜백: 작업 시작
        if self.on_task_start:
            try:
                self.on_task_start(task)
            except Exception as e:
                logger.error(f"on_task_start 콜백 오류: {e}")

        logger.info(f"작업 실행 시작: {task.name} (ID: {task.task_id})")

        while retry_count <= task.schedule_config.max_retries:
            try:
                # 실제 파이프라인 실행 (여기서는 예시)
                result_data = await self._run_pipeline(task)

                end_time = datetime.now()
                duration = (end_time - start_time).total_seconds()

                # 성공
                result = PipelineResult(
                    task_id=task.task_id,
                    success=True,
                    start_time=start_time,
                    end_time=end_time,
                    duration_seconds=duration,
                    result_data=result_data,
                )

                # 작업 상태 업데이트
                task.last_run = start_time
                task.run_count += 1
                task.failure_count = 0
                task.last_error = None

                # ONCE 타입이 아니면 다음 실행 시간 계산
                if task.schedule_config.schedule_type != ScheduleType.ONCE:
                    task.next_run = self._calculate_next_run(task.schedule_config)
                else:
                    task.schedule_config.enabled = False

                self._save_state()

                logger.info(f"작업 완료: {task.name} (소요 시간: {duration:.2f}초)")
                if task.next_run:
                    logger.info(f"  다음 실행: {task.next_run}")

                # 콜백: 작업 완료
                if self.on_task_complete:
                    try:
                        self.on_task_complete(task, result)
                    except Exception as e:
                        logger.error(f"on_task_complete 콜백 오류: {e}")

                return result

            except Exception as e:
                last_error = str(e)
                retry_count += 1

                logger.error(f"작업 실패 (시도 {retry_count}/{task.schedule_config.max_retries + 1}): {e}")

                if retry_count <= task.schedule_config.max_retries:
                    logger.info(f"{task.schedule_config.retry_delay}초 후 재시도...")
                    await asyncio.sleep(task.schedule_config.retry_delay)
                else:
                    # 모든 재시도 실패
                    end_time = datetime.now()
                    duration = (end_time - start_time).total_seconds()

                    result = PipelineResult(
                        task_id=task.task_id,
                        success=False,
                        start_time=start_time,
                        end_time=end_time,
                        duration_seconds=duration,
                        error_message=last_error,
                    )

                    # 작업 상태 업데이트
                    task.last_run = start_time
                    task.run_count += 1
                    task.failure_count += 1
                    task.last_error = last_error

                    # 실패해도 다음 실행은 스케줄대로
                    if task.schedule_config.schedule_type != ScheduleType.ONCE:
                        task.next_run = self._calculate_next_run(task.schedule_config)

                    self._save_state()

                    logger.error(f"작업 실패 (최종): {task.name}")

                    # 콜백: 작업 오류
                    if self.on_task_error:
                        try:
                            self.on_task_error(task, Exception(last_error))
                        except Exception as callback_error:
                            logger.error(f"on_task_error 콜백 오류: {callback_error}")

                    return result

    async def _run_pipeline(self, task: ScheduledTask) -> dict[str, Any]:
        """
        실제 파이프라인 실행 로직

        이 메서드는 실제 프로젝트에서 TradingPipeline과 연동되어야 합니다.
        현재는 예시 구현입니다.

        Args:
            task: 작업

        Returns:
            실행 결과 데이터
        """
        # TODO: 실제 파이프라인 통합
        # from .pipeline import TradingPipeline
        # pipeline = TradingPipeline(task.pipeline_config)
        # result = await pipeline.run()
        # return result

        # 예시 구현
        logger.info(f"  파이프라인 실행: {task.pipeline_config.name}")
        await asyncio.sleep(2)  # 실행 시뮬레이션

        return {
            "pipeline": task.pipeline_config.name,
            "parameters": task.pipeline_config.parameters,
            "status": "completed",
        }

    def _calculate_next_run(self, schedule: ScheduleConfig) -> datetime:
        """
        다음 실행 시간 계산

        Args:
            schedule: 스케줄 설정

        Returns:
            다음 실행 시간
        """
        tz = ZoneInfo(schedule.timezone)
        now = datetime.now(tz)

        if schedule.schedule_type == ScheduleType.ONCE:
            # 1회 실행: 즉시
            return now

        elif schedule.schedule_type == ScheduleType.HOURLY:
            # 매시간: 다음 정각
            next_run = now.replace(minute=0, second=0, microsecond=0)
            if next_run <= now:
                next_run += timedelta(hours=1)
            return next_run

        elif schedule.schedule_type == ScheduleType.DAILY:
            # 매일: 다음 날 00:00
            next_run = now.replace(hour=0, minute=0, second=0, microsecond=0)
            if next_run <= now:
                next_run += timedelta(days=1)
            return next_run

        elif schedule.schedule_type == ScheduleType.WEEKLY:
            # 매주: 다음 월요일 00:00
            next_run = now.replace(hour=0, minute=0, second=0, microsecond=0)
            days_ahead = 7 - now.weekday()  # 월요일까지 남은 일수
            if days_ahead <= 0:
                days_ahead += 7
            next_run += timedelta(days=days_ahead)
            return next_run

        elif schedule.schedule_type == ScheduleType.CRON:
            # Cron 표현식
            if not schedule.cron_expression:
                raise ValueError("CRON 타입은 cron_expression이 필요합니다")

            cron = croniter(schedule.cron_expression, now)
            return cron.get_next(datetime)

        else:
            raise ValueError(f"알 수 없는 스케줄 타입: {schedule.schedule_type}")

    def _save_state(self) -> None:
        """작업 상태를 파일로 저장"""
        try:
            state = {
                "tasks": [task.to_dict() for task in self.tasks.values()],
                "saved_at": datetime.now().isoformat(),
            }

            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2, ensure_ascii=False)

            logger.debug(f"상태 저장됨: {self.state_file}")

        except Exception as e:
            logger.error(f"상태 저장 실패: {e}")

    def _load_state(self) -> None:
        """파일에서 작업 상태 로드"""
        if not self.state_file.exists():
            logger.info("상태 파일이 없습니다. 새로운 스케줄러 시작.")
            return

        try:
            with open(self.state_file, "r", encoding="utf-8") as f:
                state = json.load(f)

            for task_data in state.get("tasks", []):
                task = ScheduledTask.from_dict(task_data)
                self.tasks[task.task_id] = task

            logger.info(f"상태 로드됨: {len(self.tasks)}개 작업")

        except Exception as e:
            logger.error(f"상태 로드 실패: {e}")
            logger.warning("새로운 스케줄러로 시작합니다.")


# 사용 예시
async def example_usage():
    """사용 예시"""
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s"
    )

    # 스케줄러 생성
    scheduler = PipelineScheduler(
        state_file="data/scheduler_state.json",
        max_concurrent_tasks=2,
        check_interval=5,
    )

    # 콜백 등록
    def on_start(task: ScheduledTask):
        print(f"\n>>> 작업 시작: {task.name}")

    def on_complete(task: ScheduledTask, result: PipelineResult):
        print(f">>> 작업 완료: {task.name} (성공: {result.success})")

    def on_error(task: ScheduledTask, error: Exception):
        print(f">>> 작업 오류: {task.name} - {error}")

    scheduler.on_task_start = on_start
    scheduler.on_task_complete = on_complete
    scheduler.on_task_error = on_error

    # 작업 추가
    # 1. 매시간 실행
    hourly_task = ScheduledTask(
        task_id="",
        name="시간별 데이터 수집",
        pipeline_config=PipelineConfig(
            name="hourly_collection",
            description="매시간 데이터 수집",
            parameters={"symbols": ["BTCUSDT", "ETHUSDT"]},
        ),
        schedule_config=ScheduleConfig(
            schedule_type=ScheduleType.HOURLY,
            timezone="Asia/Seoul",
        ),
    )
    scheduler.add_task(hourly_task)

    # 2. 매일 실행 (Cron 표현식)
    daily_task = ScheduledTask(
        task_id="",
        name="일일 전략 백테스트",
        pipeline_config=PipelineConfig(
            name="daily_backtest",
            description="매일 오전 9시 백테스트",
            parameters={"strategy": "momentum"},
        ),
        schedule_config=ScheduleConfig(
            schedule_type=ScheduleType.CRON,
            cron_expression="0 9 * * *",  # 매일 오전 9시
            timezone="Asia/Seoul",
        ),
    )
    scheduler.add_task(daily_task)

    # 3. 1회 실행 (테스트)
    once_task = ScheduledTask(
        task_id="",
        name="즉시 실행 테스트",
        pipeline_config=PipelineConfig(
            name="test_pipeline",
            description="테스트용 파이프라인",
        ),
        schedule_config=ScheduleConfig(
            schedule_type=ScheduleType.ONCE,
        ),
    )
    task_id = scheduler.add_task(once_task)

    # 스케줄러 시작
    await scheduler.start()

    # 작업 목록 출력
    print("\n=== 등록된 작업 ===")
    for task in scheduler.list_tasks():
        print(f"- {task.name}")
        print(f"  타입: {task.schedule_config.schedule_type.value}")
        print(f"  다음 실행: {task.next_run}")
        print(f"  실행 횟수: {task.run_count}")

    # 수동 실행 테스트
    print("\n=== 수동 실행 테스트 ===")
    result = await scheduler.run_task_now(task_id)
    print(f"결과: 성공={result.success}, 소요시간={result.duration_seconds:.2f}초")

    # 일정 시간 동안 실행
    print("\n=== 스케줄러 실행 중 (30초) ===")
    await asyncio.sleep(30)

    # 종료
    await scheduler.stop()

    print("\n=== 최종 작업 상태 ===")
    for task in scheduler.list_tasks():
        print(f"- {task.name}: {task.run_count}회 실행")
        if task.last_error:
            print(f"  마지막 오류: {task.last_error}")


if __name__ == "__main__":
    asyncio.run(example_usage())
