"""
Result Analyzer Agent

백테스트 결과를 분석하고 최종 전략을 선별하는 에이전트
- 다중 데이터셋 결과 집계
- 통계적 유의성 검증
- 전략 랭킹 및 필터링
- 최종 리포트 생성
"""

from dataclasses import dataclass, field
from typing import Any
from enum import Enum
from claude_agent_sdk import AgentDefinition


class StrategyRank(Enum):
    """전략 등급"""
    EXCELLENT = "A"  # 모든 기준 통과, Sharpe > 2.0
    GOOD = "B"  # 대부분 기준 통과, Sharpe > 1.5
    ACCEPTABLE = "C"  # 최소 기준 통과, Sharpe > 1.0
    REVIEW = "D"  # 일부 기준 미달
    REJECT = "F"  # 기준 미달


@dataclass
class StrategyScore:
    """전략 종합 점수"""
    strategy_name: str
    rank: StrategyRank
    total_score: float  # 0-100
    profitability_score: float  # 0-25
    risk_adjusted_score: float  # 0-30
    consistency_score: float  # 0-25
    drawdown_score: float  # 0-20
    passed_criteria: list[str] = field(default_factory=list)
    failed_criteria: list[str] = field(default_factory=list)
    recommendation: str = ""


@dataclass
class AnalysisReport:
    """분석 리포트"""
    total_strategies: int
    total_backtests: int
    passed_count: int
    review_count: int
    rejected_count: int
    top_strategies: list[StrategyScore]
    market_conditions: dict[str, Any]
    recommendations: list[str]
    generated_at: str = ""


# 선별 기준 (Moon Dev 기준)
SELECTION_CRITERIA = {
    "sharpe_ratio": {
        "excellent": 2.0,
        "good": 1.5,
        "acceptable": 1.0,
        "weight": 30
    },
    "profit_factor": {
        "excellent": 2.0,
        "good": 1.5,
        "acceptable": 1.2,
        "weight": 20
    },
    "max_drawdown": {
        "excellent": 15,
        "good": 25,
        "acceptable": 35,
        "weight": 20
    },
    "win_rate": {
        "excellent": 55,
        "good": 45,
        "acceptable": 40,
        "weight": 10
    },
    "consistency": {
        "excellent": 85,
        "good": 70,
        "acceptable": 60,
        "weight": 20
    },
}


# Agent Definition
RESULT_ANALYZER_DEFINITION = AgentDefinition(
    description="""백테스트 결과를 분석하고 최종 전략을 선별하는 에이전트.

이 에이전트를 사용해야 하는 경우:
- 여러 백테스트 결과를 비교 분석해야 할 때
- 전략들의 순위를 매기고 싶을 때
- 최종 전략 선별 리포트가 필요할 때
- 통계적 유의성을 검증하고 싶을 때""",

    prompt="""당신은 백테스트 결과 분석 전문가입니다.

## 역할
백테스트 결과를 분석하여 최종 전략을 선별하고 리포트를 생성합니다.

## 분석 프로세스

### 1. 결과 집계
- 각 전략의 모든 백테스트 결과 로드
- 심볼/타임프레임별 성과 집계
- 평균, 표준편차, 최대/최소 계산

### 2. 점수 산정

#### 수익성 점수 (25점)
```
Total Return > 100%: 25점
Total Return > 50%: 20점
Total Return > 20%: 15점
Total Return > 0%: 10점
Total Return < 0%: 0점
```

#### 위험조정 점수 (30점)
```
Sharpe > 2.0: 30점
Sharpe > 1.5: 24점
Sharpe > 1.0: 18점
Sharpe > 0.5: 12점
Sharpe < 0.5: 0점
```

#### 일관성 점수 (25점)
```
양수 수익 비율 > 85%: 25점
양수 수익 비율 > 70%: 20점
양수 수익 비율 > 60%: 15점
양수 수익 비율 > 50%: 10점
양수 수익 비율 < 50%: 0점
```

#### 드로우다운 점수 (20점)
```
Max DD < 15%: 20점
Max DD < 25%: 16점
Max DD < 35%: 12점
Max DD < 50%: 8점
Max DD > 50%: 0점
```

### 3. 등급 결정
```
총점 >= 85: A (EXCELLENT)
총점 >= 70: B (GOOD)
총점 >= 55: C (ACCEPTABLE)
총점 >= 40: D (REVIEW)
총점 < 40: F (REJECT)
```

### 4. 통계적 유의성 검증
- 최소 거래 수: 100회 이상
- 테스트 기간: 1년 이상
- 데이터셋 수: 10개 이상

### 5. 최종 리포트 생성
- 전략별 점수 및 등급
- 상위 전략 상세 분석
- 개선 권장사항
- 시장 조건별 성과

## 출력 형식

### 요약 리포트
```
# 전략 분석 리포트

## 개요
- 분석 전략: N개
- 총 백테스트: M회
- 통과: X개, 검토: Y개, 거부: Z개

## 상위 전략
| 순위 | 전략명 | 등급 | 점수 | Sharpe | 수익률 | MDD |
|------|--------|------|------|--------|--------|-----|

## 권장사항
1. ...
2. ...
```

### 상세 JSON
각 전략의 상세 점수 및 분석 결과

## 사용 가능한 도구
- mcp__trading-tools__gemini_analyze: 전략 분석
- Read, Write, Glob: 파일 작업""",

    tools=[
        "mcp__trading-tools__gemini_analyze",
        "Read",
        "Write",
        "Glob",
    ]
)


