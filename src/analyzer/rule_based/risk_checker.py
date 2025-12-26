# src/analyzer/rule_based/risk_checker.py

import re
from dataclasses import dataclass
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class RiskAnalysis:
    """리스크 관리 분석 결과"""
    score: float  # 0-100 (높을수록 리스크 관리 우수)
    risk_level: str  # excellent, good, fair, poor, critical
    has_stop_loss: bool
    has_take_profit: bool
    has_position_sizing: bool
    has_max_drawdown_check: bool
    concerns: List[str]
    positives: List[str]
    recommendations: List[str]


class RiskChecker:
    """
    전략 리스크 관리 수준 평가

    평가 항목:
    1. Stop Loss 구현 여부
    2. Take Profit 구현 여부
    3. Position Sizing 로직
    4. 최대 손실 제한 메커니즘
    5. 마진 / 레버리지 관리
    """

    # Stop Loss 패턴
    STOP_LOSS_PATTERNS = [
        (r'stop\s*=', "stop 변수 사용"),
        (r'strategy\.exit\s*\([^)]*stop\s*=', "strategy.exit stop 파라미터"),
        (r'strategy\.exit\s*\([^)]*loss\s*=', "strategy.exit loss 파라미터"),
        (r'sl\s*=', "sl 변수 사용"),
        (r'stopLoss', "stopLoss 변수"),
        (r'stop_loss', "stop_loss 변수"),
        (r'stoploss', "stoploss 변수"),
    ]

    # Take Profit 패턴
    TAKE_PROFIT_PATTERNS = [
        (r'profit\s*=', "profit 변수 사용"),
        (r'strategy\.exit\s*\([^)]*profit\s*=', "strategy.exit profit 파라미터"),
        (r'strategy\.exit\s*\([^)]*limit\s*=', "strategy.exit limit 파라미터"),
        (r'tp\s*=', "tp 변수 사용"),
        (r'takeProfit', "takeProfit 변수"),
        (r'take_profit', "take_profit 변수"),
        (r'target\s*=', "target 변수 사용"),
    ]

    # Position Sizing 패턴
    POSITION_SIZING_PATTERNS = [
        (r'strategy\.percent_of_equity', "자산 비율 사용"),
        (r'strategy\s*\([^)]*default_qty_type\s*=\s*strategy\.percent_of_equity',
         "기본 수량 = 자산 비율"),
        (r'position_size\s*=', "포지션 사이즈 변수"),
        (r'qty\s*=.*\*', "동적 수량 계산"),
        (r'risk\s*=.*percent', "리스크 퍼센트 계산"),
    ]

    # Max Drawdown 관련 패턴
    MAX_DRAWDOWN_PATTERNS = [
        (r'strategy\.risk\.max_drawdown', "최대 손실폭 제한"),
        (r'drawdown', "drawdown 관련 로직"),
        (r'max_loss', "최대 손실 변수"),
        (r'equity\s*<', "자산 하한선 체크"),
    ]

    # 위험한 패턴
    DANGEROUS_PATTERNS = [
        (r'strategy\.percent_of_equity\s*,\s*100', "자산 100% 투자 (매우 위험)"),
        (r'pyramiding\s*=\s*[5-9]\d*', "과도한 피라미딩"),
        (r'leverage\s*=\s*[2-9]\d', "높은 레버리지 (20배 이상)"),
        (r'margin\s*=\s*[1-9]\d{2,}', "높은 마진"),
    ]

    def analyze(self, pine_code: str) -> RiskAnalysis:
        """리스크 관리 수준 분석"""

        if not pine_code:
            return RiskAnalysis(
                score=0,
                risk_level="unknown",
                has_stop_loss=False,
                has_take_profit=False,
                has_position_sizing=False,
                has_max_drawdown_check=False,
                concerns=["코드 없음"],
                positives=[],
                recommendations=["코드를 제공해주세요."]
            )

        concerns = []
        positives = []
        recommendations = []
        score = 0

        # 1. Stop Loss 분석
        has_stop_loss = self._check_patterns(pine_code, self.STOP_LOSS_PATTERNS)
        if has_stop_loss:
            score += 30
            positives.append("Stop Loss 구현됨")
        else:
            concerns.append("Stop Loss 미구현")
            recommendations.append("반드시 Stop Loss를 구현하세요.")

        # 2. Take Profit 분석
        has_take_profit = self._check_patterns(pine_code, self.TAKE_PROFIT_PATTERNS)
        if has_take_profit:
            score += 20
            positives.append("Take Profit 구현됨")
        else:
            concerns.append("Take Profit 미구현")
            recommendations.append("Take Profit 로직을 추가하는 것이 좋습니다.")

        # 3. Position Sizing 분석
        has_position_sizing = self._check_patterns(pine_code, self.POSITION_SIZING_PATTERNS)
        if has_position_sizing:
            score += 25
            positives.append("Position Sizing 로직 존재")
        else:
            concerns.append("고정 수량 사용 (동적 포지션 사이징 없음)")
            recommendations.append("자산 비율 기반 포지션 사이징을 고려하세요.")

        # 4. Max Drawdown 분석
        has_max_drawdown = self._check_patterns(pine_code, self.MAX_DRAWDOWN_PATTERNS)
        if has_max_drawdown:
            score += 15
            positives.append("최대 손실폭 제한 구현")
        else:
            recommendations.append("최대 손실폭 제한 로직을 추가하면 좋습니다.")

        # 5. 위험한 패턴 체크
        dangerous_score, dangerous_concerns = self._check_dangerous_patterns(pine_code)
        score -= dangerous_score
        concerns.extend(dangerous_concerns)

        # 6. 추가 분석
        additional_score, additional_positives, additional_concerns = self._additional_checks(pine_code)
        score += additional_score
        positives.extend(additional_positives)
        concerns.extend(additional_concerns)

        # 점수 범위 제한
        score = max(0, min(100, score))

        # 위험 수준 결정
        if score >= 80:
            risk_level = "excellent"
        elif score >= 60:
            risk_level = "good"
        elif score >= 40:
            risk_level = "fair"
        elif score >= 20:
            risk_level = "poor"
        else:
            risk_level = "critical"
            recommendations.insert(0, "리스크 관리가 매우 부족합니다. 실거래 전 반드시 개선이 필요합니다.")

        return RiskAnalysis(
            score=score,
            risk_level=risk_level,
            has_stop_loss=has_stop_loss,
            has_take_profit=has_take_profit,
            has_position_sizing=has_position_sizing,
            has_max_drawdown_check=has_max_drawdown,
            concerns=concerns,
            positives=positives,
            recommendations=recommendations
        )

    def _check_patterns(self, code: str, patterns: List[tuple]) -> bool:
        """패턴 존재 여부 확인"""
        for pattern, _ in patterns:
            if re.search(pattern, code, re.IGNORECASE):
                return True
        return False

    def _check_dangerous_patterns(self, code: str) -> tuple[float, List[str]]:
        """위험한 패턴 체크"""
        concerns = []
        penalty = 0

        for pattern, description in self.DANGEROUS_PATTERNS:
            if re.search(pattern, code, re.IGNORECASE):
                concerns.append(f"위험: {description}")
                penalty += 15

        return penalty, concerns

    def _additional_checks(self, code: str) -> tuple[float, List[str], List[str]]:
        """추가 분석"""
        positives = []
        concerns = []
        score = 0

        # 트레일링 스탑
        if re.search(r'trail', code, re.IGNORECASE):
            score += 10
            positives.append("트레일링 스탑 사용")

        # ATR 기반 스탑
        if re.search(r'atr.*stop|stop.*atr', code, re.IGNORECASE):
            score += 5
            positives.append("ATR 기반 동적 스탑")

        # 시간 기반 청산
        if re.search(r'time.*exit|exit.*time|bars.*since', code, re.IGNORECASE):
            positives.append("시간 기반 청산 로직")

        # 복수 포지션 관리
        if re.search(r'strategy\.position_size', code, re.IGNORECASE):
            positives.append("포지션 상태 확인 로직")

        # 변동성 필터
        if re.search(r'atr|volatility|stddev', code, re.IGNORECASE):
            positives.append("변동성 기반 필터")

        # 거래 시간 필터
        if re.search(r'session|hour|dayofweek', code, re.IGNORECASE):
            positives.append("거래 시간 필터")

        # 위험 신호: 마틴게일
        if re.search(r'martingale|double.*loss|loss.*double', code, re.IGNORECASE):
            concerns.append("마틴게일 전략 의심 (매우 위험)")
            score -= 30

        # 위험 신호: 평균 단가
        if re.search(r'average.*down|down.*average', code, re.IGNORECASE):
            concerns.append("물타기 전략 의심")
            score -= 15

        return score, positives, concerns
