"""
백테스트 완료 후 자동으로 텔레그램으로 결과 전송

이 스크립트를 백테스트 스크립트 마지막에 호출하면
자동으로 결과가 텔레그램으로 전송됩니다.
"""

import os
import sys
import pandas as pd
import requests
from pathlib import Path
from dotenv import load_dotenv

class TelegramBacktestNotifier:
    """백테스트 결과 텔레그램 알림"""

    def __init__(self):
        # Load environment variables
        env_path = Path('/Users/mr.joo/Desktop/전략연구소/strategy-research-lab/.env')
        if env_path.exists():
            load_dotenv(env_path)

        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID')

        if not self.bot_token or not self.chat_id:
            print("⚠️  텔레그램 설정 없음. 알림을 건너뜁니다.")
            self.enabled = False
        else:
            self.enabled = True

    def send_message(self, text, parse_mode='Markdown'):
        """텔레그램 메시지 전송"""
        if not self.enabled:
            return False

        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            'chat_id': self.chat_id,
            'text': text,
            'parse_mode': parse_mode
        }

        try:
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            return True
        except Exception as e:
            print(f"텔레그램 전송 실패: {e}")
            return False

    def send_document(self, file_path, caption=''):
        """텔레그램 파일 전송"""
        if not self.enabled:
            return False

        url = f"https://api.telegram.org/bot{self.bot_token}/sendDocument"

        try:
            with open(file_path, 'rb') as file:
                files = {'document': file}
                data = {'chat_id': self.chat_id, 'caption': caption}
                response = requests.post(url, files=files, data=data, timeout=30)
                response.raise_for_status()
            return True
        except Exception as e:
            print(f"파일 전송 실패: {e}")
            return False

    def send_backtest_summary(self, strategy_name, results_df, best_symbol='', best_return=0, best_pf=0):
        """백테스트 요약 전송"""

        avg_return = results_df['Return%'].mean()
        avg_sharpe = results_df['Sharpe'].mean()
        avg_winrate = results_df['WinRate%'].mean()
        avg_pf = results_df['PF'].mean()
        total_trades = results_df['#Trades'].sum()

        # Moon Dev 기준 체크
        sharpe_pass = "✅" if avg_sharpe > 1.5 else "❌"
        winrate_pass = "✅" if avg_winrate > 40 else "❌"
        pf_pass = "✅" if avg_pf > 1.5 else "❌"

        message = f"""
🎯 *백테스트 완료: {strategy_name}*

━━━━━━━━━━━━━━━━━━━━━
*📊 평균 성과 (10개 데이터셋)*
━━━━━━━━━━━━━━━━━━━━━

💰 평균 수익률: *{avg_return:.2f}%*
📈 평균 샤프: {avg_sharpe:.2f}
🎯 평균 승률: {avg_winrate:.2f}%
💎 평균 PF: {avg_pf:.2f}
📊 총 거래: {total_trades}회

━━━━━━━━━━━━━━━━━━━━━
*🏆 최고 성과*
━━━━━━━━━━━━━━━━━━━━━

{best_symbol}: +{best_return:.2f}% (PF {best_pf:.2f})

━━━━━━━━━━━━━━━━━━━━━
*Moon Dev 기준*
━━━━━━━━━━━━━━━━━━━━━

{sharpe_pass} Sharpe > 1.5
{winrate_pass} Win Rate > 40%
{pf_pass} Profit Factor > 1.5

{'🎉 *통과!*' if (avg_sharpe > 1.5 and avg_winrate > 40 and avg_pf > 1.5) else '⚠️ *기준 미달*'}
"""
        return self.send_message(message.strip())

    def send_comparison_summary(self):
        """3개 전략 비교 요약 전송"""

        base_path = '/Users/mr.joo/Desktop/전략연구소'

        # Load all results
        try:
            pmax_df = pd.read_csv(f'{base_path}/pmax_results.csv')
            adaptive_df = pd.read_csv(f'{base_path}/adaptive_ml_results.csv')
            heikin_df = pd.read_csv(f'{base_path}/heikin_ashi_results.csv')
        except:
            print("⚠️  CSV 파일을 찾을 수 없습니다.")
            return False

        # Calculate averages
        pmax_avg = pmax_df['Return%'].mean()
        adaptive_avg = adaptive_df['Return%'].mean()
        heikin_avg = heikin_df['Return%'].mean()

        # Determine winner
        strategies = [
            ('Adaptive ML Trailing Stop', adaptive_avg, adaptive_df),
            ('PMax - Asymmetric Multipliers', pmax_avg, pmax_df),
            ('Heikin Ashi Wick', heikin_avg, heikin_df)
        ]
        strategies.sort(key=lambda x: x[1], reverse=True)

        winner = strategies[0]

        message = f"""
🏆 *B등급 전략 Top 3 비교 완료!*

━━━━━━━━━━━━━━━━━━━━━
*순위*
━━━━━━━━━━━━━━━━━━━━━

🥇 *{strategies[0][0]}*
   평균 수익률: *{strategies[0][1]:.2f}%*

🥈 *{strategies[1][0]}*
   평균 수익률: {strategies[1][1]:.2f}%

🥉 *{strategies[2][0]}*
   평균 수익률: {strategies[2][1]:.2f}%

━━━━━━━━━━━━━━━━━━━━━
*최종 추천*
━━━━━━━━━━━━━━━━━━━━━

전략: *{winner[0]}*
평균 수익률: *{winner[1]:.2f}%*
샤프 비율: {winner[2]['Sharpe'].mean():.2f}
Profit Factor: {winner[2]['PF'].mean():.2f}

⚠️ 실전 운용 전 추가 최적화 필요

📁 상세 결과는 CSV 파일 참조
"""
        return self.send_message(message.strip())


