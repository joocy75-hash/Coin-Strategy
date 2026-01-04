"""
Backtest Runner Agent

생성된 전략을 다중 데이터셋에서 자동 백테스트하는 에이전트
- 25개 이상 데이터셋 병렬 실행
- 다양한 타임프레임 테스트 (1m, 5m, 15m, 1h, 4h, 1d)
- 다양한 심볼 테스트 (BTC, ETH, SOL 등)
- 고급 성과 지표 계산
"""

from dataclasses import dataclass, field
from typing import Any
from claude_agent_sdk import AgentDefinition


@dataclass
class BacktestConfig:
    """백테스트 설정"""
    strategy_code: str
    strategy_name: str
    initial_cash: float = 10000.0
    commission: float = 0.001
    symbols: list[str] = field(default_factory=lambda: ["BTCUSDT", "ETHUSDT", "SOLUSDT"])
    timeframes: list[str] = field(default_factory=lambda: ["1h", "4h", "1d"])
    start_date: str = "2023-01-01"
    end_date: str = "2024-12-01"
    optimize: bool = False


@dataclass
class BacktestResult:
    """백테스트 결과"""
    strategy_name: str
    symbol: str
    timeframe: str
    total_return_pct: float
    sharpe_ratio: float
    max_drawdown_pct: float
    win_rate_pct: float
    profit_factor: float
    total_trades: int
    avg_trade_pct: float
    final_equity: float
    data_path: str


@dataclass
class AggregatedResults:
    """집계된 백테스트 결과"""
    strategy_name: str
    total_tests: int
    avg_return: float
    avg_sharpe: float
    avg_max_drawdown: float
    avg_win_rate: float
    avg_profit_factor: float
    best_result: BacktestResult | None
    worst_result: BacktestResult | None
    consistency_score: float  # 양수 수익 비율
    results: list[BacktestResult] = field(default_factory=list)


# 필수 성과 지표 정의
REQUIRED_METRICS = {
    "profitability": ["total_return_pct", "profit_factor", "avg_trade_pct"],
    "risk_adjusted": ["sharpe_ratio", "sortino_ratio", "calmar_ratio"],
    "drawdown": ["max_drawdown_pct", "avg_drawdown", "recovery_time"],
    "trade_quality": ["win_rate_pct", "avg_win_loss_ratio", "expectancy"],
    "consistency": ["monthly_returns_std", "consecutive_losses"],
}


# Agent Definition
BACKTEST_RUNNER_DEFINITION = AgentDefinition(
    description="""전략을 다중 데이터셋에서 자동 백테스트하는 에이전트.

이 에이전트를 사용해야 하는 경우:
- 전략을 여러 심볼에서 테스트하고 싶을 때
- 전략을 여러 타임프레임에서 테스트하고 싶을 때
- 통계적으로 유의미한 백테스트 결과가 필요할 때
- 전략의 일관성을 검증하고 싶을 때""",

    prompt="""당신은 다중 백테스트 실행 전문가입니다.

## 역할
전략을 여러 데이터셋에서 백테스트하고 결과를 집계합니다.
Moon Dev 기준: 25개 이상 데이터셋으로 통계적 유의성 확보.

## 백테스트 프로세스

### 1. 데이터 준비
- fetch_binance_data 도구로 필요한 데이터 수집
- 심볼: BTCUSDT, ETHUSDT, SOLUSDT, BNBUSDT 등
- 타임프레임: 1h, 4h, 1d
- 기간: 최소 1년 이상

### 2. 백테스트 실행
- run_backtest 도구로 각 데이터셋에서 실행
- 초기 자본: $10,000
- 수수료: 0.1%
- 병렬 실행으로 효율성 극대화

### 3. 결과 집계
- 전체 평균 수익률
- 전체 평균 Sharpe Ratio
- 전체 평균 Max Drawdown
- 일관성 점수 (양수 수익 비율)

### 4. 성과 지표 계산

#### 수익성 지표
- Total Return [%]: 전체 수익률
- Profit Factor: 총 이익 / 총 손실
- Avg Trade [%]: 평균 거래 수익

#### 위험조정 지표
- Sharpe Ratio: 초과수익 / 표준편차
- Sortino Ratio: 초과수익 / 하방 표준편차
- Calmar Ratio: 연간 수익 / Max Drawdown

#### 드로우다운 지표
- Max Drawdown [%]: 최대 낙폭
- Avg Drawdown [%]: 평균 낙폭
- Recovery Time: 회복 기간

#### 거래 품질 지표
- Win Rate [%]: 승률
- Avg Win/Loss: 평균 이익/손실 비율
- Expectancy: 기대값

## 선별 기준 (Moon Dev 기준)
```python
PASS_CRITERIA = {
    "sharpe_ratio": ">= 1.5",      # 이상적: 2.0+
    "profit_factor": ">= 1.5",     # 이상적: 2.0+
    "max_drawdown": "<= 30%",
    "win_rate": ">= 40%",
    "total_trades": ">= 100",      # 통계적 유의성
    "consistency": "positive in 70%+ of tests"
}
```

## 출력 형식
각 백테스트 결과와 집계 결과를 JSON으로 저장:
- data/results/{strategy_name}_results.json
- 개별 결과 + 집계 통계 포함

## 사용 가능한 도구
- mcp__trading-tools__fetch_binance_data: 데이터 수집
- mcp__trading-tools__run_backtest: 백테스트 실행
- Read, Write, Glob: 파일 작업""",

    tools=[
        "mcp__trading-tools__fetch_binance_data",
        "mcp__trading-tools__run_backtest",
        "Read",
        "Write",
        "Glob",
    ]
)


