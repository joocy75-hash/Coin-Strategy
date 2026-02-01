# 🎯 Freqtrade 전략 전달 패키지

**목적**: 이미 실행 중인 Freqtrade 서버에 새로운 전략 추가

---

## 📦 전달 파일

### 1. 전략 파일 (필수)
```
freqtrade/user_data/strategies/SimpleAdaptiveStrategy.py
```

### 2. 전략 설명서 (이 문서)
```
STRATEGY_HANDOVER.md
```

---

## 📊 전략 정보

### 전략명
**SimpleAdaptiveStrategy**

### 전략 개요
- **타입**: EMA 크로스오버 기반 추세 추종 전략
- **타임프레임**: 1시간 (1h)
- **거래 방향**: Long Only (매수만)
- **기반**: Adaptive ML Trailing Stop (평균 수익률 111%, Sharpe 0.30)

### 성과 지표 (백테스트 기준)
- **평균 수익률**: 111.08%
- **Sharpe Ratio**: 0.30
- **Win Rate**: 26.20%
- **Profit Factor**: 2.83
- **Max Drawdown**: -41.74%
- **일관성**: 80% (10개 데이터셋 중 8개에서 수익)

---

## 🎯 전략 로직

### 진입 조건 (모두 충족 시 매수)
1. **EMA 크로스오버**: EMA(9) > EMA(21)
2. **RSI 필터**: 40 < RSI < 70
3. **MACD 확인**: MACD > Signal
4. **볼륨 확인**: Volume > 평균 볼륨의 50%

### 청산 조건 (하나라도 충족 시 매도)
1. **EMA 크로스다운**: EMA(9) < EMA(21)
2. **RSI 과매수**: RSI > 75
3. **MACD 하락**: MACD < Signal

### 리스크 관리
- **손절**: -3%
- **목표 수익**: 
  - 즉시: 10%
  - 1시간 후: 5%
  - 2시간 후: 2%
- **트레일링 스톱**: 
  - 활성화: 2% 이익 후
  - 트레일링: 1%

---

## 🔧 설치 방법

### 방법 1: 수동 업로드 (권장)

```bash
# 1. 서버 접속
ssh root@YOUR_SERVER_IP

# 2. 전략 디렉토리로 이동
cd /path/to/freqtrade/user_data/strategies/

# 3. 전략 파일 업로드 (로컬에서 실행)
scp SimpleAdaptiveStrategy.py root@YOUR_SERVER_IP:/path/to/freqtrade/user_data/strategies/

# 4. 파일 권한 설정
chmod 644 SimpleAdaptiveStrategy.py

# 5. 전략 목록 확인
freqtrade list-strategies --config /path/to/config.json
```

### 방법 2: 직접 복사

```bash
# 1. 서버에서 파일 생성
ssh root@YOUR_SERVER_IP
cd /path/to/freqtrade/user_data/strategies/
nano SimpleAdaptiveStrategy.py

# 2. SimpleAdaptiveStrategy.py 내용 전체 복사 & 붙여넣기

# 3. 저장 (Ctrl+O, Enter, Ctrl+X)

# 4. 전략 확인
freqtrade list-strategies --config /path/to/config.json
```

---

## ⚙️ 설정 방법

### config.json 수정

기존 Freqtrade 설정 파일에서 다음 항목만 수정:

```json
{
    "strategy": "SimpleAdaptiveStrategy",
    "timeframe": "1h",
    "max_open_trades": 3,
    "stake_amount": 20,
    "dry_run": false
}
```

### 권장 설정

```json
{
    "strategy": "SimpleAdaptiveStrategy",
    "timeframe": "1h",
    "max_open_trades": 3,
    "stake_amount": 20,
    "stake_currency": "USDT",
    "dry_run": false,
    "trading_mode": "spot",
    
    "minimal_roi": {
        "0": 0.10,
        "60": 0.05,
        "120": 0.02
    },
    
    "stoploss": -0.03,
    
    "trailing_stop": true,
    "trailing_stop_positive": 0.01,
    "trailing_stop_positive_offset": 0.02,
    "trailing_only_offset_is_reached": true
}
```

---

## 🧪 테스트 방법

### 1. 전략 검증
```bash
# 전략 파일 문법 확인
freqtrade list-strategies --config config.json

# 출력 예시:
# Found 1 strategy:
# - SimpleAdaptiveStrategy
```

### 2. 백테스트 (선택)
```bash
# 최근 30일 데이터로 백테스트
freqtrade backtesting \
  --config config.json \
  --strategy SimpleAdaptiveStrategy \
  --timerange 20231201- \
  --breakdown day
```

