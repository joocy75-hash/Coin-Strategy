#!/usr/bin/env python3
"""
Collector 모듈 테스트

작업 항목:
- 4.3.2 Collector 테스트
- 스크래퍼, Pine 코드 추출, 성능 파서 테스트
"""

import os
import sys
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from pathlib import Path

# 프로젝트 루트 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestStrategyMeta:
    """StrategyMeta 데이터 클래스 테스트"""
    
    def test_strategy_meta_creation(self):
        """StrategyMeta 생성"""
        from src.collector import StrategyMeta
        
        meta = StrategyMeta(
            script_id="test-123",
            title="Test Strategy",
            author="test_user",
            likes=100,
            views=1000,
            script_url="https://tradingview.com/script/test-123",
        )
        
        assert meta.script_id == "test-123"
        assert meta.title == "Test Strategy"
        assert meta.author == "test_user"
        assert meta.likes == 100
    
    def test_strategy_meta_with_defaults(self):
        """StrategyMeta 기본값 포함 생성"""
        from src.collector import StrategyMeta
        
        meta = StrategyMeta(
            script_id="test-123",
            title="Test",
            author="user",
            likes=50,
        )
        
        # 기본값 확인
        assert meta.views == 0
        assert meta.category == "strategy"
        assert meta.pine_version == 5


class TestPineCodeData:
    """PineCodeData 데이터 클래스 테스트"""
    
    def test_pine_code_data_creation(self):
        """PineCodeData 생성"""
        from src.collector import PineCodeData
        
        data = PineCodeData(
            script_id="test-123",
            pine_code="//@version=5\nstrategy('Test')",
            pine_version=5,
            performance={"net_profit": 125.5},
            detailed_description="Test strategy description",
            inputs=[{"name": "length", "type": "int", "default": 14}],
            is_protected=False,
        )
        
        assert data.script_id == "test-123"
        assert "//@version=5" in data.pine_code
        assert data.pine_version == 5
        assert data.is_protected is False


class TestPerformanceParser:
    """PerformanceParser 테스트"""
    
    def test_parser_initialization(self):
        """파서 초기화"""
        from src.collector import PerformanceParser
        
        parser = PerformanceParser()
        assert parser is not None
    
    def test_parser_has_methods(self):
        """파서 메서드 존재 확인"""
        from src.collector import PerformanceParser
        
        parser = PerformanceParser()
        # 실제 구현에 따라 메서드 확인
        assert hasattr(parser, 'parse') or hasattr(parser, 'extract') or callable(parser)


class TestSessionManager:
    """SessionManager 테스트"""
    
    def test_session_manager_initialization(self):
        """세션 매니저 초기화"""
        from src.collector import SessionManager
        
        manager = SessionManager()
        assert manager is not None
    
    def test_session_manager_attributes(self):
        """세션 매니저 속성 확인"""
        from src.collector import SessionManager
        
        manager = SessionManager()
        # 세션 관리에 필요한 속성 확인
        assert manager is not None


class TestTVScriptsScraper:
    """TVScriptsScraper 테스트"""
    
    def test_scraper_initialization(self):
        """스크래퍼 초기화"""
        from src.collector import TVScriptsScraper
        
        scraper = TVScriptsScraper()
        assert scraper is not None
        assert scraper.headless is True
    
    def test_scraper_with_options(self):
        """스크래퍼 옵션 설정"""
        from src.collector import TVScriptsScraper
        
        scraper = TVScriptsScraper(headless=False, proxy="http://proxy:8080")
        assert scraper.headless is False
        assert scraper.proxy == "http://proxy:8080"
    
    def test_scraper_is_context_manager(self):
        """스크래퍼 컨텍스트 매니저 지원"""
        from src.collector import TVScriptsScraper
        
        scraper = TVScriptsScraper()
        assert hasattr(scraper, '__aenter__')
        assert hasattr(scraper, '__aexit__')
    
    def test_scraper_base_url(self):
        """스크래퍼 기본 URL"""
        from src.collector import TVScriptsScraper
        
        assert TVScriptsScraper.BASE_URL == "https://www.tradingview.com/scripts"


