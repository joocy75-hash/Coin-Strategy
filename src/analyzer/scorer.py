# src/analyzer/scorer.py

import logging
from dataclasses import dataclass
from typing import Dict, Optional
from datetime import datetime

from .rule_based.repainting_detector import RepaintingDetector, RepaintingRisk
from .rule_based.overfitting_detector import OverfittingDetector
from .rule_based.risk_checker import RiskChecker
from .llm.deep_analyzer import LLMDeepAnalyzer, LLMAnalysisResult

logger = logging.getLogger(__name__)


@dataclass
class FinalScore:
    """최종 점수"""
    total_score: float  # 0-100
    grade: str  # A, B, C, D, F
    status: str  # passed, review, rejected

    # 세부 점수
    repainting_score: float
    overfitting_score: float
    risk_score: float
    llm_score: float

    # 분석 결과
    repainting_analysis: Dict
    overfitting_analysis: Dict
    risk_analysis: Dict
    llm_analysis: Optional[Dict]

    # 메타
    analyzed_at: datetime
    analysis_version: str = "1.0"


class StrategyScorer:
    """
    전략 종합 점수 산출

    점수 구성:
    - Repainting 안전도: 25%
    - 과적합 위험도: 25%
    - 리스크 관리: 20%
    - LLM 심층 분석: 30%
    """

    WEIGHTS = {
        "repainting": 0.25,
        "overfitting": 0.25,
        "risk": 0.20,
        "llm": 0.30
    }

    GRADE_THRESHOLDS = {
        "A": 85,
        "B": 70,
        "C": 55,
        "D": 40,
        "F": 0
    }

    def __init__(self, llm_api_key: Optional[str] = None, llm_model: str = "gpt-4o"):
        self.repainting_detector = RepaintingDetector()
        self.overfitting_detector = OverfittingDetector()
        self.risk_checker = RiskChecker()

        self.llm_analyzer = None
        if llm_api_key:
            self.llm_analyzer = LLMDeepAnalyzer(api_key=llm_api_key, model=llm_model)

    async def score_strategy(
        self,
        pine_code: str,
        title: str = "",
        description: str = "",
        performance: Optional[Dict] = None,
        inputs: Optional[list] = None,
        skip_llm: bool = False
    ) -> FinalScore:
        """전략 종합 점수 산출"""

        performance = performance or {}

        # 1. Repainting 분석 (규칙 기반)
        repainting = self.repainting_detector.analyze(pine_code)
        repainting_score = repainting.score

        # 치명적 Repainting → 즉시 거부
        if repainting.risk_level == RepaintingRisk.CRITICAL:
            return FinalScore(
                total_score=0,
                grade="F",
                status="rejected",
                repainting_score=0,
                overfitting_score=0,
                risk_score=0,
                llm_score=0,
                repainting_analysis={
                    "risk_level": repainting.risk_level.name,
                    "issues": repainting.issues,
                    "details": repainting.details
                },
                overfitting_analysis={},
                risk_analysis={},
                llm_analysis=None,
                analyzed_at=datetime.now()
            )

        # 2. 과적합 분석 (규칙 기반)
        overfitting = self.overfitting_detector.analyze(pine_code, performance, inputs)
        # 과적합 점수 반전 (낮을수록 좋음 → 높을수록 좋음)
        overfitting_score = 100 - overfitting.score

        # 심각한 과적합 → 거부
        if overfitting.risk_level == "critical":
            return FinalScore(
                total_score=15,
                grade="F",
                status="rejected",
                repainting_score=repainting_score,
                overfitting_score=overfitting_score,
                risk_score=0,
                llm_score=0,
                repainting_analysis={
                    "risk_level": repainting.risk_level.name,
                    "issues": repainting.issues,
                },
                overfitting_analysis={
                    "risk_level": overfitting.risk_level,
                    "concerns": overfitting.concerns,
                    "parameter_count": overfitting.parameter_count
                },
                risk_analysis={},
                llm_analysis=None,
                analyzed_at=datetime.now()
            )

        # 3. 리스크 관리 분석
        risk = self.risk_checker.analyze(pine_code)
        risk_score = risk.score

        # 4. LLM 분석 (옵션)
        llm_score = 50  # 기본값
        llm_result = None

        if self.llm_analyzer and not skip_llm:
            try:
                llm_analysis = await self.llm_analyzer.analyze_strategy(
                    pine_code=pine_code,
                    title=title,
                    description=description,
                    performance=performance,
                    rule_analysis={
                        "repainting": {
                            "risk": repainting.risk_level.name,
                            "score": repainting_score
                        },
                        "overfitting": {
                            "risk": overfitting.risk_level,
                            "score": overfitting.score
                        },
                        "risk_management": {
                            "level": risk.risk_level,
                            "score": risk_score
                        }
                    }
                )
                llm_score = llm_analysis.total_score
                llm_result = {
                    "scores": {
                        "logic": llm_analysis.logic_score,
                        "risk": llm_analysis.risk_score,
                        "practical": llm_analysis.practical_score,
                        "code_quality": llm_analysis.code_quality_score
                    },
                    "recommendation": llm_analysis.recommendation,
                    "strengths": llm_analysis.strengths,
                    "weaknesses": llm_analysis.weaknesses,
                    "summary": llm_analysis.summary_kr
                }
            except Exception as e:
                logger.error(f"LLM analysis failed: {e}")

        # 5. 최종 점수 계산
        total_score = (
            repainting_score * self.WEIGHTS["repainting"] +
            overfitting_score * self.WEIGHTS["overfitting"] +
            risk_score * self.WEIGHTS["risk"] +
            llm_score * self.WEIGHTS["llm"]
        )

        # 6. 등급 결정
        grade = "F"
        for g, threshold in self.GRADE_THRESHOLDS.items():
            if total_score >= threshold:
                grade = g
                break

        # 7. 상태 결정
        if total_score >= 70:
            status = "passed"
        elif total_score >= 50:
            status = "review"
        else:
            status = "rejected"

        return FinalScore(
            total_score=round(total_score, 1),
            grade=grade,
            status=status,
            repainting_score=round(repainting_score, 1),
            overfitting_score=round(overfitting_score, 1),
            risk_score=round(risk_score, 1),
            llm_score=round(llm_score, 1),
            repainting_analysis={
                "risk_level": repainting.risk_level.name,
                "issues": repainting.issues,
                "safe_patterns": repainting.safe_patterns
            },
            overfitting_analysis={
                "risk_level": overfitting.risk_level,
                "concerns": overfitting.concerns,
                "parameter_count": overfitting.parameter_count,
                "magic_numbers": overfitting.magic_numbers[:5]
            },
            risk_analysis={
                "risk_level": risk.risk_level,
                "has_stop_loss": risk.has_stop_loss,
                "has_take_profit": risk.has_take_profit,
                "has_position_sizing": risk.has_position_sizing,
                "concerns": risk.concerns,
                "positives": risk.positives
            },
            llm_analysis=llm_result,
            analyzed_at=datetime.now()
        )
