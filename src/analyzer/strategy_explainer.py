# src/analyzer/strategy_explainer.py
"""
초보자를 위한 LLM 기반 전략 설명 생성기

Claude API를 활용하여 Pine Script 전략을 쉬운 한국어로 설명
- 전략 유형 분류 (추세추종, 평균회귀, 돌파, 스캘핑 등)
- 사용 지표 상세 설명 (초보자 눈높이)
- 작동 원리 설명
- 장단점 분석
- 사용 권장 여부 결정
"""

import json
import logging
import os
from typing import Dict, Optional, List
from dataclasses import dataclass, field, asdict
from enum import Enum

try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False

logger = logging.getLogger(__name__)


class RecommendationLevel(Enum):
    """사용 권장 수준"""
    RECOMMENDED = "recommended"      # 사용 권장
    REVIEW_NEEDED = "review_needed"  # 검토 필요
    NOT_RECOMMENDED = "not_recommended"  # 사용 비권장


class StrategyType(Enum):
    """전략 유형"""
    TREND_FOLLOWING = "추세추종"
    MEAN_REVERSION = "평균회귀"
    BREAKOUT = "돌파"
    SCALPING = "스캘핑"
    SWING = "스윙"
    MOMENTUM = "모멘텀"
    VOLATILITY = "변동성"
    GRID = "그리드"
    UNKNOWN = "기타"


@dataclass
class IndicatorExplanation:
    """지표 설명"""
    name: str                    # 지표 이름 (예: RSI)
    korean_name: str             # 한국어 이름 (예: 상대강도지수)
    simple_explanation: str      # 초보자용 설명
    how_used: str               # 이 전략에서 어떻게 사용되는지


@dataclass
class StrategyExplanation:
    """초보자용 전략 설명 (확장 버전)"""

    # === 핵심 요약 ===
    one_line_summary: str = ""       # "이동평균선을 이용한 추세추종 전략"
    strategy_type: str = ""          # StrategyType 값
    strategy_type_explanation: str = ""  # 전략 유형이 무엇인지 설명
    difficulty_level: str = ""       # "초급", "중급", "고급"

    # === 전략 설명 ===
    how_it_works: str = ""           # 전략 작동 방식 (2-3문장)
    entry_condition: str = ""        # 진입 조건 설명
    exit_condition: str = ""         # 청산 조건 설명

    # === 사용 지표 상세 설명 ===
    indicators_used: List[Dict] = field(default_factory=list)
    # 각 지표: {"name": "RSI", "korean_name": "상대강도지수",
    #          "explanation": "...", "usage_in_strategy": "..."}

    # === 장단점 분석 ===
    strengths: List[str] = field(default_factory=list)   # 장점
    weaknesses: List[str] = field(default_factory=list)  # 단점

    # === 적합한 시장 상황 ===
    suitable_markets: List[str] = field(default_factory=list)  # ["상승 추세", "변동성 큰 시장"]
    unsuitable_markets: List[str] = field(default_factory=list)  # ["횡보장", "급락장"]
    recommended_timeframe: str = ""  # 권장 타임프레임

    # === 위험 경고 ===
    risk_warning: str = ""           # 주요 위험 요소
    beginner_advice: str = ""        # 초보자를 위한 조언

    # === 사용 권장 여부 (핵심) ===
    recommendation_level: str = ""   # "recommended", "review_needed", "not_recommended"
    recommendation_icon: str = ""    # "✅", "⚠️", "❌"
    recommendation_title: str = ""   # "사용 권장", "검토 필요", "사용 비권장"
    recommendation_reason: str = ""  # 추천/비추천 상세 이유
    recommendation_details: List[str] = field(default_factory=list)  # 세부 판단 근거

    # === 백테스트 해석 ===
    backtest_interpretation: str = ""  # 백테스트 결과가 의미하는 바

    # === 점수 정보 (참고용) ===
    total_score: float = 0.0
    grade: str = ""
    repainting_risk: str = ""
    overfitting_risk: str = ""

    def to_dict(self) -> Dict:
        """딕셔너리로 변환"""
        return asdict(self)