def send_all_results():
    """모든 백테스트 결과 전송 (메인 함수)"""

    notifier = TelegramBacktestNotifier()

    if not notifier.enabled:
        print("텔레그램이 설정되지 않았습니다. 건너뜁니다.")
        return

    base_path = '/Users/mr.joo/Desktop/전략연구소'

    print("\n" + "=" * 60)
    print("📤 텔레그램으로 백테스트 결과 전송 중...")
    print("=" * 60 + "\n")

    # 1. 전체 비교 요약 전송
    print("1️⃣ 전체 비교 요약 전송...")
    notifier.send_comparison_summary()

    # 2. 각 전략별 상세 결과 전송
    strategies = [
        {
            'name': 'Adaptive ML Trailing Stop',
            'file': 'adaptive_ml_results.csv',
            'emoji': '🥇'
        },
        {
            'name': 'PMax - Asymmetric Multipliers',
            'file': 'pmax_results.csv',
            'emoji': '🥈'
        },
        {
            'name': 'Heikin Ashi Wick',
            'file': 'heikin_ashi_results.csv',
            'emoji': '🥉'
        }
    ]

    for i, strategy in enumerate(strategies, 2):
        csv_path = f"{base_path}/{strategy['file']}"

        if os.path.exists(csv_path):
            print(f"{i}️⃣ {strategy['name']} 결과 전송...")

            # Load and send summary
            df = pd.read_csv(csv_path)
            best_idx = df['Return%'].idxmax()
            best_symbol = f"{df.loc[best_idx, 'Symbol']} {df.loc[best_idx, 'Timeframe']}"
            best_return = df.loc[best_idx, 'Return%']
            best_pf = df.loc[best_idx, 'PF']

            notifier.send_backtest_summary(
                strategy['name'],
                df,
                best_symbol,
                best_return,
                best_pf
            )

            # Send CSV file
            caption = f"{strategy['emoji']} {strategy['name']} - 백테스트 결과 (10개 데이터셋)"
            notifier.send_document(csv_path, caption)

    print("\n" + "=" * 60)
    print("✅ 모든 결과 전송 완료!")
    print("=" * 60)
    print("\n텔레그램을 확인하세요! 📱")


if __name__ == "__main__":
    send_all_results()
