#!/usr/bin/env python3
"""
Binance Futures Testnet 연결 테스트 (개선 버전)
"""

import asyncio
import os
import sys

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    import ccxt.async_support as ccxt
except ImportError:
    print("ccxt 필요: pip install ccxt")
    sys.exit(1)


async def test_connection():
    """Binance Futures Testnet 연결 테스트"""

    print("=" * 60)
    print("Binance Futures Testnet 연결 테스트")
    print("=" * 60)

    api_key = os.getenv('BINANCE_API_KEY', '')
    api_secret = os.getenv('BINANCE_API_SECRET', '')

    if not api_key or not api_secret:
        print("\n❌ API 키가 설정되지 않았습니다!")
        print(".env 파일 확인 필요")
        return False

    print(f"\n✓ API Key: {api_key[:10]}...{api_key[-5:]}")
    print(f"✓ API Secret: {api_secret[:5]}...{api_secret[-5:]}")

    # 방법 1: ccxt sandbox mode 사용
    print("\n[방법 1] ccxt sandbox mode 테스트...")
    exchange1 = ccxt.binance({
        'apiKey': api_key,
        'secret': api_secret,
        'enableRateLimit': True,
        'options': {
            'defaultType': 'future',
            'adjustForTimeDifference': True
        }
    })
    exchange1.set_sandbox_mode(True)

    try:
        await exchange1.load_markets()
        ticker = await exchange1.fetch_ticker('BTC/USDT:USDT')
        print(f"    ✓ Sandbox 모드 성공! BTC: ${ticker['last']:,.2f}")
        balance = await exchange1.fetch_balance()
        usdt = float(balance.get('USDT', {}).get('free', 0))
        print(f"    ✓ USDT 잔고: ${usdt:,.2f}")
        await exchange1.close()
        return True
    except Exception as e1:
        print(f"    ✗ Sandbox 모드 실패: {e1}")
        await exchange1.close()

    # 방법 2: 직접 URL 설정 (demo-fapi)
    print("\n[방법 2] 직접 URL 설정 테스트 (demo-fapi)...")
    exchange2 = ccxt.binance({
        'apiKey': api_key,
        'secret': api_secret,
        'enableRateLimit': True,
        'options': {
            'defaultType': 'future',
            'adjustForTimeDifference': True,
        },
        'urls': {
            'api': {
                'fapiPublic': 'https://demo-fapi.binance.com/fapi/v1',
                'fapiPrivate': 'https://demo-fapi.binance.com/fapi/v1',
            }
        }
    })

    try:
        await exchange2.load_markets()
        ticker = await exchange2.fetch_ticker('BTC/USDT:USDT')
        print(f"    ✓ demo-fapi 성공! BTC: ${ticker['last']:,.2f}")
        balance = await exchange2.fetch_balance()
        usdt = float(balance.get('USDT', {}).get('free', 0))
        print(f"    ✓ USDT 잔고: ${usdt:,.2f}")
        await exchange2.close()
        return True
    except Exception as e2:
        print(f"    ✗ demo-fapi 실패: {e2}")
        await exchange2.close()

    # 방법 3: binanceusdm 사용
    print("\n[방법 3] binanceusdm 클래스 테스트...")
    try:
        exchange3 = ccxt.binanceusdm({
            'apiKey': api_key,
            'secret': api_secret,
            'enableRateLimit': True,
            'options': {
                'adjustForTimeDifference': True,
            }
        })
        exchange3.set_sandbox_mode(True)

        await exchange3.load_markets()
        ticker = await exchange3.fetch_ticker('BTC/USDT:USDT')
        print(f"    ✓ binanceusdm 성공! BTC: ${ticker['last']:,.2f}")
        balance = await exchange3.fetch_balance()
        usdt = float(balance.get('USDT', {}).get('free', 0))
        print(f"    ✓ USDT 잔고: ${usdt:,.2f}")
        await exchange3.close()
        return True
    except Exception as e3:
        print(f"    ✗ binanceusdm 실패: {e3}")

    # 방법 4: Public API만 테스트
    print("\n[방법 4] Public API 테스트 (인증 없이)...")
    exchange4 = ccxt.binance({
        'enableRateLimit': True,
        'options': {
            'defaultType': 'future',
        }
    })

    try:
        await exchange4.load_markets()
        ticker = await exchange4.fetch_ticker('BTC/USDT:USDT')
        print(f"    ✓ Public API 성공! BTC: ${ticker['last']:,.2f}")
        print("\n⚠️  API 키 인증 문제 - 다음을 확인하세요:")
        print("    1. testnet.binancefuture.com 에서 새 API 키 생성")
        print("    2. Mainnet API 키라면 USE_TESTNET=false로 변경")
        await exchange4.close()
    except Exception as e4:
        print(f"    ✗ Public API도 실패: {e4}")

    return False


async def test_mainnet():
    """Mainnet 연결 테스트"""
    print("\n" + "=" * 60)
    print("Mainnet 연결 테스트 (API 키 유효성 확인)")
    print("=" * 60)

    api_key = os.getenv('BINANCE_API_KEY', '')
    api_secret = os.getenv('BINANCE_API_SECRET', '')

    exchange = ccxt.binance({
        'apiKey': api_key,
        'secret': api_secret,
        'enableRateLimit': True,
        'options': {
            'defaultType': 'future',
            'adjustForTimeDifference': True
        }
    })

    try:
        await exchange.load_markets()
        ticker = await exchange.fetch_ticker('BTC/USDT:USDT')
        print(f"✓ Mainnet 연결 성공! BTC: ${ticker['last']:,.2f}")

        try:
            balance = await exchange.fetch_balance()
            usdt = float(balance.get('USDT', {}).get('free', 0))
            print(f"✓ Mainnet 잔고: ${usdt:,.2f}")
            print("\n✅ API 키는 Mainnet용입니다!")
            print("   → USE_TESTNET=false로 설정하거나")
            print("   → testnet.binancefuture.com에서 Testnet API 키 생성")
        except Exception as e:
            print(f"⚠ 잔고 조회 실패: {e}")
            print("   → API 키 권한 확인 필요")

        await exchange.close()
        return True
    except Exception as e:
        print(f"✗ Mainnet 연결 실패: {e}")
        await exchange.close()
        return False


if __name__ == "__main__":
    print("\n🔍 Binance API 연결 진단\n")

    # Testnet 테스트
    testnet_ok = asyncio.run(test_connection())

    if not testnet_ok:
        # Mainnet 테스트
        asyncio.run(test_mainnet())

    print("\n" + "=" * 60)
    if testnet_ok:
        print("✅ Testnet 연결 성공!")
    else:
        print("📋 API 키 문제 해결 방법:")
        print("   1. https://testnet.binancefuture.com 접속")
        print("   2. GitHub로 로그인")
        print("   3. 하단 'API Key' 탭에서 새 키 생성")
        print("   4. .env 파일에 새 키 저장")
    print("=" * 60)
