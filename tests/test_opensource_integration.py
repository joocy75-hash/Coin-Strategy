#!/usr/bin/env python3
"""
7단계 오픈소스 통합 테스트

- 7.1 pynescript (Pine Script 파서)
- 7.2 VectorBT (고속 백테스팅)
- 7.3 FinBERT (금융 감성 분석)
"""

import pytest
import sys
from pathlib import Path

# 프로젝트 루트 추가
sys.path.insert(0, str(Path(__file__).parent.parent))


# ============================================================
# 7.1 Pine Script Parser Tests
# ============================================================

class TestPineParser:
    """Pine Script 파서 테스트"""
    
    def test_import(self):
        """모듈 임포트 테스트"""
        from src.analyzer.pine_parser import (
            PineScriptAnalyzer,
            analyze_pine_script,
            get_pine_analyzer,
            RiskLevel,
        )
        assert PineScriptAnalyzer is not None
        assert analyze_pine_script is not None
    
    def test_analyzer_creation(self):
        """분석기 생성 테스트"""
        from src.analyzer.pine_parser import PineScriptAnalyzer
        analyzer = PineScriptAnalyzer()
        assert analyzer is not None
    
    def test_singleton(self):
        """싱글톤 테스트"""
        from src.analyzer.pine_parser import get_pine_analyzer
        a1 = get_pine_analyzer()
        a2 = get_pine_analyzer()
        assert a1 is a2
    
    def test_empty_code(self):
        """빈 코드 분석 테스트"""
        from src.analyzer.pine_parser import analyze_pine_script
        result = analyze_pine_script("")
        assert result["success"] is False
        assert "error" in result
    
    def test_version_detection(self):
        """Pine 버전 감지 테스트"""
        from src.analyzer.pine_parser import PineScriptAnalyzer
        analyzer = PineScriptAnalyzer()
        
        v5_code = "//@version=5\nstrategy('test')"
        result = analyzer.analyze(v5_code)
        assert result.pine_version == 5
        
        v4_code = "//@version=4\nstrategy('test')"
        result = analyzer.analyze(v4_code)
        assert result.pine_version == 4
    
    def test_repainting_detection(self):
        """리페인팅 탐지 테스트"""
        from src.analyzer.pine_parser import analyze_pine_script
        
        # 리페인팅 위험 코드
        risky_code = """
        //@version=5
        data = request.security(syminfo.tickerid, "D", close, lookahead=barmerge.lookahead_on)
        """
        result = analyze_pine_script(risky_code)
        assert result["success"] is True
        assert result["repainting"]["risk"] in ["critical", "high"]
        assert len(result["repainting"]["issues"]) > 0
    
    def test_safe_code(self):
        """안전한 코드 분석 테스트"""
        from src.analyzer.pine_parser import analyze_pine_script
        
        safe_code = """
        //@version=5
        strategy("Safe Strategy", overlay=true)
        sma20 = ta.sma(close, 20)
        if ta.crossover(close, sma20)
            strategy.entry("Long", strategy.long)
        """
        result = analyze_pine_script(safe_code)
        assert result["success"] is True
        assert result["repainting"]["score"] >= 80
    
    def test_overfitting_detection(self):
        """오버피팅 탐지 테스트"""
        from src.analyzer.pine_parser import analyze_pine_script
        
        # 오버피팅 위험 코드 (하드코딩된 날짜)
        risky_code = """
        //@version=5
        startDate = timestamp(2020, 1, 15)
        if time > startDate
            strategy.entry("Long", strategy.long)
        """
        result = analyze_pine_script(risky_code)
        assert result["success"] is True
        assert len(result["overfitting"]["issues"]) > 0
    
    def test_result_structure(self):
        """결과 구조 테스트"""
        from src.analyzer.pine_parser import analyze_pine_script
        
        code = "//@version=5\nstrategy('test')"
        result = analyze_pine_script(code)
        
        assert "success" in result
        assert "pine_version" in result
        assert "repainting" in result
        assert "overfitting" in result
        assert "metrics" in result
        
        assert "risk" in result["repainting"]
        assert "score" in result["repainting"]
        assert "issues" in result["repainting"]


# ============================================================
# 7.2 VectorBT Tests
# ============================================================

