"""
StrategyScorer 테스트

전략 종합 점수 산출 기능 검증
"""

import pytest
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.analyzer.scorer import StrategyScorer, FinalScore


class TestStrategyScorer:
    """StrategyScorer 단위 테스트"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """테스트 설정 - LLM 없이 초기화"""
        self.scorer = StrategyScorer(llm_api_key=None)

    # ============================================================
    # 기본 기능 테스트
    # ============================================================

    @pytest.mark.asyncio
    async def test_score_strategy_returns_final_score(self, sample_pine_script_safe):
        """score_strategy는 FinalScore를 반환해야 함"""
        result = await self.scorer.score_strategy(
            pine_code=sample_pine_script_safe,
            skip_llm=True
        )
        assert isinstance(result, FinalScore)

    @pytest.mark.asyncio
    async def test_final_score_has_all_fields(self, sample_pine_script_safe):
        """FinalScore는 모든 필수 필드를 가져야 함"""
        result = await self.scorer.score_strategy(
            pine_code=sample_pine_script_safe,
            skip_llm=True
        )

        assert hasattr(result, 'total_score')
        assert hasattr(result, 'grade')
        assert hasattr(result, 'status')
        assert hasattr(result, 'repainting_score')
        assert hasattr(result, 'overfitting_score')
        assert hasattr(result, 'risk_score')
        assert hasattr(result, 'repainting_analysis')
        assert hasattr(result, 'overfitting_analysis')
        assert hasattr(result, 'risk_analysis')
        assert hasattr(result, 'analyzed_at')

    # ============================================================
    # 점수 범위 테스트
    # ============================================================

    @pytest.mark.asyncio
    async def test_score_range(self, sample_pine_script_safe, sample_pine_script_repainting):
        """점수는 0-100 범위여야 함"""
        safe_result = await self.scorer.score_strategy(
            pine_code=sample_pine_script_safe,
            skip_llm=True
        )
        risky_result = await self.scorer.score_strategy(
            pine_code=sample_pine_script_repainting,
            skip_llm=True
        )

        assert 0 <= safe_result.total_score <= 100
        assert 0 <= risky_result.total_score <= 100

    @pytest.mark.asyncio
    async def test_component_scores_range(self, sample_pine_script_safe):
        """세부 점수도 0-100 범위여야 함"""
        result = await self.scorer.score_strategy(
            pine_code=sample_pine_script_safe,
            skip_llm=True
        )

        assert 0 <= result.repainting_score <= 100
        assert 0 <= result.overfitting_score <= 100
        assert 0 <= result.risk_score <= 100

    # ============================================================
    # 등급 테스트
    # ============================================================

    @pytest.mark.asyncio
    async def test_grade_valid(self, sample_pine_script_safe):
        """등급은 A, B, C, D, F 중 하나"""
        result = await self.scorer.score_strategy(
            pine_code=sample_pine_script_safe,
            skip_llm=True
        )
        assert result.grade in ["A", "B", "C", "D", "F"]

    @pytest.mark.asyncio
    async def test_grade_threshold_a(self):
        """85점 이상은 A등급"""
        # 안전하고 리스크 관리 있는 코드
        code = '''
        //@version=5
        strategy("Test", overlay=true)
        if barstate.isconfirmed
            if close[1] > ta.sma(close[1], 20)
                strategy.entry("Long", strategy.long)
                strategy.exit("Exit", "Long", stop=close*0.98, limit=close*1.04)
        '''
        result = await self.scorer.score_strategy(pine_code=code, skip_llm=True)
        # 점수에 따라 등급 확인
        if result.total_score >= 85:
            assert result.grade == "A"

    @pytest.mark.asyncio
    async def test_critical_repainting_is_f_grade(self, sample_pine_script_repainting):
        """CRITICAL 리페인팅은 F등급"""
        result = await self.scorer.score_strategy(
            pine_code=sample_pine_script_repainting,
            skip_llm=True
        )
        assert result.grade == "F"
        assert result.status == "rejected"

    # ============================================================
    # 상태 테스트
    # ============================================================

    @pytest.mark.asyncio
    async def test_status_valid(self, sample_pine_script_safe):
        """상태는 passed, review, rejected 중 하나"""
        result = await self.scorer.score_strategy(
            pine_code=sample_pine_script_safe,
            skip_llm=True
        )
        assert result.status in ["passed", "review", "rejected"]

    @pytest.mark.asyncio
    async def test_status_rejected_for_critical(self, sample_pine_script_repainting):
        """CRITICAL 위험은 rejected 상태"""
        result = await self.scorer.score_strategy(
            pine_code=sample_pine_script_repainting,
            skip_llm=True
        )
        assert result.status == "rejected"

    # ============================================================
    # 리페인팅 분석 테스트
    # ============================================================

    @pytest.mark.asyncio
    async def test_repainting_analysis_included(self, sample_pine_script_safe):
        """리페인팅 분석 결과가 포함되어야 함"""
        result = await self.scorer.score_strategy(
            pine_code=sample_pine_script_safe,
            skip_llm=True
        )
        assert 'risk_level' in result.repainting_analysis
        assert 'issues' in result.repainting_analysis

    @pytest.mark.asyncio
    async def test_critical_repainting_immediate_reject(self, sample_pine_script_repainting):
        """CRITICAL 리페인팅은 즉시 거부"""
        result = await self.scorer.score_strategy(
            pine_code=sample_pine_script_repainting,
            skip_llm=True
        )
        assert result.total_score == 0
        assert result.repainting_analysis['risk_level'] == 'CRITICAL'

    # ============================================================
    # 과적합 분석 테스트
    # ============================================================

    @pytest.mark.asyncio
    async def test_overfitting_analysis_included(self, sample_pine_script_safe):
        """과적합 분석 결과가 포함되어야 함"""
        result = await self.scorer.score_strategy(
            pine_code=sample_pine_script_safe,
            skip_llm=True
        )
        # CRITICAL 리페인팅이 아니면 overfitting_analysis가 있어야 함
        if result.repainting_analysis.get('risk_level') != 'CRITICAL':
            assert 'risk_level' in result.overfitting_analysis

    @pytest.mark.asyncio
    async def test_overfitting_score_inversion(self, sample_pine_script_overfitting):
        """과적합 점수는 반전됨 (높은 위험 = 낮은 점수)"""
        # CRITICAL 리페인팅이 없는 과적합 코드
        code = '''
        //@version=5
        strategy("Overfit", overlay=true)
        len1 = input.int(14, "L1")
        len2 = input.int(21, "L2")
        len3 = input.int(7, "L3")
        len4 = input.int(28, "L4")
        len5 = input.int(50, "L5")
        len6 = input.int(100, "L6")
        len7 = input.int(200, "L7")
        len8 = input.int(14, "L8")
        len9 = input.int(21, "L9")
        len10 = input.int(7, "L10")
        len11 = input.int(28, "L11")
        len12 = input.int(50, "L12")
        len13 = input.int(100, "L13")
        len14 = input.int(200, "L14")
        len15 = input.int(14, "L15")
        len16 = input.int(21, "L16")
        len17 = input.int(7, "L17")
        len18 = input.int(28, "L18")
        len19 = input.int(50, "L19")
        len20 = input.int(100, "L20")
        len21 = input.int(200, "L21")
        if barstate.isconfirmed
            strategy.entry("Long", strategy.long)
        '''
        result = await self.scorer.score_strategy(pine_code=code, skip_llm=True)
        # 많은 파라미터 → 낮은 overfitting_score
        assert result.overfitting_score < 70

    # ============================================================
    # 리스크 분석 테스트
    # ============================================================

    @pytest.mark.asyncio
    async def test_risk_analysis_included(self, sample_pine_script_safe):
        """리스크 분석 결과가 포함되어야 함"""
        result = await self.scorer.score_strategy(
            pine_code=sample_pine_script_safe,
            skip_llm=True
        )
        if result.repainting_analysis.get('risk_level') != 'CRITICAL':
            assert 'has_stop_loss' in result.risk_analysis
            assert 'has_take_profit' in result.risk_analysis

    @pytest.mark.asyncio
    async def test_good_risk_management_score(self, sample_pine_script_good_risk):
        """좋은 리스크 관리는 높은 점수"""
        result = await self.scorer.score_strategy(
            pine_code=sample_pine_script_good_risk,
            skip_llm=True
        )
        if result.repainting_analysis.get('risk_level') != 'CRITICAL':
            assert result.risk_score >= 50

    # ============================================================
    # LLM 스킵 테스트
    # ============================================================

    @pytest.mark.asyncio
    async def test_skip_llm_flag(self, sample_pine_script_safe):
        """skip_llm=True면 LLM 분석 없이 진행"""
        result = await self.scorer.score_strategy(
            pine_code=sample_pine_script_safe,
            skip_llm=True
        )
        # LLM 분석 없이도 결과가 있어야 함
        assert result.total_score > 0 or result.status == "rejected"

    @pytest.mark.asyncio
    async def test_llm_score_default_without_api(self, sample_pine_script_safe):
        """API 키 없으면 LLM 점수는 기본값(50)"""
        result = await self.scorer.score_strategy(
            pine_code=sample_pine_script_safe,
            skip_llm=True
        )
        if result.status != "rejected":
            assert result.llm_score == 50  # 기본값

    # ============================================================
    # 메타데이터 테스트
    # ============================================================

    @pytest.mark.asyncio
    async def test_analyzed_at_timestamp(self, sample_pine_script_safe):
        """analyzed_at은 datetime 타입"""
        result = await self.scorer.score_strategy(
            pine_code=sample_pine_script_safe,
            skip_llm=True
        )
        assert isinstance(result.analyzed_at, datetime)

    @pytest.mark.asyncio
    async def test_analysis_version_present(self, sample_pine_script_safe):
        """분석 버전이 존재해야 함"""
        result = await self.scorer.score_strategy(
            pine_code=sample_pine_script_safe,
            skip_llm=True
        )
        assert hasattr(result, 'analysis_version')
        assert result.analysis_version is not None
