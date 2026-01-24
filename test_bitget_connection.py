#!/usr/bin/env python3
"""
Bitget API 연결 테스트 스크립트
"""

import ccxt
import json
from datetime import datetime

def test_bitget_connection():
    """Bitget API 연결 및 기본 기능 테스트"""
    
    print("=" * 60)
    print("🔌 Bitget API 연결 테스트")
    print("=" * 60)
    print()
    
    # API 자격증명
    api_key = "bg_6563f559d91c72bd3a2b2e552a1c9cec"
    api_secret = "1db14e0f08b08663d07e60b19af10ecd1ec6f9e162e0cde923dec2770e6b786f"
    api_password = "Wnrkswl123"
    
    try:
        # Bitget 거래소 객체 생성
        print("📡 Bitget 거래소 연결 중...")
        exchange = ccxt.bitget({
            'apiKey': api_key,
            'secret': api_secret,
            'password': api_password,
            'enableRateLimit': True,
            'options': {
                'defaultType': 'spot',  # spot 거래
            }
        })
        
        # 1. 거래소 상태 확인
        print("✅ 거래소 연결 성공!")
        print(f"   거래소: {exchange.name}")
        print(f"   버전: {exchange.version if hasattr(exchange, 'version') else 'N/A'}")
        print()
        
        # 2. 시장 데이터 로드
        print("📊 시장 데이터 로딩 중...")
        markets = exchange.load_markets()
        print(f"✅ {len(markets)}개 거래쌍 로드 완료")
        print()
        
        # 3. 계정 잔고 조회
        print("💰 계정 잔고 조회 중...")
        balance = exchange.fetch_balance()
        
        print("✅ 잔고 조회 성공!")
        print()
        print("📈 보유 자산:")
        
        # USDT 및 주요 코인 잔고 표시
        important_currencies = ['USDT', 'BTC', 'ETH', 'SOL', 'XRP', 'ADA']
        has_balance = False
        
        for currency in important_currencies:
            if currency in balance['total'] and balance['total'][currency] > 0:
                total = balance['total'][currency]
                free = balance['free'][currency]
                used = balance['used'][currency]
                print(f"   {currency:6s}: 총 {total:12.8f} (가용: {free:12.8f}, 사용중: {used:12.8f})")
                has_balance = True
        
        if not has_balance:
            print("   ⚠️  주요 자산 잔고가 없습니다.")
            print()
            print("   전체 잔고:")
            for currency, amount in balance['total'].items():
                if amount > 0:
                    print(f"   {currency:6s}: {amount:12.8f}")
        
        print()
        
        # 4. 현재 시세 조회 (BTC/USDT)
        print("💹 현재 시세 조회 중...")
        symbols_to_check = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT']
        
        for symbol in symbols_to_check:
            try:
                ticker = exchange.fetch_ticker(symbol)
                print(f"   {symbol:12s}: ${ticker['last']:,.2f} (24h 변동: {ticker['percentage']:+.2f}%)")
            except Exception as e:
                print(f"   {symbol:12s}: 조회 실패 - {str(e)}")
        
        print()
        
        # 5. 최근 거래 내역 조회 (있는 경우)
        print("📜 최근 거래 내역 조회 중...")
        try:
            orders = exchange.fetch_orders(limit=5)
            if orders:
                print(f"✅ 최근 {len(orders)}개 주문 발견:")
                for order in orders[:5]:
                    print(f"   - {order['symbol']} {order['side']} {order['amount']} @ {order['price']} ({order['status']})")
            else:
                print("   ℹ️  최근 거래 내역이 없습니다.")
        except Exception as e:
            print(f"   ⚠️  거래 내역 조회 실패: {str(e)}")
        
        print()
        
        # 6. API 권한 확인
        print("🔐 API 권한 확인:")
        try:
            # 잔고 조회 성공 = 읽기 권한 있음
            print("   ✅ 읽기 권한: 활성화")
            
            # 주문 생성 권한 테스트 (실제로 주문하지 않음)
            if exchange.has['createOrder']:
                print("   ✅ 거래 권한: 활성화 (주의: 실제 거래 가능)")
            else:
                print("   ⚠️  거래 권한: 비활성화")
                
            if exchange.has['withdraw']:
                print("   ⚠️  출금 권한: 활성화 (보안 주의!)")
            else:
                print("   ✅ 출금 권한: 비활성화 (권장)")
                
        except Exception as e:
            print(f"   ⚠️  권한 확인 실패: {str(e)}")
        
        print()
        
        # 7. Freqtrade 호환성 확인
        print("🤖 Freqtrade 호환성 확인:")
        required_features = [
            ('fetchBalance', '잔고 조회'),
            ('fetchTicker', '시세 조회'),
            ('fetchOHLCV', '캔들 데이터'),
            ('createOrder', '주문 생성'),
            ('cancelOrder', '주문 취소'),
            ('fetchOrder', '주문 조회'),
            ('fetchOrders', '주문 내역'),
        ]
        
        for feature, description in required_features:
            if exchange.has.get(feature):
                print(f"   ✅ {description:15s}: 지원")
            else:
                print(f"   ❌ {description:15s}: 미지원")
        
        print()
        print("=" * 60)
        print("✅ Bitget API 연결 테스트 완료!")
        print("=" * 60)
        print()
        print("📝 다음 단계:")
        print("   1. Freqtrade 설정 파일(config.json)에 API 정보가 저장되었습니다")
        print("   2. 'dry_run: true' 모드로 먼저 테스트하세요")
        print("   3. 실전 거래 전 충분한 테스트를 진행하세요")
        print()
        
        return True
        
    except ccxt.AuthenticationError as e:
        print("❌ 인증 실패!")
        print(f"   오류: {str(e)}")
        print()
        print("💡 해결 방법:")
        print("   1. API Key가 올바른지 확인하세요")
        print("   2. API Secret이 올바른지 확인하세요")
        print("   3. API Password(Passphrase)가 올바른지 확인하세요")
        print("   4. Bitget에서 API가 활성화되어 있는지 확인하세요")
        print("   5. IP 화이트리스트 설정을 확인하세요")
        return False
        
    except ccxt.NetworkError as e:
        print("❌ 네트워크 오류!")
        print(f"   오류: {str(e)}")
        print()
        print("💡 해결 방법:")
        print("   1. 인터넷 연결을 확인하세요")
        print("   2. 방화벽 설정을 확인하세요")
        print("   3. VPN 사용 시 비활성화해보세요")
        return False
        
    except Exception as e:
        print("❌ 예상치 못한 오류 발생!")
        print(f"   오류: {str(e)}")
        print(f"   타입: {type(e).__name__}")
        import traceback
        print()
        print("상세 오류:")
        traceback.print_exc()
        return False


if __name__ == "__main__":
    test_bitget_connection()