class TestVectorBTEngine:
    """VectorBT 백테스팅 엔진 테스트"""
    
    def test_import(self):
        """모듈 임포트 테스트"""
        from src.backtester.vectorbt_engine import (
            VectorBTEngine,
            BacktestConfig,
            BacktestResult,
            quick_backtest,
            VECTORBT_AVAILABLE,
        )
        assert VectorBTEngine is not None
        assert BacktestConfig is not None
    
    def test_config_creation(self):
        """설정 생성 테스트"""
        from src.backtester.vectorbt_engine import BacktestConfig
        
        config = BacktestConfig()
        assert config.initial_capital == 10000.0
        assert config.commission == 0.001
        
        custom_config = BacktestConfig(
            initial_capital=50000,
            commission=0.0005,
        )
        assert custom_config.initial_capital == 50000
    
    def test_engine_creation(self):
        """엔진 생성 테스트"""
        from src.backtester.vectorbt_engine import VectorBTEngine, BacktestConfig
        
        engine = VectorBTEngine()
        assert engine is not None
        assert engine.config is not None
        
        config = BacktestConfig(initial_capital=20000)
        engine = VectorBTEngine(config)
        assert engine.config.initial_capital == 20000
    
    def test_result_structure(self):
        """결과 구조 테스트"""
        from src.backtester.vectorbt_engine import BacktestResult
        
        result = BacktestResult(success=True)
        result_dict = result.to_dict()
        
        assert "success" in result_dict
        assert "returns" in result_dict
        assert "risk" in result_dict
        assert "trades" in result_dict
        assert "period" in result_dict
    
    def test_builtin_strategies(self):
        """내장 전략 함수 테스트"""
        from src.backtester.vectorbt_engine import (
            sma_crossover_strategy,
            rsi_strategy,
            bollinger_bands_strategy,
        )
        import pandas as pd
        import numpy as np
        
        # 테스트 데이터
        dates = pd.date_range('2023-01-01', periods=100, freq='1h')
        data = pd.DataFrame({
            'open': np.random.randn(100).cumsum() + 100,
            'high': np.random.randn(100).cumsum() + 101,
            'low': np.random.randn(100).cumsum() + 99,
            'close': np.random.randn(100).cumsum() + 100,
            'volume': np.random.randint(1000, 10000, 100),
        }, index=dates)
        
        # SMA 크로스오버
        entries, exits = sma_crossover_strategy(data, {"fast_period": 5, "slow_period": 20})
        assert len(entries) == len(data)
        assert entries.dtype == bool
        
        # RSI
        entries, exits = rsi_strategy(data, {"period": 14, "oversold": 30, "overbought": 70})
        assert len(entries) == len(data)
        
        # 볼린저 밴드
        entries, exits = bollinger_bands_strategy(data, {"period": 20, "std_dev": 2.0})
        assert len(entries) == len(data)
    
    @pytest.mark.skipif(
        not __import__('src.backtester.vectorbt_engine', fromlist=['VECTORBT_AVAILABLE']).VECTORBT_AVAILABLE,
        reason="VectorBT not installed"
    )
    def test_quick_backtest(self):
        """빠른 백테스트 테스트 (VectorBT 필요)"""
        from src.backtester.vectorbt_engine import quick_backtest
        import pandas as pd
        import numpy as np
        
        dates = pd.date_range('2023-01-01', periods=500, freq='1h')
        data = pd.DataFrame({
            'open': np.random.randn(500).cumsum() + 100,
            'high': np.random.randn(500).cumsum() + 101,
            'low': np.random.randn(500).cumsum() + 99,
            'close': np.random.randn(500).cumsum() + 100,
            'volume': np.random.randint(1000, 10000, 500),
        }, index=dates)
        
        result = quick_backtest(data, "sma_crossover", {"fast_period": 10, "slow_period": 30})
        assert result["success"] is True
        assert "returns" in result


# ============================================================
# 7.3 FinBERT Tests
# ============================================================

