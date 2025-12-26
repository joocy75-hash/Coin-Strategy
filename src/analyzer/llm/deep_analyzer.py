# src/analyzer/llm/deep_analyzer.py

import json
import logging
from typing import Dict, List
from dataclasses import dataclass
import anthropic

from .prompts import ANALYSIS_PROMPT_TEMPLATE, CONVERSION_PROMPT_TEMPLATE

logger = logging.getLogger(__name__)

@dataclass
class LLMAnalysisResult:
    """LLM 분석 결과"""
    logic_score: int  # 1-10
    risk_score: int
    practical_score: int
    code_quality_score: int
    total_score: int  # 0-100
    recommendation: str  # PASS, REVIEW, REJECT
    strengths: List[str]
    weaknesses: List[str]
    summary_kr: str
    conversion_notes: str
    raw_response: Dict

class LLMDeepAnalyzer:
    """
    LLM을 활용한 Pine Script 심층 분석 (Claude API)

    역할:
    1. 전략 로직 평가 (시장 원리 부합 여부)
    2. 리스크 관리 수준 평가
    3. 실거래 적합성 판단
    4. Python 변환 가능성 평가
    """

    def __init__(
        self,
        api_key: str,
        model: str = "claude-3-5-sonnet-20241022"
    ):
        self.client = anthropic.AsyncAnthropic(api_key=api_key)
        self.model = model

    async def analyze_strategy(
        self,
        pine_code: str,
        title: str,
        description: str,
        performance: Dict,
        rule_analysis: Dict
    ) -> LLMAnalysisResult:
        """전략 심층 분석"""

        # 코드 길이 제한 (토큰 절약)
        code_truncated = pine_code[:6000] if pine_code else ""

        prompt = ANALYSIS_PROMPT_TEMPLATE.format(
            title=title,
            description=description[:1000],
            performance=json.dumps(performance, ensure_ascii=False),
            rule_analysis=json.dumps(rule_analysis, ensure_ascii=False),
            pine_code=code_truncated
        )

        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=1500,
                messages=[{"role": "user", "content": prompt + "\n\nJSON 형식으로만 응답해주세요."}]
            )

            result = json.loads(response.content[0].text)

            # 총점 계산
            total_score = (
                result.get('logic_score', 5) * 2.5 +
                result.get('risk_score', 5) * 2.5 +
                result.get('practical_score', 5) * 2.5 +
                result.get('code_quality_score', 5) * 2.5
            )

            return LLMAnalysisResult(
                logic_score=result.get('logic_score', 5),
                risk_score=result.get('risk_score', 5),
                practical_score=result.get('practical_score', 5),
                code_quality_score=result.get('code_quality_score', 5),
                total_score=int(total_score),
                recommendation=result.get('overall_recommendation', 'REVIEW'),
                strengths=result.get('key_strengths', []),
                weaknesses=result.get('key_weaknesses', []),
                summary_kr=result.get('summary_kr', ''),
                conversion_notes=result.get('conversion_notes', ''),
                raw_response=result
            )

        except Exception as e:
            logger.error(f"LLM analysis error: {e}")
            return LLMAnalysisResult(
                logic_score=5,
                risk_score=5,
                practical_score=5,
                code_quality_score=5,
                total_score=50,
                recommendation="ERROR",
                strengths=[],
                weaknesses=[str(e)],
                summary_kr="분석 중 오류 발생",
                conversion_notes="",
                raw_response={"error": str(e)}
            )

    async def convert_pine_to_python(
        self,
        pine_code: str,
        strategy_type: str = "basic"
    ) -> str:
        """Pine Script를 Python으로 변환"""

        prompt = CONVERSION_PROMPT_TEMPLATE.format(
            pine_code=pine_code[:8000],
            strategy_type=strategy_type
        )

        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=4000,
                messages=[{"role": "user", "content": prompt}]
            )

            return response.content[0].text

        except Exception as e:
            logger.error(f"Conversion error: {e}")
            return ""

    async def get_strategy_summary(self, pine_code: str) -> str:
        """전략 요약 생성"""

        prompt = f"""다음 Pine Script 전략을 간결하게 요약해주세요:

```pinescript
{pine_code[:3000]}
```

요약 형식:
1. 전략 유형 (추세추종/역추세/스캘핑 등)
2. 사용 지표
3. 진입/청산 조건 (간략히)
4. 리스크 관리 방식

한국어로 200자 이내로 작성해주세요."""

        try:
            response = await self.client.messages.create(
                model="claude-3-5-haiku-20241022",  # 요약은 저비용 모델
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}]
            )

            return response.content[0].text

        except Exception as e:
            logger.error(f"Summary error: {e}")
            return "요약 생성 실패"
