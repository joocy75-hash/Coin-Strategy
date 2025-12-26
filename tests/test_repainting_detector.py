"""
RepaintingDetector 테스트

Pine Script의 리페인팅 위험을 탐지하는 기능 검증
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.analyzer.rule_based.repainting_detector import (
    RepaintingDetector,
    RepaintingRisk,
    RepaintingAnalysis
)


class TestRepaintingDetector:
    """RepaintingDetector 단위 테스트"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """테스트 설정"""
        self.detector = RepaintingDetector()

    # ============================================================
    # 기본 기능 테스트
    # ============================================================

    def test_empty_code_returns_none_risk(self):
        """빈 코드는 NONE 위험을 반환해야 함"""
        result = self.detector.analyze("")
        assert result.risk_level == RepaintingRisk.NONE
        assert result.score == 0

    def test_short_code_returns_none_risk(self):
        """너무 짧은 코드는 NONE 위험을 반환"""
        result = self.detector.analyze("plot()")
        assert result.risk_level == RepaintingRisk.NONE

    def test_result_type(self, sample_pine_script_safe):
        """분석 결과가 RepaintingAnalysis 타입이어야 함"""
        result = self.detector.analyze(sample_pine_script_safe)
        assert isinstance(result, RepaintingAnalysis)

    # ============================================================
    # 치명적 패턴 테스트
    # ============================================================

    def test_lookahead_on_critical(self):
        """lookahead_on은 CRITICAL 위험"""
        code = '''
        higher = request.security(syminfo.tickerid, "D", close, lookahead=barmerge.lookahead_on)
        '''
        result = self.detector.analyze(code)
        assert result.risk_level == RepaintingRisk.CRITICAL
        assert result.score == 0
        assert any("lookahead" in issue.lower() for issue in result.issues)

    def test_legacy_security_lookahead(self):
        """레거시 security() 함수의 lookahead_on도 탐지"""
        code = '''
        higher = security(syminfo.tickerid, "D", close, lookahead=barmerge.lookahead_on)
        '''
        result = self.detector.analyze(code)
        assert result.risk_level == RepaintingRisk.CRITICAL

    # ============================================================
    # 고위험 패턴 테스트
    # ============================================================

    def test_barstate_isrealtime_high_risk(self):
        """barstate.isrealtime은 HIGH 위험"""
        code = '''
        if barstate.isrealtime == true
            alert("Real-time alert")
        '''
        result = self.detector.analyze(code)
        assert result.risk_level.value >= RepaintingRisk.HIGH.value
        assert any("실시간" in issue or "isrealtime" in issue.lower() for issue in result.issues)

    def test_barstate_isconfirmed_false_high_risk(self):
        """barstate.isconfirmed == false는 HIGH 위험"""
        code = '''
        if barstate.isconfirmed == false
            signal := true
        '''
        result = self.detector.analyze(code)
        assert result.risk_level.value >= RepaintingRisk.HIGH.value

    # ============================================================
    # 중간 위험 패턴 테스트
    # ============================================================

    def test_varip_medium_risk(self):
        """varip 변수는 MEDIUM 이상 위험"""
        code = '''
        varip float lastClose = 0
        lastClose := close
        '''
        result = self.detector.analyze(code)
        assert result.risk_level.value >= RepaintingRisk.MEDIUM.value
        assert any("varip" in issue.lower() for issue in result.issues)

    def test_timenow_medium_risk(self):
        """timenow는 MEDIUM 이상 위험"""
        code = '''
        currentTime = timenow
        if timenow > time + 3600000
            signal := true
        '''
        result = self.detector.analyze(code)
        assert result.risk_level.value >= RepaintingRisk.MEDIUM.value

    def test_security_without_lookahead(self):
        """lookahead 미명시 security는 MEDIUM 위험"""
        code = '''
        htf_close = request.security(syminfo.tickerid, "D", close)
        '''
        result = self.detector.analyze(code)
        assert result.risk_level.value >= RepaintingRisk.MEDIUM.value

    # ============================================================
    # 안전 패턴 테스트
    # ============================================================

    def test_safe_script_low_risk(self, sample_pine_script_safe):
        """안전한 스크립트는 낮은 위험"""
        result = self.detector.analyze(sample_pine_script_safe)
        # 안전 패턴이 있으면 감점 완화
        assert result.risk_level.value <= RepaintingRisk.LOW.value or len(result.safe_patterns) > 0

    def test_barstate_isconfirmed_true_safe(self):
        """barstate.isconfirmed == true는 안전 패턴"""
        code = '''
        if barstate.isconfirmed == true
            signal := close[1] > sma
        '''
        result = self.detector.analyze(code)
        assert any("봉 완성 확인" in p for p in result.safe_patterns)

    def test_previous_bar_reference_safe(self):
        """[1] 참조는 안전 패턴"""
        code = '''
        prevClose = close[1]
        prevHigh = high[1]
        signal = prevClose > ta.sma(close[1], 20)
        '''
        result = self.detector.analyze(code)
        assert any("[1]" in p or "이전 봉" in p for p in result.safe_patterns)

    def test_lookahead_off_safe(self):
        """lookahead_off는 안전 패턴"""
        code = '''
        htf = request.security(syminfo.tickerid, "D", close, lookahead=barmerge.lookahead_off)
        '''
        result = self.detector.analyze(code)
        assert any("lookahead" in p.lower() for p in result.safe_patterns)
        # lookahead_off 명시는 CRITICAL이 아님
        assert result.risk_level != RepaintingRisk.CRITICAL

    # ============================================================
    # 점수 계산 테스트
    # ============================================================

    def test_score_range(self, sample_pine_script_safe, sample_pine_script_repainting):
        """점수는 0-100 범위여야 함"""
        safe_result = self.detector.analyze(sample_pine_script_safe)
        risky_result = self.detector.analyze(sample_pine_script_repainting)

        assert 0 <= safe_result.score <= 100
        assert 0 <= risky_result.score <= 100

    def test_critical_score_is_zero(self):
        """CRITICAL 위험은 점수 0"""
        code = '''
        data = request.security(syminfo.tickerid, "D", close, lookahead=barmerge.lookahead_on)
        '''
        result = self.detector.analyze(code)
        assert result.score == 0

    def test_safe_patterns_increase_score(self):
        """안전 패턴은 점수를 높임"""
        risky_code = '''
        varip float x = 0
        '''
        safe_code = '''
        varip float x = 0
        if barstate.isconfirmed == true
            y = close[1]
        '''
        risky_result = self.detector.analyze(risky_code)
        safe_result = self.detector.analyze(safe_code)

        # 안전 패턴이 있으면 점수가 더 높아야 함
        assert safe_result.score >= risky_result.score

    # ============================================================
    # 통합 테스트
    # ============================================================

    def test_repainting_script_detected(self, sample_pine_script_repainting):
        """리페인팅 스크립트는 HIGH 이상으로 탐지되어야 함"""
        result = self.detector.analyze(sample_pine_script_repainting)
        # lookahead_on이 있으므로 CRITICAL
        assert result.risk_level == RepaintingRisk.CRITICAL
        assert len(result.issues) > 0

    def test_confidence_level(self, sample_pine_script_repainting):
        """신뢰도는 0-1 범위"""
        result = self.detector.analyze(sample_pine_script_repainting)
        assert 0 <= result.confidence <= 1

    def test_details_not_empty(self, sample_pine_script_safe):
        """details 필드는 비어있지 않아야 함"""
        result = self.detector.analyze(sample_pine_script_safe)
        assert result.details
        assert len(result.details) > 0
