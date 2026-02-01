# 📦 SimpleAdaptiveStrategy 전략 패키지

## 🎯 이 패키지는?

이미 실행 중인 Freqtrade 서버에 SimpleAdaptiveStrategy 전략을 추가하기 위한 패키지입니다.

---

## 📁 패키지 내용

```
strategy_package/
├── README.md                      # 이 파일
├── SimpleAdaptiveStrategy.py      # 전략 코드 (필수)
├── STRATEGY_HANDOVER.md           # 상세 설명서
├── QUICK_STRATEGY_GUIDE.md        # 빠른 가이드
└── STRATEGY_ONLY_PROMPT.txt       # Claude 전달용 프롬프트
```

---

## 🚀 빠른 시작 (3단계)

### 1. 파일 업로드
```bash
scp SimpleAdaptiveStrategy.py root@YOUR_SERVER:/path/to/freqtrade/user_data/strategies/
```

### 2. 설정 수정
```json
{
    "strategy": "SimpleAdaptiveStrategy",
    "timeframe": "1h"
}
```

### 3. 재시작
```bash
docker-compose restart
```

---

## 📊 전략 정보

### 성과 (백테스트)
- **평균 수익률**: 111.08%
- **Sharpe Ratio**: 0.30
- **Win Rate**: 26.20%
- **일관성**: 80%

### 로직
- **진입**: EMA 크로스오버 + RSI + MACD + 볼륨
- **청산**: EMA 크로스다운 또는 RSI 과매수 또는 MACD 하락
- **리스크**: 손절 -3%, 트레일링 스톱

---

## 📖 문서 가이드

### 처음 사용하는 경우
1. **QUICK_STRATEGY_GUIDE.md** 읽기 (5분)
2. **SimpleAdaptiveStrategy.py** 업로드
3. 설정 수정 및 재시작

### 상세 정보가 필요한 경우
**STRATEGY_HANDOVER.md** 참조
- 전략 로직 상세 설명
- 설치 방법 (2가지)
- 테스트 방법
- 문제 해결

### Claude에게 전달하는 경우
**STRATEGY_ONLY_PROMPT.txt** 사용
1. 파일 열기
2. `[필요한 작업]` 부분 수정
3. 복사 & 붙여넣기
4. SimpleAdaptiveStrategy.py 첨부

---

## ⚡ 초간단 가이드

```bash
# 1. 업로드
scp SimpleAdaptiveStrategy.py root@SERVER:/freqtrade/user_data/strategies/

# 2. 확인
ssh root@SERVER "freqtrade list-strategies --config config.json"

# 3. 설정 (config.json)
"strategy": "SimpleAdaptiveStrategy"

# 4. 재시작
ssh root@SERVER "docker-compose restart"
```

---

## ⚠️ 주의사항

- ✅ 기존 Freqtrade 서버에 전략만 추가
- ✅ 기존 설정은 유지
- ✅ Dry Run으로 먼저 테스트 권장
- ✅ 소액으로 시작

---

## 📞 도움말

### 문제 발생 시
1. STRATEGY_HANDOVER.md의 "문제 해결" 섹션 참조
2. 로그 확인: `tail -f logs/freqtrade.log`
3. 전략 목록 확인: `freqtrade list-strategies`

### 추가 정보
- Freqtrade 공식 문서: https://www.freqtrade.io
- 전략 개발 가이드: https://www.freqtrade.io/en/stable/strategy-customization/

---

## ✅ 체크리스트

설치 전:
- [ ] 전략 파일 준비
- [ ] 서버 접속 정보 확인
- [ ] Freqtrade 경로 확인

설치:
- [ ] 파일 업로드
- [ ] 전략 목록 확인
- [ ] 설정 수정

테스트:
- [ ] Dry Run 테스트 (권장)
- [ ] 로그 확인
- [ ] 진입 신호 확인

실전:
- [ ] 잔고 확인
- [ ] 모니터링 준비
- [ ] 봇 재시작

---

**준비 완료! 전략을 적용하세요! 🚀**

**예상 소요 시간**: 7분
- 파일 업로드: 2분
- 설정 수정: 3분
- 재시작 및 확인: 2분