# Claude API 프롬프트
EXPLANATION_PROMPT = """당신은 트레이딩 전략을 완전 초보자에게 설명하는 친절한 전문가입니다.

## 중요 지침
1. 전문 용어는 반드시 쉬운 말로 풀어서 설명하세요
2. 비유와 예시를 적극 활용하세요
3. 한국어로 자연스럽게 작성하세요
4. 초등학생도 이해할 수 있는 수준으로 설명하세요

## 전략 정보
- 제목: {title}
- 설명: {description}

## 분석 결과
- 총점: {total_score}/100
- 등급: {grade}
- 리페인팅 위험: {repainting_risk}
- 리페인팅 이슈 수: {repainting_issue_count}개
- 오버피팅 위험: {overfitting_risk}
- 오버피팅 이슈 수: {overfitting_issue_count}개

## 백테스트 성과
{performance}

## Pine Script 코드
```pinescript
{pine_code}
```

## 응답 형식 (반드시 아래 JSON 구조를 따르세요)
{{
    "one_line_summary": "이 전략을 한 줄로 설명 (예: 두 이동평균선이 교차할 때 매매하는 전략)",

    "strategy_type": "추세추종/평균회귀/돌파/스캘핑/스윙/모멘텀/변동성/그리드 중 하나",
    "strategy_type_explanation": "이 전략 유형이 무엇인지 초보자에게 2문장으로 설명",

    "difficulty_level": "초급/중급/고급 중 하나",

    "how_it_works": "전략이 어떻게 작동하는지 2-3문장으로 쉽게 설명",
    "entry_condition": "언제 매수/매도하는지 일상적인 비유를 들어 설명",
    "exit_condition": "언제 포지션을 청산하는지 쉽게 설명",

    "indicators_used": ["사용된 지표 이름 (한국어)"],

    "strengths": ["장점1 (구체적으로)", "장점2"],
    "weaknesses": ["단점1 (구체적으로)", "단점2"],

    "suitable_markets": ["이 전략이 잘 작동하는 시장 상황1", "상황2"],
    "unsuitable_markets": ["이 전략이 잘 안 맞는 시장 상황1", "상황2"],
    "recommended_timeframe": "권장 타임프레임 (예: 1시간봉, 4시간봉)",

    "risk_warning": "이 전략 사용 시 가장 주의해야 할 위험 요소 (구체적으로)",
    "beginner_advice": "초보자에게 해주고 싶은 핵심 조언 (2-3문장)",

    "backtest_interpretation": "백테스트 결과가 의미하는 바를 초보자 눈높이로 설명"
}}"""


