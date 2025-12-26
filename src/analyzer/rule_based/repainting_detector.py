# src/analyzer/rule_based/repainting_detector.py

import re
from enum import Enum
from dataclasses import dataclass
from typing import List, Tuple
import logging

logger = logging.getLogger(__name__)

class RepaintingRisk(Enum):
    """Repainting 위험 수준"""
    NONE = 0       # 위험 없음
    LOW = 1        # 낮은 위험
    MEDIUM = 2     # 중간 위험
    HIGH = 3       # 높은 위험
    CRITICAL = 4   # 치명적 (확정적 Repainting)

@dataclass
class RepaintingAnalysis:
    """Repainting 분석 결과"""
    risk_level: RepaintingRisk
    score: float  # 0-100 (높을수록 안전)
    issues: List[str]
    safe_patterns: List[str]
    confidence: float
    details: str

class RepaintingDetector:
    """
    Pine Script Repainting 탐지

    Repainting이란?
    - 과거 캔들의 신호가 실시간으로 바뀌는 현상
    - 백테스트에서는 좋아 보이지만 실거래에서는 작동 안함
    """

    # === 치명적 패턴 (확정적 Repainting) ===
    CRITICAL_PATTERNS = [
        (r'security\s*\([^)]*lookahead\s*=\s*barmerge\.lookahead_on',
         "lookahead_on: 미래 데이터 사용"),
        (r'request\.security\s*\([^)]*lookahead\s*=\s*barmerge\.lookahead_on',
         "request.security with lookahead_on"),
    ]

    # === 고위험 패턴 ===
    HIGH_RISK_PATTERNS = [
        (r'\bclose\s*$', "현재 봉 종가 직접 사용 (봉 완성 전)"),
        (r'barstate\.isrealtime\s*(?:==\s*true|\?)', "실시간 바 상태 의존"),
        (r'barstate\.isconfirmed\s*==\s*false', "미확정 바에서 신호"),
        (r'security\s*\([^)]*\)\s*\[0\]', "security 현재값 (리페인팅 가능)"),
    ]

    # === 중간 위험 패턴 ===
    MEDIUM_RISK_PATTERNS = [
        (r'(?<!request\.)security\s*\((?![^)]*lookahead)',
         "security() 사용 (lookahead 미명시)"),
        (r'request\.security\s*\((?![^)]*lookahead)',
         "request.security (lookahead 미명시)"),
        (r'\bvarip\s+', "varip: 실시간 전용 변수"),
        (r'timenow\b', "timenow: 실시간 시간"),
        (r'tickerid\s*,\s*["\'][^"\']+["\']\s*,\s*close\s*\)',
         "다른 타임프레임 close 직접 사용"),
    ]

    # === 안전한 패턴 (리페인팅 방지) ===
    SAFE_PATTERNS = [
        (r'barstate\.isconfirmed\s*(?:==\s*true|\?)', "봉 완성 확인"),
        (r'\[1\]', "이전 봉 데이터 사용"),
        (r'lookahead\s*=\s*barmerge\.lookahead_off', "lookahead 명시적 비활성화"),
        (r'ta\.valuewhen\s*\([^)]+,\s*[^,]+,\s*[1-9]', "과거 값 참조"),
        (r'fixnan\s*\(', "NaN 처리 (안정성)"),
    ]

    def analyze(self, pine_code: str) -> RepaintingAnalysis:
        """Pine Script 코드의 Repainting 위험 분석"""

        if not pine_code or len(pine_code) < 20:
            return RepaintingAnalysis(
                risk_level=RepaintingRisk.NONE,
                score=0,
                issues=["코드 없음 또는 너무 짧음"],
                safe_patterns=[],
                confidence=0,
                details="분석할 코드가 없습니다."
            )

        issues = []
        safe_patterns = []
        risk_level = RepaintingRisk.NONE

        # 1. 치명적 패턴 검사
        for pattern, description in self.CRITICAL_PATTERNS:
            if re.search(pattern, pine_code, re.IGNORECASE | re.MULTILINE):
                issues.append(f"CRITICAL: {description}")
                risk_level = RepaintingRisk.CRITICAL

        # 치명적이면 바로 반환
        if risk_level == RepaintingRisk.CRITICAL:
            return RepaintingAnalysis(
                risk_level=risk_level,
                score=0,
                issues=issues,
                safe_patterns=[],
                confidence=0.95,
                details="치명적인 Repainting 패턴이 발견되었습니다. 이 전략은 백테스트와 실거래 결과가 다를 가능성이 매우 높습니다."
            )

        # 2. 고위험 패턴 검사
        for pattern, description in self.HIGH_RISK_PATTERNS:
            if re.search(pattern, pine_code, re.IGNORECASE | re.MULTILINE):
                issues.append(f"HIGH: {description}")
                if risk_level.value < RepaintingRisk.HIGH.value:
                    risk_level = RepaintingRisk.HIGH

        # 3. 중간 위험 패턴 검사
        for pattern, description in self.MEDIUM_RISK_PATTERNS:
            if re.search(pattern, pine_code, re.IGNORECASE | re.MULTILINE):
                issues.append(f"MEDIUM: {description}")
                if risk_level.value < RepaintingRisk.MEDIUM.value:
                    risk_level = RepaintingRisk.MEDIUM

        # 4. 안전한 패턴 검사 (감점 완화)
        for pattern, description in self.SAFE_PATTERNS:
            if re.search(pattern, pine_code, re.IGNORECASE | re.MULTILINE):
                safe_patterns.append(f"{description}")

        # 5. 점수 계산 (100점 만점)
        score = 100

        if risk_level == RepaintingRisk.HIGH:
            score -= 50
        elif risk_level == RepaintingRisk.MEDIUM:
            score -= 25
        elif risk_level == RepaintingRisk.LOW:
            score -= 10

        # 고위험 패턴 개수만큼 추가 감점
        high_count = len([i for i in issues if "HIGH" in i])
        medium_count = len([i for i in issues if "MEDIUM" in i])
        score -= high_count * 10
        score -= medium_count * 5

        # 안전 패턴으로 가점
        score += len(safe_patterns) * 5

        # 범위 제한
        score = max(0, min(100, score))

        # 6. 상세 설명 생성
        if not issues:
            details = "Repainting 관련 위험 패턴이 발견되지 않았습니다."
            risk_level = RepaintingRisk.NONE
        else:
            details = f"{len(issues)}개의 잠재적 위험 패턴 발견. "
            if safe_patterns:
                details += f"{len(safe_patterns)}개의 안전 패턴으로 일부 완화."

        # 신뢰도 계산
        confidence = 0.9 if risk_level == RepaintingRisk.CRITICAL else 0.7

        return RepaintingAnalysis(
            risk_level=risk_level,
            score=score,
            issues=issues,
            safe_patterns=safe_patterns,
            confidence=confidence,
            details=details
        )
