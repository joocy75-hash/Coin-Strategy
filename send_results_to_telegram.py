"""
백테스트 결과를 텔레그램으로 전송하는 스크립트

사용법:
1. .env 파일에 TELEGRAM_BOT_TOKEN과 TELEGRAM_CHAT_ID 설정
2. python send_results_to_telegram.py 실행
"""

import os
import sys
import pandas as pd
import requests
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
env_path = Path('/Users/mr.joo/Desktop/전략연구소/strategy-research-lab/.env')
if env_path.exists():
    load_dotenv(env_path)
else:
    print("⚠️  .env 파일이 없습니다. strategy-research-lab/.env 파일을 확인하세요.")
    print("필요한 환경 변수: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID")
    sys.exit(1)

# Telegram configuration
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
    print("❌ 텔레그램 설정이 없습니다!")
    print("strategy-research-lab/.env 파일에 다음을 추가하세요:")
    print("TELEGRAM_BOT_TOKEN=your_bot_token")
    print("TELEGRAM_CHAT_ID=your_chat_id")
    sys.exit(1)

def send_telegram_message(text, parse_mode='Markdown'):
    """텔레그램 메시지 전송"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

    payload = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': text,
        'parse_mode': parse_mode
    }

    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        return True
    except Exception as e:
        print(f"❌ 메시지 전송 실패: {e}")
        return False

def send_telegram_document(file_path, caption=''):
    """텔레그램 파일 전송"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendDocument"

    try:
        with open(file_path, 'rb') as file:
            files = {'document': file}
            data = {
                'chat_id': TELEGRAM_CHAT_ID,
                'caption': caption
            }
            response = requests.post(url, files=files, data=data)
            response.raise_for_status()
        return True
    except Exception as e:
        print(f"❌ 파일 전송 실패: {e}")
        return False

def main():
    """메인 실행 함수"""

    base_path = '/Users/mr.joo/Desktop/전략연구소'

    # 1. 요약 메시지 전송
    summary_message = """
🎯 *B등급 전략 백테스트 완료*

━━━━━━━━━━━━━━━━━━━━━
*🏆 최종 순위*
━━━━━━━━━━━━━━━━━━━━━

🥇 *#1: Adaptive ML Trailing Stop*
📊 평균 수익률: *100.90%*
📈 샤프 비율: 0.40
💰 Profit Factor: 1.54
🎯 최고 성과: SOLUSDT 4h (+257.77%)

🥈 *#2: PMax - Asymmetric Multipliers*
📊 평균 수익률: 11.14%
📈 샤프 비율: -0.08
💰 Profit Factor: 1.27
🎯 최고 성과: SOLUSDT 4h (+153.79%)

🥉 *#3: Heikin Ashi Wick*
📊 평균 수익률: 43.94%
📈 샤프 비율: -0.30
💰 Profit Factor: 1.06
🎯 최고 성과: SOLUSDT 4h (+338.40%)

━━━━━━━━━━━━━━━━━━━━━
⚠️ *주의사항*
━━━━━━━━━━━━━━━━━━━━━

• 모든 전략이 Moon Dev 기준 미달
• Sharpe Ratio < 1.5
• Win Rate < 40%
• 추가 최적화 필요

📁 상세 결과는 CSV 파일을 확인하세요!
"""

    print("📤 텔레그램 메시지 전송 중...")
    if send_telegram_message(summary_message):
        print("✅ 요약 메시지 전송 완료")

    # 2. CSV 파일 전송
    csv_files = [
        {
            'path': f'{base_path}/adaptive_ml_results.csv',
            'caption': '🥇 Adaptive ML Trailing Stop - 백테스트 결과 (10개 데이터셋)'
        },
        {
            'path': f'{base_path}/pmax_results.csv',
            'caption': '🥈 PMax Asymmetric - 백테스트 결과 (10개 데이터셋)'
        },
        {
            'path': f'{base_path}/heikin_ashi_results.csv',
            'caption': '🥉 Heikin Ashi Wick - 백테스트 결과 (10개 데이터셋)'
        }
    ]

    for file_info in csv_files:
        file_path = file_info['path']
        caption = file_info['caption']

        if os.path.exists(file_path):
            print(f"📤 파일 전송 중: {os.path.basename(file_path)}")
            if send_telegram_document(file_path, caption):
                print(f"✅ {os.path.basename(file_path)} 전송 완료")
        else:
            print(f"⚠️  파일 없음: {file_path}")

    # 3. 전략 코드 파일 전송 (선택사항)
    print("\n📁 전략 Python 코드 파일도 전송하시겠습니까? (y/n): ", end='')
    choice = input().strip().lower()

    if choice == 'y':
        strategy_files = [
            {
                'path': f'{base_path}/trading-agent-system/strategies/adaptive_ml_trailing_stop.py',
                'caption': '🥇 Adaptive ML Trailing Stop - Python 소스코드'
            },
            {
                'path': f'{base_path}/trading-agent-system/strategies/pmax_asymmetric.py',
                'caption': '🥈 PMax Asymmetric - Python 소스코드'
            },
            {
                'path': f'{base_path}/trading-agent-system/strategies/heikin_ashi_wick.py',
                'caption': '🥉 Heikin Ashi Wick - Python 소스코드'
            }
        ]

        for file_info in strategy_files:
            file_path = file_info['path']
            caption = file_info['caption']

            if os.path.exists(file_path):
                print(f"📤 코드 파일 전송 중: {os.path.basename(file_path)}")
                if send_telegram_document(file_path, caption):
                    print(f"✅ {os.path.basename(file_path)} 전송 완료")

    # 4. 비교 분석 스크립트 결과 전송
    print("\n" + "=" * 50)
    print("🎉 모든 파일 전송 완료!")
    print("=" * 50)
    print("\n텔레그램에서 다음 파일들을 확인하세요:")
    print("1️⃣ 요약 메시지 (순위 및 주요 지표)")
    print("2️⃣ adaptive_ml_results.csv")
    print("3️⃣ pmax_results.csv")
    print("4️⃣ heikin_ashi_results.csv")
    if choice == 'y':
        print("5️⃣ Python 전략 소스코드 파일들")

if __name__ == "__main__":
    main()
