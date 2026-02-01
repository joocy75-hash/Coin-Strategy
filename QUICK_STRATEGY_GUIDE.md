# ⚡ 빠른 전략 적용 가이드

## 🎯 목적
이미 실행 중인 Freqtrade 서버에 SimpleAdaptiveStrategy 추가

---

## 📦 필요한 파일

1. **SimpleAdaptiveStrategy.py** (전략 코드)
2. **STRATEGY_HANDOVER.md** (상세 설명)

---

## 🚀 3단계 설치

### 1단계: 파일 업로드 (2분)
```bash
scp SimpleAdaptiveStrategy.py root@YOUR_SERVER:/path/to/freqtrade/user_data/strategies/
```

### 2단계: 설정 수정 (3분)
```bash
# config.json 수정
{
    "strategy": "SimpleAdaptiveStrategy",
    "timeframe": "1h"
}
```

### 3단계: 재시작 (2분)
```bash
docker-compose restart
# 또는
freqtrade trade --config config.json --strategy SimpleAdaptiveStrategy
```

---

## ✅ 확인 방법

```bash
# 전략 로드 확인
freqtrade list-strategies --config config.json

# 로그 확인
tail -f logs/freqtrade.log
```

---

## 📊 전략 요약

**진입**: EMA(9) > EMA(21) + RSI 40-70 + MACD 상승 + 볼륨 확인
**청산**: EMA 크로스다운 또는 RSI > 75 또는 MACD 하락
**리스크**: 손절 -3%, 트레일링 스톱 활성화

**성과**: 평균 수익률 111%, Sharpe 0.30, 일관성 80%

---

## ⚠️ 주의사항

- 소액으로 시작 (거래당 10-20 USDT)
- Dry Run으로 먼저 테스트 권장
- 정기 모니터링 필수

---

## 📞 문제 해결

**전략이 안 보임**: 파일 경로 및 권한 확인
**진입 신호 없음**: 정상 (조건이 까다로움, 하루 0-2회)
**에러 발생**: STRATEGY_HANDOVER.md 참조

---

**총 소요 시간**: 7분
**상세 가이드**: STRATEGY_HANDOVER.md
