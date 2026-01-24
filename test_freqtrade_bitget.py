#!/usr/bin/env python3
"""
Freqtrade + Bitget 통합 테스트
"""

import json
from pathlib import Path

def test_freqtrade_config():
    """Freqtrade 설정 파일 검증"""
    
    print("=" * 60)
    print("🤖 Freqtrade + Bitget 설정 검증")
    print("=" * 60)
    print()
    
    config_path = Path("freqtrade/config.json")
    
    if not config_path.exists():
        print("❌ config.json 파일을 찾을 수 없습니다!")
        return False
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        print("✅ config.json 로드 성공")
        print()
        
        # 거래소 설정 확인
        exchange = config.get('exchange', {})
        print("📊 거래소 설정:")
        print(f"   거래소: {exchange.get('name')}")
        print(f"   API Key: {exchange.get('key')[:20]}..." if exchange.get('key') else "   API Key: 미설정")
        print(f"   API Secret: {'설정됨' if exchange.get('secret') else '미설정'}")
        print(f"   Password: {'설정됨' if exchange.get('password') else '미설정'}")
        print()
        
        # 거래쌍 확인
        whitelist = exchange.get('pair_whitelist', [])
        print(f"📈 거래쌍 ({len(whitelist)}개):")
        for pair in whitelist:
            print(f"   - {pair}")
        print()
        
        # 거래 모드 확인
        print("⚙️  거래 설정:")
        print(f"   Dry Run: {config.get('dry_run', True)}")
        print(f"   거래 모드: {config.get('trading_mode', 'spot')}")
        print(f"   최대 동시 거래: {config.get('max_open_trades', 3)}")
        print(f"   기준 통화: {config.get('stake_currency', 'USDT')}")
        print()
        
        # API 서버 확인
        api_server = config.get('api_server', {})
        if api_server.get('enabled'):
            print("🌐 API 서버:")
            print(f"   활성화: {api_server.get('enabled')}")
            print(f"   포트: {api_server.get('listen_port')}")
            print(f"   사용자명: {api_server.get('username')}")
            print()
        
        # 경고 메시지
        if config.get('dry_run'):
            print("✅ Dry Run 모드 활성화 (안전)")
            print("   → 실제 거래가 발생하지 않습니다")
        else:
            print("⚠️  실전 거래 모드!")
            print("   → 실제 자금이 사용됩니다!")
        
        print()
        print("=" * 60)
        print("✅ Freqtrade 설정 검증 완료!")
        print("=" * 60)
        print()
        
        return True
        
    except json.JSONDecodeError as e:
        print(f"❌ JSON 파싱 오류: {str(e)}")
        return False
    except Exception as e:
        print(f"❌ 오류 발생: {str(e)}")
        return False


def print_freqtrade_commands():
    """Freqtrade 실행 명령어 안내"""
    
    print("📝 Freqtrade 실행 명령어:")
    print()
    print("1️⃣  Dry Run 모드로 봇 시작:")
    print("   cd freqtrade")
    print("   freqtrade trade --config config.json --strategy SampleStrategy")
    print()
    print("2️⃣  백테스트 실행:")
    print("   freqtrade backtesting --config config.json --strategy SampleStrategy")
    print()
    print("3️⃣  데이터 다운로드:")
    print("   freqtrade download-data --exchange bitget --pairs BTC/USDT ETH/USDT --timeframe 1h")
    print()
    print("4️⃣  API 서버 시작:")
    print("   freqtrade trade --config config.json --strategy SampleStrategy")
    print("   → http://localhost:8081 에서 접속")
    print()
    print("5️⃣  전략 목록 확인:")
    print("   freqtrade list-strategies --config config.json")
    print()
    print("⚠️  주의사항:")
    print("   - 실전 거래 전 반드시 dry_run 모드로 충분히 테스트하세요")
    print("   - 전략의 성능을 백테스트로 먼저 검증하세요")
    print("   - 소액으로 시작하여 점진적으로 증액하세요")
    print()


if __name__ == "__main__":
    if test_freqtrade_config():
        print()
        print_freqtrade_commands()
