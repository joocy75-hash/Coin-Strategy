"""
StrategyGenerator 테스트

Pine Script를 Python 전략으로 변환하는 기능 검증
"""

import pytest
import sys
from pathlib import Path
import tempfile

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.converter.strategy_generator import StrategyGenerator


class TestStrategyGenerator:
    """StrategyGenerator 단위 테스트"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """테스트 설정"""
        self.generator = StrategyGenerator()

    # ============================================================
    # 기본 기능 테스트
    # ============================================================

    def test_generate_strategy_returns_dict(self, sample_pine_script_safe):
        """generate_strategy는 dict를 반환해야 함"""
        result = self.generator.generate_strategy(
            strategy_code="test_strategy",
            strategy_name="Test Strategy",
            strategy_type="basic",
            pine_code=sample_pine_script_safe,
            analysis_result={"total_score": 80, "grade": "B"}
        )
        assert isinstance(result, dict)

    def test_result_has_required_keys(self, sample_pine_script_safe):
        """결과에 필수 키가 있어야 함"""
        result = self.generator.generate_strategy(
            strategy_code="test_strategy",
            strategy_name="Test Strategy",
            strategy_type="basic",
            pine_code=sample_pine_script_safe,
            analysis_result={"total_score": 80, "grade": "B"}
        )

        assert "strategy_file" in result
        assert "loader_snippet" in result
        assert "init_snippet" in result
        assert "filename" in result
        assert "class_name" in result

    # ============================================================
    # 코드 정규화 테스트
    # ============================================================

    def test_normalize_code_lowercase(self):
        """코드는 소문자로 변환"""
        result = self.generator._normalize_code("MyStrategy")
        assert result == result.lower()

    def test_normalize_code_removes_special_chars(self):
        """특수문자 제거"""
        result = self.generator._normalize_code("My-Strategy@123!")
        assert "-" not in result
        assert "@" not in result
        assert "!" not in result

    def test_normalize_code_replaces_spaces(self):
        """공백을 언더스코어로 변환"""
        result = self.generator._normalize_code("my strategy name")
        assert " " not in result
        assert "_" in result

    def test_normalize_code_removes_consecutive_underscores(self):
        """연속 언더스코어 제거"""
        result = self.generator._normalize_code("my__strategy___name")
        assert "__" not in result

    def test_normalize_empty_returns_default(self):
        """빈 문자열은 기본값 반환"""
        result = self.generator._normalize_code("")
        assert result == "custom_strategy"

    # ============================================================
    # 클래스명 생성 테스트
    # ============================================================

    def test_generate_class_name_camel_case(self):
        """클래스명은 CamelCase"""
        result = self.generator._generate_class_name("my_test_strategy")
        assert result == "MyTestStrategyStrategy"

    def test_generate_class_name_ends_with_strategy(self):
        """클래스명은 Strategy로 끝남"""
        result = self.generator._generate_class_name("ema_cross")
        assert result.endswith("Strategy")

    def test_generate_class_name_single_word(self):
        """단일 단어도 처리"""
        result = self.generator._generate_class_name("macd")
        assert result == "MacdStrategy"

    # ============================================================
    # Pine 버전 감지 테스트
    # ============================================================

    def test_detect_pine_version_5(self):
        """Pine v5 감지"""
        code = "//@version=5\nstrategy('Test')"
        result = self.generator._detect_pine_version(code)
        assert result == 5

    def test_detect_pine_version_4(self):
        """Pine v4 감지"""
        code = "//@version=4\nstudy('Test')"
        result = self.generator._detect_pine_version(code)
        assert result == 4

    def test_detect_pine_version_default(self):
        """버전 없으면 기본값 5"""
        code = "strategy('Test')"
        result = self.generator._detect_pine_version(code)
        assert result == 5

    # ============================================================
    # 전략 파일 생성 테스트
    # ============================================================

    def test_strategy_file_is_valid_python(self, sample_pine_script_safe):
        """생성된 코드가 유효한 Python이어야 함"""
        result = self.generator.generate_strategy(
            strategy_code="test_strategy",
            strategy_name="Test Strategy",
            strategy_type="basic",
            pine_code=sample_pine_script_safe,
            analysis_result={"total_score": 80, "grade": "B"}
        )

        # 컴파일 가능해야 함
        try:
            compile(result["strategy_file"], "<string>", "exec")
            compiled = True
        except SyntaxError:
            compiled = False

        assert compiled, "Generated code should be valid Python"

    def test_strategy_file_contains_class(self, sample_pine_script_safe):
        """전략 파일에 클래스가 포함되어야 함"""
        result = self.generator.generate_strategy(
            strategy_code="ema_cross",
            strategy_name="EMA Cross",
            strategy_type="basic",
            pine_code=sample_pine_script_safe,
            analysis_result={"total_score": 80, "grade": "B"}
        )

        assert "class EmaCrossStrategy" in result["strategy_file"]

    def test_strategy_file_contains_generate_signal(self, sample_pine_script_safe):
        """전략 파일에 generate_signal 메서드가 있어야 함"""
        result = self.generator.generate_strategy(
            strategy_code="test_strategy",
            strategy_name="Test",
            strategy_type="basic",
            pine_code=sample_pine_script_safe,
            analysis_result={}
        )

        assert "def generate_signal" in result["strategy_file"]

    def test_strategy_file_contains_pine_comment(self, sample_pine_script_safe):
        """원본 Pine 코드가 주석으로 포함되어야 함"""
        result = self.generator.generate_strategy(
            strategy_code="test_strategy",
            strategy_name="Test",
            strategy_type="basic",
            pine_code=sample_pine_script_safe,
            analysis_result={}
        )

        assert "Original Pine Script" in result["strategy_file"]

    # ============================================================
    # 메타데이터 테스트
    # ============================================================

    def test_metadata_included(self, sample_pine_script_safe):
        """메타데이터가 파일에 포함되어야 함"""
        result = self.generator.generate_strategy(
            strategy_code="test_strategy",
            strategy_name="Test Strategy Name",
            strategy_type="basic",
            pine_code=sample_pine_script_safe,
            analysis_result={"total_score": 85, "grade": "A"}
        )

        assert "Test Strategy Name" in result["strategy_file"]
        assert "Strategy Research Lab" in result["strategy_file"]

    def test_analysis_summary_included(self, sample_pine_script_safe):
        """분석 요약이 포함되어야 함"""
        result = self.generator.generate_strategy(
            strategy_code="test_strategy",
            strategy_name="Test",
            strategy_type="basic",
            pine_code=sample_pine_script_safe,
            analysis_result={
                "total_score": 85,
                "grade": "A",
                "repainting_analysis": {"risk_level": "LOW"}
            }
        )

        assert "85" in result["strategy_file"] or "Total Score" in result["strategy_file"]

    # ============================================================
    # 스니펫 생성 테스트
    # ============================================================

    def test_loader_snippet_format(self, sample_pine_script_safe):
        """loader_snippet이 올바른 형식"""
        result = self.generator.generate_strategy(
            strategy_code="my_strategy",
            strategy_name="Test",
            strategy_type="basic",
            pine_code=sample_pine_script_safe,
            analysis_result={}
        )

        assert 'elif strategy_code == "my_strategy"' in result["loader_snippet"]
        assert "MyStrategyStrategy" in result["loader_snippet"]

    def test_init_snippet_format(self, sample_pine_script_safe):
        """init_snippet이 올바른 형식"""
        result = self.generator.generate_strategy(
            strategy_code="my_strategy",
            strategy_name="Test",
            strategy_type="basic",
            pine_code=sample_pine_script_safe,
            analysis_result={}
        )

        assert '"my_strategy"' in result["init_snippet"]

    # ============================================================
    # 파일명 테스트
    # ============================================================

    def test_filename_format(self, sample_pine_script_safe):
        """파일명이 올바른 형식"""
        result = self.generator.generate_strategy(
            strategy_code="ema_cross",
            strategy_name="EMA Cross",
            strategy_type="basic",
            pine_code=sample_pine_script_safe,
            analysis_result={}
        )

        assert result["filename"] == "ema_cross_strategy.py"

    def test_filename_normalized(self, sample_pine_script_safe):
        """파일명이 정규화됨"""
        result = self.generator.generate_strategy(
            strategy_code="My-Strategy@123",
            strategy_name="Test",
            strategy_type="basic",
            pine_code=sample_pine_script_safe,
            analysis_result={}
        )

        assert "-" not in result["filename"]
        assert "@" not in result["filename"]
        assert result["filename"].endswith("_strategy.py")

    # ============================================================
    # 파일 저장 테스트
    # ============================================================

    def test_save_strategy_creates_file(self, sample_pine_script_safe):
        """save_strategy가 파일을 생성해야 함"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = self.generator.save_strategy(
                output_dir=tmpdir,
                strategy_code="test_save",
                strategy_name="Test Save",
                strategy_type="basic",
                pine_code=sample_pine_script_safe,
                analysis_result={}
            )

            assert Path(output_path).exists()
            assert output_path.endswith("test_save_strategy.py")

    def test_save_strategy_content_valid(self, sample_pine_script_safe):
        """저장된 파일 내용이 유효해야 함"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = self.generator.save_strategy(
                output_dir=tmpdir,
                strategy_code="test_content",
                strategy_name="Test Content",
                strategy_type="basic",
                pine_code=sample_pine_script_safe,
                analysis_result={}
            )

            content = Path(output_path).read_text()
            assert "class TestContentStrategy" in content

    def test_save_strategy_creates_subdirs(self, sample_pine_script_safe):
        """필요한 하위 디렉토리도 생성"""
        with tempfile.TemporaryDirectory() as tmpdir:
            nested_dir = Path(tmpdir) / "sub1" / "sub2"
            output_path = self.generator.save_strategy(
                output_dir=str(nested_dir),
                strategy_code="nested_test",
                strategy_name="Nested Test",
                strategy_type="basic",
                pine_code=sample_pine_script_safe,
                analysis_result={}
            )

            assert Path(output_path).exists()
            assert nested_dir.exists()

    # ============================================================
    # LLM 변환 코드 테스트
    # ============================================================

    def test_llm_converted_code_used(self, sample_pine_script_safe):
        """llm_converted_code가 있으면 사용됨"""
        custom_logic = '''
        # Custom LLM converted logic
        return {"action": "custom", "confidence": 0.9}
        '''

        result = self.generator.generate_strategy(
            strategy_code="llm_test",
            strategy_name="LLM Test",
            strategy_type="basic",
            pine_code=sample_pine_script_safe,
            analysis_result={},
            llm_converted_code=custom_logic
        )

        assert "Custom LLM converted" in result["strategy_file"]
