#!/usr/bin/env python3
"""
CORS 및 Rate Limiting 테스트 스크립트

작업 항목:
- 1.2.2 CORS 로컬 테스트
- 2.1.4 Rate Limiting 테스트
"""

import requests
import time
from typing import Dict, Any

# 서버 URL 설정
BASE_URL = "http://141.164.55.245"
LOCAL_URL = "http://localhost:8080"

# 테스트할 URL (로컬 또는 프로덕션)
TEST_URL = BASE_URL  # 프로덕션 테스트 시


def test_cors_allowed_origin():
    """허용된 Origin에서의 CORS 테스트"""
    print("\n" + "="*60)
    print("🧪 CORS 테스트 - 허용된 Origin")
    print("="*60)
    
    allowed_origins = [
        "http://141.164.55.245",
        "http://141.164.55.245:8081",
        "http://localhost:3000",
        "http://localhost:8080",
    ]
    
    for origin in allowed_origins:
        headers = {"Origin": origin}
        try:
            response = requests.options(
                f"{TEST_URL}/api/health",
                headers=headers,
                timeout=10
            )
            
            cors_header = response.headers.get("Access-Control-Allow-Origin", "없음")
            
            if cors_header == origin or cors_header == "*":
                print(f"✅ {origin}: CORS 허용됨 (응답: {cors_header})")
            else:
                print(f"⚠️  {origin}: CORS 헤더 불일치 (응답: {cors_header})")
                
        except Exception as e:
            print(f"❌ {origin}: 요청 실패 - {e}")


def test_cors_blocked_origin():
    """차단되어야 하는 Origin 테스트"""
    print("\n" + "="*60)
    print("🧪 CORS 테스트 - 차단되어야 하는 Origin")
    print("="*60)
    
    blocked_origins = [
        "http://malicious-site.com",
        "http://attacker.io",
        "http://192.168.1.100",
    ]
    
    for origin in blocked_origins:
        headers = {"Origin": origin}
        try:
            response = requests.options(
                f"{TEST_URL}/api/health",
                headers=headers,
                timeout=10
            )
            
            cors_header = response.headers.get("Access-Control-Allow-Origin", "")
            
            if cors_header == "" or cors_header != origin:
                print(f"✅ {origin}: 정상 차단됨")
            else:
                print(f"❌ {origin}: 차단되어야 하지만 허용됨! (응답: {cors_header})")
                
        except Exception as e:
            print(f"⚠️  {origin}: 요청 실패 - {e}")


def test_cors_preflight():
    """CORS Preflight (OPTIONS) 요청 테스트"""
    print("\n" + "="*60)
    print("🧪 CORS Preflight 테스트")
    print("="*60)
    
    headers = {
        "Origin": "http://141.164.55.245",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "Content-Type",
    }
    
    try:
        response = requests.options(
            f"{TEST_URL}/api/backtest",
            headers=headers,
            timeout=10
        )
        
        print(f"상태 코드: {response.status_code}")
        print(f"Allow-Origin: {response.headers.get('Access-Control-Allow-Origin', '없음')}")
        print(f"Allow-Methods: {response.headers.get('Access-Control-Allow-Methods', '없음')}")
        print(f"Allow-Headers: {response.headers.get('Access-Control-Allow-Headers', '없음')}")
        
        if response.status_code in [200, 204]:
            print("✅ Preflight 요청 성공")
        else:
            print(f"⚠️  Preflight 응답 코드: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Preflight 요청 실패: {e}")


def test_rate_limiting():
    """Rate Limiting 테스트"""
    print("\n" + "="*60)
    print("🧪 Rate Limiting 테스트")
    print("="*60)
    
    endpoints = [
        ("/api/health", 60, "60/minute"),
        ("/api/stats", 30, "30/minute"),
        ("/api/strategies", 30, "30/minute"),
    ]
    
    for endpoint, limit, limit_str in endpoints:
        print(f"\n📍 {endpoint} (제한: {limit_str})")
        
        success_count = 0
        rate_limited = False
        
        # 빠르게 여러 요청 보내기
        for i in range(min(limit + 5, 35)):  # 최대 35회 테스트
            try:
                response = requests.get(f"{TEST_URL}{endpoint}", timeout=5)
                
                if response.status_code == 200:
                    success_count += 1
                elif response.status_code == 429:
                    rate_limited = True
                    print(f"   ⚡ {i+1}번째 요청에서 Rate Limit 도달 (429)")
                    break
                else:
                    print(f"   ⚠️  예상치 못한 응답: {response.status_code}")
                    
            except Exception as e:
                print(f"   ❌ 요청 실패: {e}")
                break
        
        if rate_limited:
            print(f"   ✅ Rate Limiting 정상 작동 ({success_count}회 성공 후 차단)")
        else:
            print(f"   ⚠️  {success_count}회 요청 모두 성공 (Rate Limit 미도달)")


def test_rate_limit_recovery():
    """Rate Limit 해제 테스트"""
    print("\n" + "="*60)
    print("🧪 Rate Limit 해제 테스트")
    print("="*60)
    
    # 먼저 rate limit에 도달
    print("1. Rate Limit 도달 시도...")
    for i in range(35):
        try:
            response = requests.get(f"{TEST_URL}/api/stats", timeout=5)
            if response.status_code == 429:
                print(f"   Rate Limit 도달 ({i+1}회)")
                break
        except:
            pass
    
    # 잠시 대기 후 재시도
    print("2. 10초 대기 후 재시도...")
    time.sleep(10)
    
    try:
        response = requests.get(f"{TEST_URL}/api/stats", timeout=5)
        if response.status_code == 200:
            print("   ✅ Rate Limit 해제됨 - 요청 성공")
        elif response.status_code == 429:
            print("   ⚠️  아직 Rate Limit 상태 (더 긴 대기 필요)")
        else:
            print(f"   ⚠️  응답 코드: {response.status_code}")
    except Exception as e:
        print(f"   ❌ 요청 실패: {e}")


def test_api_endpoints():
    """기본 API 엔드포인트 테스트"""
    print("\n" + "="*60)
    print("🧪 API 엔드포인트 기본 테스트")
    print("="*60)
    
    endpoints = [
        ("GET", "/api/health", None),
        ("GET", "/api/stats", None),
        ("GET", "/api/strategies?limit=5", None),
        ("GET", "/api/backtest-charts", None),
    ]
    
    for method, endpoint, data in endpoints:
        try:
            if method == "GET":
                response = requests.get(f"{TEST_URL}{endpoint}", timeout=10)
            else:
                response = requests.post(f"{TEST_URL}{endpoint}", json=data, timeout=10)
            
            status = "✅" if response.status_code == 200 else "⚠️"
            print(f"{status} {method} {endpoint}: {response.status_code}")
            
        except Exception as e:
            print(f"❌ {method} {endpoint}: {e}")


def main():
    """메인 테스트 실행"""
    print("\n" + "="*60)
    print("🚀 CORS & Rate Limiting 테스트 시작")
    print(f"   대상 서버: {TEST_URL}")
    print("="*60)
    
    # 1. 기본 API 테스트
    test_api_endpoints()
    
    # 2. CORS 테스트
    test_cors_allowed_origin()
    test_cors_blocked_origin()
    test_cors_preflight()
    
    # 3. Rate Limiting 테스트
    test_rate_limiting()
    
    # 4. Rate Limit 해제 테스트 (선택)
    # test_rate_limit_recovery()
    
    print("\n" + "="*60)
    print("✅ 테스트 완료")
    print("="*60)


if __name__ == "__main__":
    main()
