# 텔레그램 알림 설정 가이드

백테스트 결과를 자동으로 텔레그램으로 받을 수 있습니다.

## 📱 1단계: 텔레그램 봇 만들기

1. 텔레그램에서 **@BotFather** 검색
2. `/newbot` 명령 입력
3. 봇 이름 입력 (예: "Strategy Backtest Bot")
4. 봇 사용자명 입력 (예: "my_strategy_backtest_bot")
5. **봇 토큰 복사** (예: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

## 🆔 2단계: Chat ID 확인

### 방법 1: 개인 채팅 사용

1. 만든 봇과 대화 시작 (`/start` 입력)
2. 다음 URL을 브라우저에서 열기:
   ```
   https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates
   ```
   `<YOUR_BOT_TOKEN>`을 실제 봇 토큰으로 교체

3. JSON 응답에서 `"chat":{"id":` 뒤의 숫자 확인 (예: `123456789`)

### 방법 2: 그룹 채팅 사용 (추천)

1. 새 그룹 생성
2. 만든 봇을 그룹에 초대
3. 그룹에 메시지 보내기
4. 위의 getUpdates URL 확인
5. `"chat":{"id":` 뒤의 숫자 확인 (그룹은 음수로 시작: `-123456789`)

## ⚙️ 3단계: .env 파일 설정

`strategy-research-lab/.env` 파일을 열고 다음 줄을 **추가**하세요:

```bash
# ================================================
# Telegram Notifications
# ================================================

TELEGRAM_BOT_TOKEN=여기에_봇_토큰_입력
TELEGRAM_CHAT_ID=여기에_Chat_ID_입력
```

### 예시:
```bash
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_CHAT_ID=123456789
```

또는 그룹 채팅:
```bash
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_CHAT_ID=-987654321
```

## 🚀 4단계: 테스트

설정이 완료되면 다음 명령으로 테스트:

```bash
cd /Users/mr.joo/Desktop/전략연구소
python auto_send_backtest_results.py
```

성공하면 텔레그램에 다음과 같은 메시지가 전송됩니다:
- 📊 전략 비교 요약
- 🥇 Adaptive ML 결과 + CSV 파일
- 🥈 PMax 결과 + CSV 파일
- 🥉 Heikin Ashi 결과 + CSV 파일

## 📋 전송되는 내용

### 1. 비교 요약 메시지
```
🏆 B등급 전략 Top 3 비교 완료!

━━━━━━━━━━━━━━━━━━━━━
순위
━━━━━━━━━━━━━━━━━━━━━

🥇 Adaptive ML Trailing Stop
   평균 수익률: 100.90%

🥈 PMax - Asymmetric Multipliers
   평균 수익률: 11.14%

🥉 Heikin Ashi Wick
   평균 수익률: 43.94%
...
```

### 2. 각 전략별 상세 결과
- 평균 수익률
- 샤프 비율
- 승률
- Profit Factor
- Moon Dev 기준 통과 여부

### 3. CSV 파일 (다운로드 가능)
- `adaptive_ml_results.csv`
- `pmax_results.csv`
- `heikin_ashi_results.csv`

각 CSV에는 10개 데이터셋별 상세 결과가 포함됩니다.

## 🔄 자동화 (선택사항)

백테스트 스크립트 마지막에 자동 전송 추가:

```python
# test_adaptive_ml_multi_dataset.py 마지막에 추가
if __name__ == "__main__":
    run_multi_dataset_backtest()

    # 백테스트 완료 후 텔레그램 전송
    import sys
    sys.path.append('/Users/mr.joo/Desktop/전략연구소')
    from auto_send_backtest_results import TelegramBacktestNotifier

    notifier = TelegramBacktestNotifier()
    if notifier.enabled:
        notifier.send_backtest_summary(
            "Adaptive ML Trailing Stop",
            pd.read_csv('/Users/mr.joo/Desktop/전략연구소/adaptive_ml_results.csv'),
            "SOLUSDT 4h",
            257.77,
            2.54
        )
```

## ❓ 문제 해결

### "텔레그램 설정 없음" 오류
- `.env` 파일이 올바른 위치에 있는지 확인
- `TELEGRAM_BOT_TOKEN`과 `TELEGRAM_CHAT_ID`가 정확히 입력되었는지 확인
- 환경 변수 이름 오타 확인

### "텔레그램 전송 실패" 오류
- 봇 토큰이 올바른지 확인 (BotFather에서 재확인)
- Chat ID가 올바른지 확인 (getUpdates로 재확인)
- 봇과 대화를 시작했는지 확인 (`/start` 입력)
- 그룹 사용 시 봇이 그룹에 초대되었는지 확인

### CSV 파일이 전송되지 않음
- CSV 파일이 존재하는지 확인:
  ```bash
  ls -la /Users/mr.joo/Desktop/전략연구소/*.csv
  ```
- 백테스트가 완료되었는지 확인

## 📱 웹 대시보드 (향후 추가 가능)

원하시면 다음 기능도 추가할 수 있습니다:

1. **텔레그램 봇 명령어**
   - `/results` - 최신 백테스트 결과 보기
   - `/top3` - Top 3 전략 보기
   - `/download <strategy_name>` - CSV 파일 다운로드

2. **실시간 알림**
   - 백테스트 시작 시 알림
   - 각 데이터셋 완료 시 진행률 알림
   - 최종 완료 시 요약 알림

3. **인터랙티브 버튼**
   - CSV 다운로드 버튼
   - Python 코드 다운로드 버튼
   - 상세 결과 보기 버튼

필요하시면 말씀해주세요!

---

**작성일**: 2026-01-04
**버전**: 1.0
