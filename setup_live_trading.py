#!/usr/bin/env python3
"""
실전매매 설정 스크립트
"""

import json
from pathlib import Path
import sys

def setup_live_trading(dry_run=True, stake_amount=10):
    """
    실전매매 설정
    
    Args:
        dry_run: True면 가상 거래, False면 실제 거래
        stake_amount: 거래당 투자 금액 (USDT)
    """
    
    config_path = Path("freqtrade/config.json")
    
    if not config_path.exists():
        print("❌ config.json 파일을 찾을 수 없습니다!")
        return False
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        print("=" * 60)
        print("🚀 Freqtrade 실전매매 설정")
        print("=" * 60)
        print()
        
        # 현재 설정 표시
        print("📊 현재 설정:")
        print(f"   Dry Run: {config.get('dry_run', True)}")
        print(f"   거래소: {config.get('exchange', {}).get('name', 'N/A')}")
        print(f"   투자 금액: {config.get('stake_amount', 'unlimited')}")
        print()
        
        # 새 설정 적용
        if dry_run:
            print("⚙️  Dry Run 모드로 설정 중...")
            config['dry_run'] = True
            config['dry_run_wallet'] = 1000
            config['stake_amount'] = 'unlimited'
            mode_text = "가상 거래 (안전)"
        else:
            print("⚠️  실전 거래 모드로 설정 중...")
            print()
            print("🔴 경고: 실제 자금이 사용됩니다!")
            print()
            
            # 사용자 확인
            confirm = input("실전 거래를 시작하시겠습니까? (yes/no): ").strip().lower()
            if confirm != 'yes':
                print("❌ 취소되었습니다.")
                return False
            
            config['dry_run'] = False
            config['stake_amount'] = stake_amount
            config['strategy'] = 'SimpleAdaptiveStrategy'
            mode_text = f"실전 거래 (거래당 {stake_amount} USDT)"
        
        # 전략 설정
        config['strategy'] = 'SimpleAdaptiveStrategy'
        
        # 리스크 관리 강화
        config['max_open_trades'] = 3
        config['tradable_balance_ratio'] = 0.99
        
        # 설정 저장
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=4)
        
        print()
        print("✅ 설정 완료!")
        print()
        print("📝 새로운 설정:")
        print(f"   모드: {mode_text}")
        print(f"   전략: SimpleAdaptiveStrategy")
        print(f"   최대 동시 거래: {config['max_open_trades']}")
        print(f"   거래소: {config['exchange']['name']}")
        print(f"   거래쌍: {', '.join(config['exchange']['pair_whitelist'][:3])}...")
        print()
        
        if dry_run:
            print("🎯 다음 단계:")
            print("   1. 백테스트로 전략 검증:")
            print("      freqtrade backtesting --config freqtrade/config.json --strategy AdaptiveMLStrategy --timerange 20260101-")
            print()
            print("   2. Dry Run으로 실시간 테스트:")
            print("      freqtrade trade --config freqtrade/config.json")
            print()
            print("   3. 최소 1-2주간 Dry Run 테스트 후 실전 거래 고려")
        else:
            print("🚀 실전 거래 시작:")
            print("   freqtrade trade --config freqtrade/config.json")
            print()
            print("⚠️  주의사항:")
            print("   - 정기적으로 성과를 모니터링하세요")
            print("   - 손실이 발생하면 즉시 중단하세요")
            print("   - 소액으로 시작하여 점진적으로 증액하세요")
        
        print()
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"❌ 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def show_strategy_info():
    """전략 정보 표시"""
    
    print("=" * 60)
    print("📊 AdaptiveMLStrategy 전략 정보")
    print("=" * 60)
    print()
    print("🏆 성과 지표 (10개 데이터셋 평균):")
    print("   - 평균 수익률: 111.08%")
    print("   - Sharpe Ratio: 0.30")
    print("   - Win Rate: 26.20%")
    print("   - Profit Factor: 2.83")
    print("   - Max Drawdown: -41.74%")
    print("   - 일관성: 80% (10개 중 8개 데이터셋에서 수익)")
    print()
    print("📈 최고 성과:")
    print("   - SOLUSDT 1h: +483.16%")
    print()
    print("📉 최악 성과:")
    print("   - SOLUSDT 4h: -43.14%")
    print()
    print("⚙️  전략 특징:")
    print("   - KAMA (Kaufman Adaptive Moving Average) 기반")
    print("   - ATR 기반 동적 손절")
    print("   - EMA 크로스오버 신호")
    print("   - RSI, MACD 필터링")
    print("   - 적응형 트레일링 스톱")
    print()
    print("⏰ 권장 타임프레임: 1시간")
    print("💰 권장 거래쌍: BTC/USDT, ETH/USDT, SOL/USDT")
    print()
    print("=" * 60)
    print()


if __name__ == "__main__":
    show_strategy_info()
    
    print("설정 옵션을 선택하세요:")
    print("1. Dry Run 모드 (가상 거래, 권장)")
    print("2. 실전 거래 모드 (소액)")
    print("3. 취소")
    print()
    
    choice = input("선택 (1-3): ").strip()
    
    if choice == "1":
        setup_live_trading(dry_run=True)
    elif choice == "2":
        stake_amount = input("거래당 투자 금액 (USDT, 기본값 10): ").strip()
        stake_amount = float(stake_amount) if stake_amount else 10.0
        setup_live_trading(dry_run=False, stake_amount=stake_amount)
    else:
        print("취소되었습니다.")
