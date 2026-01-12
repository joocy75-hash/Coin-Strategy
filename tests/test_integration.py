#!/usr/bin/env python3
"""
통합 테스트 스크립트

작업 항목:
- SecureAPIManager 통합 테스트
- LiveTradingSafeguards 통합 테스트
- 긴급 정지 API 테스트
"""

import os
import sys
import json
import requests

# 프로젝트 루트 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE_URL = "http://141.164.55.245"


def test_secure_api_manager():
    """SecureAPIManager 테스트"""
    print("\n" + "="*60)
    print("🧪 SecureAPIManager 테스트")
    print("="*60)
    
    try:
        from encrypted_api_manager import get_api_manager, APICredentials
        
        manager = get_api_manager()
        print("✅ SecureAPIManager 로드 성공")
        
        # 환경변수에서 로드 테스트
        creds = manager.get_from_env("binance")
        if creds:
            print(f"✅ 환경변수에서 로드: {manager.mask_key(creds.api_key)}")
        else:
            print("⚠️  환경변수에 API 키 없음")
        
        # 암호화 저장 테스트
        test_creds = APICredentials(
            api_key="test_key_12345",
            api_secret="test_secret_67890",
            exchange="test_exchange",
            is_testnet=True,
        )
        
        if manager.store_credentials("test_integration", test_creds):
            print("✅ 암호화 저장 성공")
            
            # 로드 테스트
            loaded = manager.load_credentials("test_integration")
            if loaded and loaded.api_key == test_creds.api_key:
                print("✅ 복호화 로드 성공")
            else:
                print("❌ 복호화 로드 실패")
            
            # 정리
            manager.delete_credentials("test_integration")
            print("✅ 테스트 자격증명 삭제")
        else:
            print("❌ 암호화 저장 실패")
            
    except ImportError as e:
        print(f"❌ SecureAPIManager 로드 실패: {e}")
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")


def test_live_safeguards():
    """LiveTradingSafeguards 테스트"""
    print("\n" + "="*60)
    print("🧪 LiveTradingSafeguards 테스트")
    print("="*60)
    
    try:
        from src.trading.live_safeguards import LiveTradingSafeguards, SafeguardConfig
        
        # 테스트용 설정
        config = SafeguardConfig(
            max_position_size_percent=10.0,
            daily_loss_limit_percent=5.0,
            max_consecutive_losses=3,
        )
        
        safeguards = LiveTradingSafeguards(
            config=config,
            initial_balance=10000.0,
            state_file=".test_trading_state.json",
        )
        print("✅ LiveTradingSafeguards 생성 성공")
        
        # 시작 테스트
        if safeguards.start():
            print("✅ 트레이딩 시작 성공")
        
        # 거래 가능 체크
        can_trade, reason = safeguards.can_trade()
        print(f"✅ 거래 가능 체크: {can_trade} ({reason})")
        
        # 포지션 크기 체크
        is_valid, msg, adjusted = safeguards.check_position_size(0.5, 50000)
        print(f"✅ 포지션 크기 체크: {is_valid} - {msg}")
        
        # 거래 기록 테스트
        safeguards.record_trade(pnl=100, is_win=True)
        print(f"✅ 승리 기록: 잔고=${safeguards.metrics.current_balance}")
        
        safeguards.record_trade(pnl=-50, is_win=False)
        print(f"✅ 패배 기록: 잔고=${safeguards.metrics.current_balance}")
        
        # 상태 조회
        status = safeguards.get_status()
        print(f"✅ 상태 조회: {status['state']}")
        
        # 긴급 정지 테스트
        safeguards.emergency_stop("테스트 긴급 정지")
        can_trade, reason = safeguards.can_trade()
        print(f"✅ 긴급 정지 후: {can_trade} ({reason})")
        
        # 긴급 정지 해제
        safeguards.reset_emergency_stop()
        print("✅ 긴급 정지 해제")
        
        # 정리
        import os
        if os.path.exists(".test_trading_state.json"):
            os.remove(".test_trading_state.json")
            print("✅ 테스트 상태 파일 삭제")
            
    except ImportError as e:
        print(f"❌ LiveTradingSafeguards 로드 실패: {e}")
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")


def test_live_trading_api():
    """Live Trading API 테스트"""
    print("\n" + "="*60)
    print("🧪 Live Trading API 테스트")
    print("="*60)
    
    # 상태 조회 테스트
    try:
        response = requests.get(f"{BASE_URL}/api/live/status", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ GET /api/live/status: {response.status_code}")
            print(f"   상태: {data.get('status', {}).get('state', 'N/A')}")
        else:
            print(f"⚠️  GET /api/live/status: {response.status_code}")
    except Exception as e:
        print(f"❌ 상태 조회 실패: {e}")
    
    # 긴급 정지 테스트 (API 키 없이)
    try:
        response = requests.post(
            f"{BASE_URL}/api/emergency-stop",
            json={"reason": "테스트", "api_key": "invalid_key"},
            timeout=10
        )
        if response.status_code == 401:
            print("✅ POST /api/emergency-stop: 인증 실패 (예상대로)")
        elif response.status_code == 200:
            print("⚠️  POST /api/emergency-stop: 인증 없이 성공 (API_SECRET_KEY 미설정)")
        else:
            print(f"⚠️  POST /api/emergency-stop: {response.status_code}")
    except Exception as e:
        print(f"❌ 긴급 정지 테스트 실패: {e}")


def test_multi_strategy_bot_imports():
    """MultiStrategyBot 임포트 테스트"""
    print("\n" + "="*60)
    print("🧪 MultiStrategyBot 임포트 테스트")
    print("="*60)
    
    try:
        from multi_strategy_bot import (
            Config, MultiStrategyBot, 
            SECURE_API_AVAILABLE, SAFEGUARDS_AVAILABLE
        )
        
        print("✅ MultiStrategyBot 임포트 성공")
        print(f"   SecureAPIManager 사용 가능: {SECURE_API_AVAILABLE}")
        print(f"   LiveTradingSafeguards 사용 가능: {SAFEGUARDS_AVAILABLE}")
        
        # Config 테스트
        config = Config()
        print(f"✅ Config 생성 성공")
        print(f"   Paper Trading: {config.PAPER_TRADING}")
        print(f"   Use Testnet: {config.USE_TESTNET}")
        
        if config.API_KEY:
            from encrypted_api_manager import SecureAPIManager
            print(f"   API Key: {SecureAPIManager.mask_key(config.API_KEY)}")
        else:
            print("   API Key: 미설정")
            
    except ImportError as e:
        print(f"❌ 임포트 실패: {e}")
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")


def main():
    """메인 테스트 실행"""
    print("\n" + "="*60)
    print("🚀 통합 테스트 시작")
    print("="*60)
    
    # 1. SecureAPIManager 테스트
    test_secure_api_manager()
    
    # 2. LiveTradingSafeguards 테스트
    test_live_safeguards()
    
    # 3. MultiStrategyBot 임포트 테스트
    test_multi_strategy_bot_imports()
    
    # 4. Live Trading API 테스트
    test_live_trading_api()
    
    print("\n" + "="*60)
    print("✅ 통합 테스트 완료")
    print("="*60)


if __name__ == "__main__":
    main()
