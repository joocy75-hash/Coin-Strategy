"""
OverfittingDetector 테스트

Pine Script의 과적합 위험을 탐지하는 기능 검증
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.analyzer.rule_based.overfitting_detector import (
    OverfittingDetector,
    OverfittingAnalysis
)


class TestOverfittingDetector:
    """OverfittingDetector 단위 테스트"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """테스트 설정"""
        self.detector = OverfittingDetector()

    # ============================================================
    # 기본 기능 테스트
    # ============================================================

    def test_empty_code_returns_unknown(self):
        """빈 코드는 unknown 위험을 반환"""
        result = self.detector.analyze("")
        assert result.risk_level == "unknown"
        assert result.parameter_count == 0

    def test_result_type(self, sample_pine_script_simple):
        """분석 결과가 OverfittingAnalysis 타입이어야 함"""
        result = self.detector.analyze(sample_pine_script_simple)
        assert isinstance(result, OverfittingAnalysis)

    # ============================================================
    # 파라미터 수 테스트
    # ============================================================

    def test_few_parameters_low_risk(self):
        """파라미터가 적으면 low 위험"""
        code = '''
        length = input.int(14, "Length")
        src = input.source(close, "Source")
        ma = ta.sma(src, length)
        '''
        result = self.detector.analyze(code)
        assert result.risk_level in ["low", "medium"]
        assert result.parameter_count <= 5

    def test_many_parameters_high_risk(self, sample_pine_script_overfitting):
        """파라미터가 많으면 high 이상 위험"""
        result = self.detector.analyze(sample_pine_script_overfitting)
        assert result.parameter_count >= 20
        assert result.risk_level in ["high", "critical"]

    def test_parameter_count_accuracy(self):
        """파라미터 수 정확하게 카운트"""
        code = '''
        a = input.int(1, "A")
        b = input.float(2.0, "B")
        c = input.bool(true, "C")
        d = input.string("x", "D")
        e = input(5, "E")
        '''
        result = self.detector.analyze(code)
        assert result.parameter_count == 5

    def test_input_types_detected(self):
        """다양한 input 타입 탐지"""
        code = '''
        p1 = input.int(14, "Int")
        p2 = input.float(1.5, "Float")
        p3 = input.bool(true, "Bool")
        p4 = input.source(close, "Source")
        p5 = input.timeframe("D", "TF")
        p6 = input.session("0930-1600", "Session")
        '''
        result = self.detector.analyze(code)
        assert result.parameter_count >= 6

    # ============================================================
    # 매직 넘버 테스트
    # ============================================================

    def test_magic_numbers_detected(self):
        """매직 넘버 탐지"""
        code = '''
        ratio1 = 1.23456
        ratio2 = 0.786543
        threshold = 123456
        '''
        result = self.detector.analyze(code)
        assert len(result.magic_numbers) > 0

    def test_common_numbers_not_flagged(self):
        """일반적인 숫자는 매직 넘버로 플래그하지 않음"""
        code = '''
        length = 100
        period = 200
        lots = 1000
        '''
        result = self.detector.analyze(code)
        # 100, 200, 1000은 라운드 넘버로 제외
        assert "100" not in result.magic_numbers
        assert "200" not in result.magic_numbers

    def test_year_numbers_not_flagged(self):
        """년도는 매직 넘버로 플래그하지 않음"""
        code = '''
        // 2024년 데이터
        year_start = 2020
        year_end = 2025
        '''
        result = self.detector.analyze(code)
        assert "2024" not in result.magic_numbers
        assert "2020" not in result.magic_numbers

    # ============================================================
    # 하드코딩된 날짜 테스트
    # ============================================================

    def test_hardcoded_dates_detected(self, sample_pine_script_overfitting):
        """하드코딩된 날짜 탐지"""
        result = self.detector.analyze(sample_pine_script_overfitting)
        assert len(result.hardcoded_dates) > 0

    def test_timestamp_pattern_detected(self):
        """timestamp() 패턴 탐지"""
        code = '''
        start = timestamp(2020, 1, 1)
        end = timestamp(2024, 12, 31)
        '''
        result = self.detector.analyze(code)
        assert len(result.hardcoded_dates) > 0

    def test_year_month_check_detected(self):
        """year/month 체크 탐지"""
        code = '''
        if year == 2023 and month == 6
            strategy.entry("Long", strategy.long)
        '''
        result = self.detector.analyze(code)
        assert len(result.hardcoded_dates) > 0 or any("날짜" in c for c in result.concerns)

    # ============================================================
    # 성과 지표 분석 테스트
    # ============================================================

    def test_suspicious_performance_increases_risk(self, sample_pine_script_simple, mock_performance_suspicious):
        """의심스러운 성과는 위험도 증가"""
        result = self.detector.analyze(
            sample_pine_script_simple,
            performance=mock_performance_suspicious
        )
        assert any("비현실" in c or "매우 높은" in c for c in result.concerns)

    def test_good_performance_normal_risk(self, sample_pine_script_simple, mock_performance_good):
        """정상적인 성과는 추가 위험 없음"""
        result = self.detector.analyze(
            sample_pine_script_simple,
            performance=mock_performance_good
        )
        # 성과 관련 심각한 경고가 없어야 함
        perf_concerns = [c for c in result.concerns if "비현실" in c]
        assert len(perf_concerns) == 0

    def test_low_trade_param_ratio_flagged(self):
        """거래수/파라미터 비율이 낮으면 경고"""
        code = '''
        p1 = input.int(1, "P1")
        p2 = input.int(2, "P2")
        p3 = input.int(3, "P3")
        '''
        performance = {
            "total_trades": 20,  # 20거래 / 3파라미터 = 6.7 비율
            "profit_factor": 1.5,
            "win_rate": 50
        }
        result = self.detector.analyze(code, performance=performance)
        assert any("비율" in c for c in result.concerns)

    # ============================================================
    # 코드 복잡도 테스트
    # ============================================================

    def test_complex_conditions_detected(self):
        """복잡한 조건 분기 탐지"""
        # 많은 if문과 and/or
        conditions = " and ".join([f"cond{i}" for i in range(60)])
        ifs = "\n".join([f"if x{i} > 0\n    y{i} := 1" for i in range(35)])
        code = f'''
        condition = {conditions}
        {ifs}
        '''
        result = self.detector.analyze(code)
        assert any("if문" in c or "and/or" in c for c in result.concerns)

    # ============================================================
    # 위험 수준 테스트
    # ============================================================

    def test_risk_levels_valid(self, sample_pine_script_simple, sample_pine_script_overfitting):
        """위험 수준이 유효한 값"""
        valid_levels = ["low", "medium", "high", "critical", "unknown"]

        simple_result = self.detector.analyze(sample_pine_script_simple)
        overfit_result = self.detector.analyze(sample_pine_script_overfitting)

        assert simple_result.risk_level in valid_levels
        assert overfit_result.risk_level in valid_levels

    def test_overfitting_script_high_risk(self, sample_pine_script_overfitting):
        """과적합 스크립트는 high/critical 위험"""
        result = self.detector.analyze(sample_pine_script_overfitting)
        assert result.risk_level in ["high", "critical"]
        assert result.score >= 50

    # ============================================================
    # 권장사항 테스트
    # ============================================================

    def test_recommendations_provided(self, sample_pine_script_overfitting):
        """위험 시 권장사항 제공"""
        result = self.detector.analyze(sample_pine_script_overfitting)
        assert len(result.recommendations) > 0

    def test_low_risk_positive_message(self, sample_pine_script_simple):
        """낮은 위험 시 긍정적 메시지"""
        result = self.detector.analyze(sample_pine_script_simple)
        if result.risk_level == "low":
            assert any("낮습니다" in r for r in result.recommendations)

    # ============================================================
    # 점수 범위 테스트
    # ============================================================

    def test_score_range(self, sample_pine_script_simple, sample_pine_script_overfitting):
        """점수는 0-100 범위"""
        simple_result = self.detector.analyze(sample_pine_script_simple)
        overfit_result = self.detector.analyze(sample_pine_script_overfitting)

        assert 0 <= simple_result.score <= 100
        assert 0 <= overfit_result.score <= 100

    def test_high_score_high_risk(self, sample_pine_script_overfitting):
        """높은 점수는 높은 위험과 상관"""
        result = self.detector.analyze(sample_pine_script_overfitting)
        # 점수가 높을수록 위험 (이 모듈에서 score는 위험도)
        if result.score >= 70:
            assert result.risk_level == "critical"
        elif result.score >= 50:
            assert result.risk_level in ["high", "critical"]