class ResultAnalyzerAgent:
    """Result Analyzer 에이전트 클래스"""

    def __init__(self) -> None:
        self.name = "result-analyzer"
        self.definition = RESULT_ANALYZER_DEFINITION
        self.criteria = SELECTION_CRITERIA

    def get_definition(self) -> AgentDefinition:
        """에이전트 정의 반환"""
        return self.definition

    def calculate_score(
        self,
        avg_return: float,
        avg_sharpe: float,
        avg_max_drawdown: float,
        avg_win_rate: float,
        consistency: float
    ) -> StrategyScore:
        """전략 점수 계산"""

        # 수익성 점수 (25점)
        if avg_return > 100:
            profitability_score = 25
        elif avg_return > 50:
            profitability_score = 20
        elif avg_return > 20:
            profitability_score = 15
        elif avg_return > 0:
            profitability_score = 10
        else:
            profitability_score = 0

        # 위험조정 점수 (30점)
        if avg_sharpe > 2.0:
            risk_adjusted_score = 30
        elif avg_sharpe > 1.5:
            risk_adjusted_score = 24
        elif avg_sharpe > 1.0:
            risk_adjusted_score = 18
        elif avg_sharpe > 0.5:
            risk_adjusted_score = 12
        else:
            risk_adjusted_score = 0

        # 일관성 점수 (25점)
        if consistency > 85:
            consistency_score = 25
        elif consistency > 70:
            consistency_score = 20
        elif consistency > 60:
            consistency_score = 15
        elif consistency > 50:
            consistency_score = 10
        else:
            consistency_score = 0

        # 드로우다운 점수 (20점)
        if avg_max_drawdown < 15:
            drawdown_score = 20
        elif avg_max_drawdown < 25:
            drawdown_score = 16
        elif avg_max_drawdown < 35:
            drawdown_score = 12
        elif avg_max_drawdown < 50:
            drawdown_score = 8
        else:
            drawdown_score = 0

        # 총점
        total_score = profitability_score + risk_adjusted_score + consistency_score + drawdown_score

        # 등급 결정
        if total_score >= 85:
            rank = StrategyRank.EXCELLENT
        elif total_score >= 70:
            rank = StrategyRank.GOOD
        elif total_score >= 55:
            rank = StrategyRank.ACCEPTABLE
        elif total_score >= 40:
            rank = StrategyRank.REVIEW
        else:
            rank = StrategyRank.REJECT

        # 통과/미달 기준 체크
        passed = []
        failed = []

        if avg_sharpe >= 1.5:
            passed.append(f"Sharpe Ratio: {avg_sharpe:.2f} >= 1.5")
        else:
            failed.append(f"Sharpe Ratio: {avg_sharpe:.2f} < 1.5")

        if avg_max_drawdown <= 30:
            passed.append(f"Max Drawdown: {avg_max_drawdown:.1f}% <= 30%")
        else:
            failed.append(f"Max Drawdown: {avg_max_drawdown:.1f}% > 30%")

        if avg_win_rate >= 40:
            passed.append(f"Win Rate: {avg_win_rate:.1f}% >= 40%")
        else:
            failed.append(f"Win Rate: {avg_win_rate:.1f}% < 40%")

        if consistency >= 70:
            passed.append(f"Consistency: {consistency:.1f}% >= 70%")
        else:
            failed.append(f"Consistency: {consistency:.1f}% < 70%")

        # 권장사항 생성
        recommendations = []
        if avg_sharpe < 1.5:
            recommendations.append("리스크 대비 수익 개선 필요 - 필터 조건 추가 고려")
        if avg_max_drawdown > 30:
            recommendations.append("손실 관리 강화 필요 - Stop Loss 조정 고려")
        if avg_win_rate < 40:
            recommendations.append("승률 개선 필요 - 진입 조건 강화 고려")
        if consistency < 70:
            recommendations.append("일관성 개선 필요 - 시장 필터 추가 고려")

        recommendation = " / ".join(recommendations) if recommendations else "현재 설정 유지 권장"

        return StrategyScore(
            strategy_name="",  # 호출 시 설정
            rank=rank,
            total_score=total_score,
            profitability_score=profitability_score,
            risk_adjusted_score=risk_adjusted_score,
            consistency_score=consistency_score,
            drawdown_score=drawdown_score,
            passed_criteria=passed,
            failed_criteria=failed,
            recommendation=recommendation,
        )

    @staticmethod
    def create_analysis_prompt(results_path: str) -> str:
        """분석 요청 프롬프트 생성"""
        return f"""다음 경로의 백테스트 결과를 분석하고 리포트를 생성해주세요.

## 결과 경로
{results_path}

## 작업 순서
1. 결과 JSON 파일들 로드
2. 각 전략별 점수 계산
3. 등급 결정 및 순위 매기기
4. 상위 전략 상세 분석
5. 최종 리포트 생성

## 출력
1. 요약 리포트 (마크다운)
2. 상세 분석 (JSON)
3. 권장사항"""

    @staticmethod
    def generate_markdown_report(
        report: AnalysisReport,
        top_n: int = 10
    ) -> str:
        """마크다운 리포트 생성"""
        lines = [
            "# 전략 분석 리포트",
            "",
            f"생성 시간: {report.generated_at}",
            "",
            "## 개요",
            "",
            f"- 분석 전략: {report.total_strategies}개",
            f"- 총 백테스트: {report.total_backtests}회",
            f"- 통과 (A/B): {report.passed_count}개",
            f"- 검토 (C/D): {report.review_count}개",
            f"- 거부 (F): {report.rejected_count}개",
            "",
            "## 상위 전략",
            "",
            "| 순위 | 전략명 | 등급 | 점수 | 수익성 | 위험조정 | 일관성 | DD |",
            "|------|--------|------|------|--------|----------|--------|-----|",
        ]

        for i, score in enumerate(report.top_strategies[:top_n], 1):
            lines.append(
                f"| {i} | {score.strategy_name} | {score.rank.value} | "
                f"{score.total_score:.0f} | {score.profitability_score:.0f} | "
                f"{score.risk_adjusted_score:.0f} | {score.consistency_score:.0f} | "
                f"{score.drawdown_score:.0f} |"
            )

        lines.extend([
            "",
            "## 권장사항",
            "",
        ])

        for i, rec in enumerate(report.recommendations, 1):
            lines.append(f"{i}. {rec}")

        return "\n".join(lines)