### 3. Dry Run 테스트 (권장)
```bash
# 1. config.json에서 dry_run: true로 설정
# 2. 봇 시작
freqtrade trade --config config.json --strategy SimpleAdaptiveStrategy

# 3. 1-2시간 관찰 후 로그 확인
# 4. 정상 작동 확인 후 실전 전환
```

---

## 🚀 실전 적용

### 단계별 적용

```bash
# 1. 기존 봇 중지
# Docker 사용 시
docker-compose down

# 또는 프로세스 종료
pkill -f "freqtrade trade"

# 2. config.json 수정
nano config.json
# strategy: "SimpleAdaptiveStrategy" 설정
# dry_run: false 설정

# 3. 봇 재시작
# Docker 사용 시
docker-compose up -d

# 또는 직접 실행
freqtrade trade --config config.json --strategy SimpleAdaptiveStrategy

# 4. 로그 확인
tail -f logs/freqtrade.log
# 또는 Docker
docker-compose logs -f
```

---

## 📊 모니터링

### 확인 사항

1. **전략 로딩 확인**
   ```
   로그에서 "Using resolved strategy SimpleAdaptiveStrategy" 확인
   ```

2. **지표 계산 확인**
   ```
   로그에서 "Calculating indicators" 확인
   ```

3. **진입 신호 확인**
   ```
   로그에서 "Buy signal found" 확인
   ```

4. **포지션 확인**
   ```bash
   # API 사용 시
   curl http://localhost:8080/api/v1/status
   ```

---

## ⚠️ 주의사항

### 실전 적용 전 체크리스트

- [ ] 전략 파일이 올바르게 업로드되었는가?
- [ ] 전략이 목록에 표시되는가?
- [ ] 백테스트를 실행했는가? (선택)
- [ ] Dry Run으로 테스트했는가? (권장)
- [ ] config.json 설정이 올바른가?
- [ ] 거래소 API 연결이 정상인가?
- [ ] 충분한 잔고가 있는가?
- [ ] 모니터링 준비가 되었는가?

### 리스크 관리

1. **소액으로 시작**: 거래당 10-20 USDT
2. **최대 동시 거래 제한**: 3개 이하
3. **정기 모니터링**: 하루 2-3회
4. **손실 한도 설정**: 일일/주간 최대 손실 한도

---

## 🔧 문제 해결

### 전략이 로드되지 않음
```bash
# 1. 파일 위치 확인
ls -la user_data/strategies/SimpleAdaptiveStrategy.py

# 2. 파일 권한 확인
chmod 644 user_data/strategies/SimpleAdaptiveStrategy.py

# 3. 문법 오류 확인
python3 -m py_compile user_data/strategies/SimpleAdaptiveStrategy.py

# 4. 전략 목록 재확인
freqtrade list-strategies --config config.json
```

### 진입 신호가 없음
- 정상입니다. 진입 조건이 까다로워서 신호가 자주 발생하지 않습니다.
- 1시간 타임프레임에서 하루 0-2회 정도 신호 발생
- 로그에서 "No entry signal" 메시지 확인

### 의존성 오류
```bash
# 필요한 라이브러리 설치
pip install ta-lib pandas numpy
```

---

## 📞 지원

### 추가 정보 필요 시

**전략 코드**: `SimpleAdaptiveStrategy.py` 파일 참조

**Freqtrade 문서**: https://www.freqtrade.io/en/stable/

**전략 개발 가이드**: https://www.freqtrade.io/en/stable/strategy-customization/

---

## 📝 변경 이력

### v1.0 (2026-01-20)
- 초기 버전
- EMA 크로스오버 기반
- RSI, MACD 필터링
- 트레일링 스톱 적용

---

## ✅ 빠른 체크리스트

### 설치
- [ ] 전략 파일 업로드
- [ ] 파일 권한 설정
- [ ] 전략 목록 확인

### 설정
- [ ] config.json 수정
- [ ] 전략명 설정
- [ ] 타임프레임 설정
- [ ] 리스크 설정

### 테스트
- [ ] 전략 검증
- [ ] 백테스트 (선택)
- [ ] Dry Run (권장)

### 실전
- [ ] 기존 봇 중지
- [ ] 설정 적용
- [ ] 봇 재시작
- [ ] 로그 확인
- [ ] 모니터링 시작

---

**준비 완료! 전략을 적용하세요! 🚀**

**예상 소요 시간**: 10-15분
- 파일 업로드: 2분
- 설정 수정: 3분
- 테스트: 5분
- 실전 적용: 5분

**문의사항이 있으면 언제든지 알려주세요!**