class BacktestRunnerAgent:
    """Backtest Runner 에이전트 클래스"""

    def __init__(self) -> None:
        self.name = "backtest-runner"
        self.definition = BACKTEST_RUNNER_DEFINITION
        self.required_metrics = REQUIRED_METRICS

    def get_definition(self) -> AgentDefinition:
        """에이전트 정의 반환"""
        return self.definition

    @staticmethod
    def create_backtest_prompt(config: BacktestConfig) -> str:
        """백테스트 요청 프롬프트 생성"""
        symbols_str = ", ".join(config.symbols)
        timeframes_str = ", ".join(config.timeframes)

        return f"""다음 전략을 다중 데이터셋에서 백테스트해주세요.

## 전략 코드
```python
{config.strategy_code}
```

## 전략 이름
{config.strategy_name}

## 백테스트 설정
- 초기 자본: ${config.initial_cash:,.0f}
- 수수료: {config.commission * 100:.2f}%
- 심볼: {symbols_str}
- 타임프레임: {timeframes_str}
- 기간: {config.start_date} ~ {config.end_date}
- 최적화: {config.optimize}

## 작업 순서
1. 각 심볼/타임프레임 조합에 대해 데이터 수집 (fetch_binance_data)
2. 각 데이터셋에서 백테스트 실행 (run_backtest)
3. 결과 집계 및 통계 계산
4. 결과를 JSON 파일로 저장

총 {len(config.symbols) * len(config.timeframes)}개의 백테스트를 실행합니다."""

    @staticmethod
    def aggregate_results(results: list[BacktestResult]) -> AggregatedResults:
        """백테스트 결과 집계"""
        if not results:
            return AggregatedResults(
                strategy_name="Unknown",
                total_tests=0,
                avg_return=0,
                avg_sharpe=0,
                avg_max_drawdown=0,
                avg_win_rate=0,
                avg_profit_factor=0,
                best_result=None,
                worst_result=None,
                consistency_score=0,
            )

        strategy_name = results[0].strategy_name
        total_tests = len(results)

        # 평균 계산
        avg_return = sum(r.total_return_pct for r in results) / total_tests
        avg_sharpe = sum(r.sharpe_ratio for r in results) / total_tests
        avg_max_drawdown = sum(r.max_drawdown_pct for r in results) / total_tests
        avg_win_rate = sum(r.win_rate_pct for r in results) / total_tests
        avg_profit_factor = sum(r.profit_factor for r in results) / total_tests

        # 최고/최저 결과
        best_result = max(results, key=lambda r: r.total_return_pct)
        worst_result = min(results, key=lambda r: r.total_return_pct)

        # 일관성 점수 (양수 수익 비율)
        positive_count = sum(1 for r in results if r.total_return_pct > 0)
        consistency_score = positive_count / total_tests * 100

        return AggregatedResults(
            strategy_name=strategy_name,
            total_tests=total_tests,
            avg_return=avg_return,
            avg_sharpe=avg_sharpe,
            avg_max_drawdown=avg_max_drawdown,
            avg_win_rate=avg_win_rate,
            avg_profit_factor=avg_profit_factor,
            best_result=best_result,
            worst_result=worst_result,
            consistency_score=consistency_score,
            results=results,
        )

    @staticmethod
    def check_pass_criteria(aggregated: AggregatedResults) -> tuple[bool, list[str]]:
        """Moon Dev 기준 통과 여부 확인"""
        issues = []

        if aggregated.avg_sharpe < 1.5:
            issues.append(f"Sharpe Ratio {aggregated.avg_sharpe:.2f} < 1.5")

        if aggregated.avg_profit_factor < 1.5:
            issues.append(f"Profit Factor {aggregated.avg_profit_factor:.2f} < 1.5")

        if aggregated.avg_max_drawdown > 30:
            issues.append(f"Max Drawdown {aggregated.avg_max_drawdown:.1f}% > 30%")

        if aggregated.avg_win_rate < 40:
            issues.append(f"Win Rate {aggregated.avg_win_rate:.1f}% < 40%")

        if aggregated.consistency_score < 70:
            issues.append(f"Consistency {aggregated.consistency_score:.1f}% < 70%")

        return len(issues) == 0, issues

    def get_default_test_matrix(self) -> list[tuple[str, str]]:
        """기본 테스트 매트릭스 반환 (심볼, 타임프레임)"""
        symbols = [
            "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
            "ADAUSDT", "DOGEUSDT", "DOTUSDT", "MATICUSDT", "AVAXUSDT"
        ]
        timeframes = ["1h", "4h", "1d"]

        matrix = []
        for symbol in symbols:
            for tf in timeframes:
                matrix.append((symbol, tf))

        return matrix  # 30개 조합