class TestSentimentAnalyzer:
    """FinBERT 감성 분석기 테스트"""
    
    def test_import(self):
        """모듈 임포트 테스트"""
        from src.analyzer.sentiment_analyzer import (
            FinBERTAnalyzer,
            RuleBasedHypeAnalyzer,
            analyze_strategy_description,
            quick_hype_check,
            SentimentLabel,
            HypeAnalysisResult,
        )
        assert FinBERTAnalyzer is not None
        assert RuleBasedHypeAnalyzer is not None
    
    def test_rule_based_analyzer(self):
        """규칙 기반 분석기 테스트"""
        from src.analyzer.sentiment_analyzer import RuleBasedHypeAnalyzer
        
        analyzer = RuleBasedHypeAnalyzer()
        
        # 과대광고 텍스트
        hype_text = "GUARANTEED 100% WIN RATE! Never lose money!"
        result = analyzer.analyze(hype_text)
        
        assert result.success is True
        assert result.hype_score > 50
        assert len(result.hype_phrases) > 0
    
    def test_quick_hype_check(self):
        """빠른 과대광고 체크 테스트"""
        from src.analyzer.sentiment_analyzer import quick_hype_check
        
        # 과대광고
        result = quick_hype_check("This is the BEST strategy! 100% guaranteed profit!")
        assert result["success"] is True
        assert result["hype_score"] > 30
        
        # 객관적 설명
        result = quick_hype_check("Simple moving average crossover strategy with 55% win rate.")
        assert result["success"] is True
        assert result["hype_score"] < 30
    
    def test_korean_hype_detection(self):
        """한국어 과대광고 탐지 테스트"""
        from src.analyzer.sentiment_analyzer import quick_hype_check
        
        result = quick_hype_check("100% 수익 보장! 최고의 전략입니다!")
        assert result["success"] is True
        assert result["hype_score"] > 30
        assert len(result["analysis"]["hype_phrases"]) > 0
    
    def test_empty_text(self):
        """빈 텍스트 테스트"""
        from src.analyzer.sentiment_analyzer import quick_hype_check
        
        result = quick_hype_check("")
        assert result["success"] is False
    
    def test_result_structure(self):
        """결과 구조 테스트"""
        from src.analyzer.sentiment_analyzer import quick_hype_check
        
        result = quick_hype_check("Test strategy description")
        
        assert "success" in result
        assert "hype_score" in result
        assert "hype_level" in result
        assert "analysis" in result
        assert "recommendations" in result
    
    def test_hype_levels(self):
        """과대광고 수준 테스트"""
        from src.analyzer.sentiment_analyzer import RuleBasedHypeAnalyzer
        
        analyzer = RuleBasedHypeAnalyzer()
        
        # 낮은 수준
        result = analyzer.analyze("Simple strategy using SMA crossover.")
        assert result.hype_level == "low"
        
        # 높은 수준
        result = analyzer.analyze(
            "GUARANTEED 100% WIN RATE! Never lose! Best ever! "
            "Secret strategy! Limited time! Act now!"
        )
        assert result.hype_level in ["high", "extreme"]
    
    def test_finbert_analyzer_creation(self):
        """FinBERT 분석기 생성 테스트"""
        from src.analyzer.sentiment_analyzer import FinBERTAnalyzer
        
        analyzer = FinBERTAnalyzer()
        assert analyzer is not None
        assert analyzer._model_loaded is False  # 지연 로딩
    
    def test_singleton(self):
        """싱글톤 테스트"""
        from src.analyzer.sentiment_analyzer import get_sentiment_analyzer
        
        a1 = get_sentiment_analyzer()
        a2 = get_sentiment_analyzer()
        assert a1 is a2


# ============================================================
# Integration Tests
# ============================================================

class TestOpenSourceIntegration:
    """오픈소스 통합 테스트"""
    
    def test_all_modules_importable(self):
        """모든 모듈 임포트 가능 테스트"""
        # Pine Parser
        from src.analyzer.pine_parser import analyze_pine_script
        
        # VectorBT Engine
        from src.backtester.vectorbt_engine import quick_backtest
        
        # Sentiment Analyzer
        from src.analyzer.sentiment_analyzer import quick_hype_check
        
        assert analyze_pine_script is not None
        assert quick_backtest is not None
        assert quick_hype_check is not None
    
    def test_combined_analysis(self):
        """통합 분석 테스트"""
        from src.analyzer.pine_parser import analyze_pine_script
        from src.analyzer.sentiment_analyzer import quick_hype_check
        
        # Pine 코드 분석
        pine_code = """
        //@version=5
        strategy("Test", overlay=true)
        if ta.crossover(ta.sma(close, 10), ta.sma(close, 20))
            strategy.entry("Long", strategy.long)
        """
        pine_result = analyze_pine_script(pine_code)
        
        # 설명문 분석
        description = "Simple SMA crossover strategy with 55% win rate."
        hype_result = quick_hype_check(description)
        
        # 결합된 점수 계산
        combined_score = (
            pine_result["repainting"]["score"] * 0.4 +
            pine_result["overfitting"]["score"] * 0.3 +
            (100 - hype_result["hype_score"]) * 0.3
        )
        
        assert combined_score > 0
        assert combined_score <= 100


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