class StrategyExplainer:
    """
    초보자용 전략 설명 생성기 (Claude API 버전)

    주요 기능:
    1. Pine Script 코드 분석 및 초보자용 설명 생성
    2. 전략 유형 분류 (추세추종, 평균회귀, 돌파 등)
    3. 사용 지표 상세 설명 (초보자 눈높이)
    4. 장단점 분석
    5. 적합한 시장 상황 안내
    6. 사용 권장 여부 결정 (점수 기반)
    """

    # 권장 여부 결정 임계값
    RECOMMENDATION_THRESHOLDS = {
        "recommended": {
            "min_score": 70,
            "max_repainting_issues": 0,
            "max_overfitting_issues": 2,
            "allowed_grades": ["A", "B"]
        },
        "review_needed": {
            "min_score": 45,
            "max_repainting_issues": 2,
            "max_overfitting_issues": 4,
            "allowed_grades": ["A", "B", "C"]
        }
        # 그 외는 not_recommended
    }

    def __init__(
        self,
        api_key: str = None,
        model: str = "claude-sonnet-4-20250514"  # 비용 효율적인 모델
    ):
        """
        Args:
            api_key: Anthropic API 키 (없으면 환경변수에서 가져옴)
            model: 사용할 Claude 모델 (기본: claude-sonnet-4-20250514)
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.model = model
        self.client = None

        if HAS_ANTHROPIC and self.api_key:
            self.client = anthropic.AsyncAnthropic(api_key=self.api_key)

    async def explain_strategy(
        self,
        pine_code: str,
        title: str,
        description: str = "",
        analysis_result: Optional[Dict] = None,
        performance: Optional[Dict] = None
    ) -> StrategyExplanation:
        """
        전략을 초보자 눈높이로 설명

        Args:
            pine_code: Pine Script 코드
            title: 전략 제목
            description: 전략 설명
            analysis_result: 분석 결과 (scorer에서 온 결과)
            performance: 백테스트 성과 데이터

        Returns:
            StrategyExplanation: 초보자용 전략 설명
        """
        if analysis_result is None:
            analysis_result = {}
        if performance is None:
            performance = {}

        # 분석 결과에서 정보 추출
        total_score = analysis_result.get("total_score", 0)
        grade = analysis_result.get("grade", "N/A")

        repainting_analysis = analysis_result.get("repainting_analysis", {})
        overfitting_analysis = analysis_result.get("overfitting_analysis", {})

        repainting_issues = repainting_analysis.get("issues", [])
        overfitting_concerns = overfitting_analysis.get("concerns", [])

        # 1. 사용 권장 여부 결정 (규칙 기반)
        recommendation = self._determine_recommendation(
            total_score=total_score,
            repainting_issues=repainting_issues,
            overfitting_concerns=overfitting_concerns,
            grade=grade
        )

        # 2. 성과 데이터 포맷팅
        perf_text = self._format_performance(performance)

        # Claude API 사용 가능한 경우
        if self.client:
            try:
                llm_result = await self._call_llm(
                    pine_code=pine_code,
                    title=title,
                    description=description,
                    total_score=total_score,
                    grade=grade,
                    repainting_analysis=repainting_analysis,
                    overfitting_analysis=overfitting_analysis,
                    repainting_issues=repainting_issues,
                    overfitting_concerns=overfitting_concerns,
                    perf_text=perf_text
                )
            except Exception as e:
                logger.error(f"LLM 호출 실패: {e}")
                llm_result = {}
        else:
            logger.warning("Claude API 클라이언트가 없습니다. 기본 설명을 생성합니다.")
            llm_result = {}

        # 결과 조합
        return StrategyExplanation(
            # LLM 결과
            one_line_summary=llm_result.get("one_line_summary", "자동 분석된 트레이딩 전략"),
            strategy_type=llm_result.get("strategy_type", "분석 필요"),
            strategy_type_explanation=llm_result.get("strategy_type_explanation", ""),
            difficulty_level=llm_result.get("difficulty_level", "중급"),
            how_it_works=llm_result.get("how_it_works", "상세 분석이 필요합니다."),
            entry_condition=llm_result.get("entry_condition", "코드 분석 필요"),
            exit_condition=llm_result.get("exit_condition", "코드 분석 필요"),
            indicators_used=llm_result.get("indicators_used", []),
            strengths=llm_result.get("strengths", []),
            weaknesses=llm_result.get("weaknesses", []),
            suitable_markets=llm_result.get("suitable_markets", []),
            unsuitable_markets=llm_result.get("unsuitable_markets", []),
            recommended_timeframe=llm_result.get("recommended_timeframe", ""),
            risk_warning=llm_result.get("risk_warning", "충분한 테스트 후 사용하세요."),
            beginner_advice=llm_result.get("beginner_advice", "실거래 전 데모 계좌에서 충분히 테스트하세요."),
            backtest_interpretation=llm_result.get("backtest_interpretation", ""),

            # 규칙 기반 권장 여부
            recommendation_level=recommendation["level"],
            recommendation_icon=recommendation["icon"],
            recommendation_title=recommendation["title"],
            recommendation_reason=recommendation["reason"],
            recommendation_details=recommendation["details"],

            # 점수 정보
            total_score=total_score,
            grade=grade,
            repainting_risk=self._get_risk_level_korean(repainting_analysis),
            overfitting_risk=self._get_risk_level_korean(overfitting_analysis)
        )

    async def _call_llm(
        self,
        pine_code: str,
        title: str,
        description: str,
        total_score: float,
        grade: str,
        repainting_analysis: Dict,
        overfitting_analysis: Dict,
        repainting_issues: List[str],
        overfitting_concerns: List[str],
        perf_text: str
    ) -> Dict:
        """Claude API 호출"""

        prompt = EXPLANATION_PROMPT.format(
            title=title,
            description=description[:500] if description else "설명 없음",
            total_score=total_score,
            grade=grade,
            repainting_risk=self._get_risk_level_korean(repainting_analysis),
            repainting_issue_count=len(repainting_issues),
            overfitting_risk=self._get_risk_level_korean(overfitting_analysis),
            overfitting_issue_count=len(overfitting_concerns),
            performance=perf_text,
            pine_code=pine_code[:4000] if pine_code else "코드 없음"
        )

        response = await self.client.messages.create(
            model=self.model,
            max_tokens=2000,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )

        response_text = response.content[0].text
        return self._parse_json_response(response_text)

    def _determine_recommendation(
        self,
        total_score: float,
        repainting_issues: List[str],
        overfitting_concerns: List[str],
        grade: str
    ) -> Dict:
        """
        사용 권장 여부 결정 (규칙 기반)

        결정 기준:
        1. total_score: 종합 점수
        2. repainting_issues: 리페인팅 문제 (치명적)
        3. overfitting_concerns: 과적합 우려 사항
        4. grade: 등급 (A, B, C, D, F)
        """
        details = []

        # 치명적 리페인팅 체크 (최우선)
        critical_repainting = any("CRITICAL" in str(issue).upper() for issue in repainting_issues)
        high_repainting = any("HIGH" in str(issue).upper() for issue in repainting_issues)

        if critical_repainting:
            details.append("치명적 리페인팅 문제 발견 - 백테스트 결과 신뢰 불가")
            return {
                "level": RecommendationLevel.NOT_RECOMMENDED.value,
                "icon": "❌",
                "title": "사용 비권장",
                "reason": "치명적인 리페인팅 문제가 발견되었습니다. "
                         "이 전략의 백테스트 결과는 실제 거래와 크게 다를 수 있어 사용을 권장하지 않습니다.",
                "details": details
            }

        # F 등급 즉시 거부
        if grade == "F":
            details.append(f"등급 F - 기본 품질 기준 미달")
            return {
                "level": RecommendationLevel.NOT_RECOMMENDED.value,
                "icon": "❌",
                "title": "사용 비권장",
                "reason": "전략 품질 평가에서 F등급을 받았습니다. "
                         "여러 심각한 문제가 발견되어 사용을 권장하지 않습니다.",
                "details": details
            }

        # 점수 기반 평가
        repainting_count = len(repainting_issues)
        overfitting_count = len(overfitting_concerns)

        # 권장 기준 체크
        recommended_threshold = self.RECOMMENDATION_THRESHOLDS["recommended"]
        review_threshold = self.RECOMMENDATION_THRESHOLDS["review_needed"]

        # 점수 평가
        if total_score >= recommended_threshold["min_score"]:
            details.append(f"총점 {total_score:.1f}점 - 양호")
        elif total_score >= review_threshold["min_score"]:
            details.append(f"총점 {total_score:.1f}점 - 보통")
        else:
            details.append(f"총점 {total_score:.1f}점 - 미흡")

        # 리페인팅 평가
        if repainting_count == 0:
            details.append("리페인팅 문제 없음")
        elif repainting_count <= recommended_threshold["max_repainting_issues"]:
            details.append(f"경미한 리페인팅 우려 {repainting_count}건")
        else:
            details.append(f"리페인팅 우려 {repainting_count}건 - 주의 필요")

        # 과적합 평가
        if overfitting_count <= recommended_threshold["max_overfitting_issues"]:
            details.append(f"과적합 우려 낮음 ({overfitting_count}건)")
        elif overfitting_count <= review_threshold["max_overfitting_issues"]:
            details.append(f"과적합 우려 있음 ({overfitting_count}건)")
        else:
            details.append(f"과적합 위험 높음 ({overfitting_count}건)")

        # 최종 결정
        # 사용 권장 조건
        if (total_score >= recommended_threshold["min_score"] and
            repainting_count <= recommended_threshold["max_repainting_issues"] and
            overfitting_count <= recommended_threshold["max_overfitting_issues"] and
            not high_repainting and
            grade in recommended_threshold["allowed_grades"]):

            return {
                "level": RecommendationLevel.RECOMMENDED.value,
                "icon": "✅",
                "title": "사용 권장",
                "reason": f"총점 {total_score:.1f}점으로 양호하며, "
                         f"리페인팅/과적합 위험이 낮습니다. "
                         f"실제 사용 전 충분한 테스트를 권장합니다.",
                "details": details
            }

        # 검토 필요 조건
        elif (total_score >= review_threshold["min_score"] and
              repainting_count <= review_threshold["max_repainting_issues"] and
              overfitting_count <= review_threshold["max_overfitting_issues"] and
              grade in review_threshold["allowed_grades"]):

            warnings = []
            if high_repainting:
                warnings.append("리페인팅 우려")
            if overfitting_count > recommended_threshold["max_overfitting_issues"]:
                warnings.append("과적합 가능성")
            if total_score < recommended_threshold["min_score"]:
                warnings.append("점수 다소 낮음")

            warning_text = ", ".join(warnings) if warnings else "일부 개선 필요"

            return {
                "level": RecommendationLevel.REVIEW_NEEDED.value,
                "icon": "⚠️",
                "title": "검토 필요",
                "reason": f"총점 {total_score:.1f}점으로 사용 가능하나, "
                         f"{warning_text} 사항이 있습니다. "
                         f"실거래 전 해당 부분을 반드시 확인하세요.",
                "details": details
            }

        # 사용 비권장
        else:
            problems = []
            if total_score < review_threshold["min_score"]:
                problems.append(f"낮은 점수 ({total_score:.1f}점)")
            if repainting_count > review_threshold["max_repainting_issues"]:
                problems.append(f"리페인팅 문제 다수 ({repainting_count}건)")
            if overfitting_count > review_threshold["max_overfitting_issues"]:
                problems.append(f"과적합 위험 높음 ({overfitting_count}건)")
            if high_repainting:
                problems.append("높은 리페인팅 위험")
            if grade not in review_threshold["allowed_grades"]:
                problems.append(f"낮은 등급 ({grade})")

            problem_text = ", ".join(problems) if problems else "여러 문제 발견"

            return {
                "level": RecommendationLevel.NOT_RECOMMENDED.value,
                "icon": "❌",
                "title": "사용 비권장",
                "reason": f"{problem_text}으로 인해 사용을 권장하지 않습니다. "
                         f"실거래 시 예상치 못한 손실이 발생할 수 있습니다.",
                "details": details
            }

    def _format_performance(self, performance: Dict) -> str:
        """성과 데이터를 읽기 쉽게 포맷팅"""
        if not performance:
            return "백테스트 데이터 없음"

        lines = []

        # 주요 지표 한글화 및 초보자 설명 추가
        key_mapping = {
            "net_profit": ("순수익", "전체 이익 - 손실"),
            "net_profit_pct": ("순수익률", "투자 대비 수익 비율"),
            "net_profit_percent": ("순수익률", "투자 대비 수익 비율"),
            "total_trades": ("총 거래 수", "매매 횟수"),
            "win_rate": ("승률", "이긴 거래 비율"),
            "profit_factor": ("수익 팩터", "총이익/총손실, 1.5 이상 권장"),
            "max_drawdown": ("최대 손실폭", "가장 크게 잃었던 금액"),
            "max_drawdown_pct": ("최대 손실률", "가장 크게 잃었던 비율"),
            "max_drawdown_percent": ("최대 손실률", "가장 크게 잃었던 비율"),
            "avg_trade": ("평균 거래 수익", "거래당 평균 수익"),
            "sharpe_ratio": ("샤프 비율", "위험 대비 수익, 1 이상 양호"),
            "avg_bars_in_trade": ("평균 보유 기간", "거래당 평균 보유 봉 수")
        }

        for key, (korean_name, desc) in key_mapping.items():
            if key in performance:
                value = performance[key]
                if isinstance(value, (int, float)):
                    if "pct" in key or "percent" in key or "rate" in key:
                        lines.append(f"- {korean_name}: {value:.2f}% ({desc})")
                    elif key == "profit_factor":
                        quality = "우수" if value >= 1.5 else "보통" if value >= 1.0 else "주의"
                        lines.append(f"- {korean_name}: {value:.2f} [{quality}] ({desc})")
                    elif key == "sharpe_ratio":
                        quality = "우수" if value >= 1.0 else "보통" if value >= 0.5 else "낮음"
                        lines.append(f"- {korean_name}: {value:.2f} [{quality}] ({desc})")
                    else:
                        lines.append(f"- {korean_name}: {value:.2f} ({desc})")
                else:
                    lines.append(f"- {korean_name}: {value} ({desc})")

        return "\n".join(lines) if lines else "상세 성과 데이터 없음"

    def _get_risk_level_korean(self, analysis: Dict) -> str:
        """위험 수준을 한글로 변환"""
        if not analysis:
            return "분석 안됨"

        risk_level = analysis.get("risk_level", "")
        if isinstance(risk_level, dict):
            risk_level = risk_level.get("value", "unknown")

        mapping = {
            "NONE": "없음 ✅",
            "LOW": "낮음 ✅",
            "MEDIUM": "중간 ⚠️",
            "HIGH": "높음 ⚠️",
            "CRITICAL": "매우 높음 ❌",
            "none": "없음 ✅",
            "low": "낮음 ✅",
            "medium": "중간 ⚠️",
            "high": "높음 ⚠️",
            "critical": "매우 높음 ❌",
            "excellent": "우수 ✅",
            "good": "양호 ✅",
            "fair": "보통 ⚠️",
            "poor": "미흡 ⚠️",
        }

        return mapping.get(str(risk_level), str(risk_level))

    def _parse_json_response(self, response_text: str) -> Dict:
        """LLM 응답에서 JSON 추출"""
        import re

        try:
            # 직접 파싱 시도
            return json.loads(response_text)
        except json.JSONDecodeError:
            pass

        # 코드 블록 안에 있는 경우
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response_text)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        # { } 사이 추출
        brace_match = re.search(r'\{[\s\S]*\}', response_text)
        if brace_match:
            try:
                return json.loads(brace_match.group(0))
            except json.JSONDecodeError:
                pass

        logger.warning("JSON 파싱 실패, 빈 딕셔너리 반환")
        return {}

    async def get_quick_summary(
        self,
        pine_code: str,
        max_length: int = 100
    ) -> str:
        """전략 빠른 요약 (짧은 버전)"""

        if not self.client:
            return "전략 요약 생성에 실패했습니다. (API 키 필요)"

        prompt = f"""다음 Pine Script 전략을 {max_length}자 이내로 한국어로 간단히 요약하세요.
초보자도 이해할 수 있게 작성하세요.

코드:
```pinescript
{pine_code[:2000]}
```

요약 (한 문장):"""

        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=200,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text.strip()
        except Exception as e:
            logger.error(f"빠른 요약 생성 실패: {e}")
            return "전략 요약 생성에 실패했습니다."


# 편의 함수
async def create_beginner_explanation(
    pine_code: str,
    title: str,
    analysis_result: Dict,
    performance: Dict = None,
    api_key: str = None
) -> StrategyExplanation:
    """
    초보자용 전략 설명 생성 편의 함수

    Usage:
        explanation = await create_beginner_explanation(
            pine_code="...",
            title="My Strategy",
            analysis_result=scorer_result,
            api_key="sk-ant-..."
        )
        print(f"{explanation.recommendation_icon} {explanation.recommendation_title}")
        print(explanation.recommendation_reason)
    """
    api_key = api_key or os.getenv("ANTHROPIC_API_KEY")

    explainer = StrategyExplainer(api_key=api_key)
    return await explainer.explain_strategy(
        pine_code=pine_code,
        title=title,
        analysis_result=analysis_result,
        performance=performance or {}
    )