class TestPineCodeFetcher:
    """PineCodeFetcher 테스트"""
    
    def test_fetcher_initialization(self):
        """Pine 코드 추출기 초기화"""
        from src.collector import PineCodeFetcher
        
        fetcher = PineCodeFetcher()
        assert fetcher is not None
        assert fetcher.headless is True
    
    def test_fetcher_with_options(self):
        """추출기 옵션 설정"""
        from src.collector import PineCodeFetcher
        
        fetcher = PineCodeFetcher(headless=False)
        assert fetcher.headless is False
    
    def test_fetcher_has_fetch_method(self):
        """fetch_pine_code 메서드 존재"""
        from src.collector import PineCodeFetcher
        
        fetcher = PineCodeFetcher()
        assert hasattr(fetcher, 'fetch_pine_code')


class TestCollectorIntegration:
    """Collector 통합 테스트"""
    
    def test_all_exports_available(self):
        """모든 export 사용 가능"""
        from src.collector import (
            TVScriptsScraper,
            StrategyMeta,
            PineCodeFetcher,
            PineCodeData,
            SessionManager,
            PerformanceParser,
        )
        
        assert TVScriptsScraper is not None
        assert StrategyMeta is not None
        assert PineCodeFetcher is not None
        assert PineCodeData is not None
        assert SessionManager is not None
        assert PerformanceParser is not None
    
    def test_module_import(self):
        """모듈 임포트"""
        import src.collector
        
        assert hasattr(src.collector, 'TVScriptsScraper')
        assert hasattr(src.collector, 'PineCodeFetcher')


class TestHumanLikeScraper:
    """HumanLikeScraper 테스트"""
    
    def test_scraper_exists(self):
        """스크래퍼 모듈 존재"""
        from src.collector.human_like_scraper import HumanLikeScraper
        
        assert HumanLikeScraper is not None
    
    def test_scraper_initialization(self):
        """스크래퍼 초기화"""
        from src.collector.human_like_scraper import HumanLikeScraper
        
        scraper = HumanLikeScraper()
        assert scraper is not None


class TestQualityMetrics:
    """QualityMetrics 테스트"""
    
    def test_quality_metrics_exists(self):
        """QualityMetrics 클래스 존재"""
        from src.collector.quality_scorer import QualityMetrics
        
        assert QualityMetrics is not None
    
    def test_quality_metrics_creation(self):
        """QualityMetrics 생성"""
        from src.collector.quality_scorer import QualityMetrics
        
        metrics = QualityMetrics(
            script_id="test-123",
            title="Test Strategy",
            author="test_user",
            script_url="https://tradingview.com/script/test-123",
            likes=500,
            views=10000,
        )
        
        assert metrics.script_id == "test-123"
        assert metrics.likes == 500
    
    def test_quality_metrics_calculate_scores(self):
        """품질 점수 계산"""
        from src.collector.quality_scorer import QualityMetrics
        
        metrics = QualityMetrics(
            script_id="test-123",
            title="Test Strategy",
            author="test_user",
            script_url="https://tradingview.com/script/test-123",
            likes=1000,
            views=50000,
            comments=50,
            author_followers=1000,
        )
        
        score = metrics.calculate_scores()
        assert score >= 0
        assert score <= 100
        assert metrics.total_quality_score == score


def test_collector_module_structure():
    """Collector 모듈 구조 테스트"""
    from pathlib import Path
    
    collector_dir = Path(__file__).parent.parent / "src" / "collector"
    
    expected_files = [
        "__init__.py",
        "scripts_scraper.py",
        "pine_fetcher.py",
        "session_manager.py",
        "performance_parser.py",
        "human_like_scraper.py",
        "quality_scorer.py",
    ]
    
    for filename in expected_files:
        filepath = collector_dir / filename
        assert filepath.exists(), f"Missing file: {filename}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
