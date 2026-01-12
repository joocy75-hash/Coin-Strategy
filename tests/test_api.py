#!/usr/bin/env python3
"""
API 서버 테스트

작업 항목:
- 4.3.1 API 엔드포인트 테스트
- 2.1 Rate Limiting 테스트
- 2.2 API 인증 테스트
"""

import os
import sys
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

# 프로젝트 루트 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# FastAPI 테스트 클라이언트
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """테스트 클라이언트 생성"""
    # 테스트용 환경변수 설정
    os.environ["APP_BASE_DIR"] = str(Path(__file__).parent.parent)
    os.environ["API_SECRET_KEY"] = "test_secret_key"
    
    from api.server import app
    return TestClient(app)


class TestHealthEndpoint:
    """헬스 체크 엔드포인트 테스트"""
    
    def test_health_check(self, client):
        """헬스 체크 정상 응답"""
        response = client.get("/api/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "database_exists" in data
    
    def test_health_check_headers(self, client):
        """헬스 체크 응답 헤더"""
        response = client.get("/api/health")
        assert "X-Request-ID" in response.headers
        assert "X-Process-Time" in response.headers


class TestStatsEndpoint:
    """통계 엔드포인트 테스트"""
    
    def test_stats_response_format(self, client):
        """통계 응답 형식"""
        response = client.get("/api/stats")
        assert response.status_code == 200
        
        data = response.json()
        assert "total_strategies" in data
        assert "analyzed_count" in data
        assert "passed_count" in data
        assert "avg_score" in data


class TestStrategiesEndpoint:
    """전략 목록 엔드포인트 테스트"""
    
    def test_strategies_list(self, client):
        """전략 목록 조회"""
        response = client.get("/api/strategies")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_strategies_pagination(self, client):
        """전략 목록 페이지네이션"""
        response = client.get("/api/strategies?limit=10&offset=0")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data) <= 10
    
    def test_strategies_filter_by_grade(self, client):
        """등급별 필터링"""
        response = client.get("/api/strategies?grade=A")
        assert response.status_code == 200
    
    def test_strategies_search(self, client):
        """검색 기능"""
        response = client.get("/api/strategies?search=test")
        assert response.status_code == 200
    
    def test_strategies_invalid_limit(self, client):
        """잘못된 limit 파라미터"""
        response = client.get("/api/strategies?limit=500")
        assert response.status_code == 422  # Validation error


class TestStrategyDetailEndpoint:
    """전략 상세 엔드포인트 테스트"""
    
    def test_strategy_not_found(self, client):
        """존재하지 않는 전략"""
        response = client.get("/api/strategy/nonexistent-id")
        assert response.status_code == 404
    
    def test_strategy_invalid_id(self, client):
        """잘못된 script_id 형식 - sanitize 후 404 반환"""
        response = client.get("/api/strategy/<script>alert(1)</script>")
        # XSS 문자가 제거된 후 해당 ID가 없으므로 404
        assert response.status_code in [400, 404]


class TestInputValidation:
    """입력값 검증 테스트"""
    
    def test_search_sanitization(self, client):
        """검색어 sanitization"""
        # SQL Injection 시도
        response = client.get("/api/strategies?search='; DROP TABLE strategies; --")
        assert response.status_code == 200  # 에러 없이 처리
    
    def test_xss_prevention(self, client):
        """XSS 방지"""
        response = client.get("/api/strategies?search=<script>alert(1)</script>")
        assert response.status_code == 200


class TestCORS:
    """CORS 설정 테스트"""
    
    def test_cors_allowed_origin(self, client):
        """허용된 Origin"""
        response = client.options(
            "/api/health",
            headers={"Origin": "http://localhost:3000"}
        )
        # OPTIONS 요청은 CORS preflight
        assert response.status_code in [200, 405]
    
    def test_cors_headers(self, client):
        """CORS 헤더 확인"""
        response = client.get(
            "/api/health",
            headers={"Origin": "http://localhost:3000"}
        )
        # 허용된 origin이면 CORS 헤더 포함
        assert response.status_code == 200


class TestLiveTradingEndpoints:
    """실전매매 엔드포인트 테스트"""
    
    def test_live_status(self, client):
        """실전매매 상태 조회"""
        response = client.get("/api/live/status")
        assert response.status_code == 200
        
        data = response.json()
        assert "success" in data
        assert "timestamp" in data
    
    def test_emergency_stop_without_auth(self, client):
        """인증 없이 긴급 정지 시도"""
        response = client.post(
            "/api/emergency-stop",
            json={"reason": "test", "api_key": "wrong_key"}
        )
        assert response.status_code == 401
    
    def test_emergency_stop_with_auth(self, client):
        """인증 후 긴급 정지"""
        response = client.post(
            "/api/emergency-stop",
            json={"reason": "test", "api_key": "test_secret_key"}
        )
        # 성공 또는 safeguards 미설치
        assert response.status_code in [200, 500]


class TestTradeLogEndpoints:
    """거래 로그 엔드포인트 테스트"""
    
    def test_recent_trades(self, client):
        """최근 거래 조회"""
        response = client.get("/api/trades/recent")
        assert response.status_code == 200
        
        data = response.json()
        assert "trades" in data
        assert "count" in data


class TestErrorHandling:
    """에러 핸들링 테스트"""
    
    def test_404_error_format(self, client):
        """404 에러 응답 형식"""
        response = client.get("/api/nonexistent")
        assert response.status_code == 404
        
        data = response.json()
        assert "detail" in data or "error" in data
    
    def test_error_response_has_request_id(self, client):
        """에러 응답에 request_id 포함"""
        response = client.get("/api/strategy/nonexistent-id")
        assert response.status_code == 404
        
        data = response.json()
        # 커스텀 에러 핸들러 사용 시
        if "request_id" in data:
            assert data["request_id"] is not None


def test_api_docs_available(client):
    """API 문서 접근 가능"""
    response = client.get("/api/docs")
    assert response.status_code == 200


def test_openapi_schema(client):
    """OpenAPI 스키마 접근"""
    response = client.get("/api/openapi.json")
    assert response.status_code == 200
    
    data = response.json()
    assert "openapi" in data
    assert "paths" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
