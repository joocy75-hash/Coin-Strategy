# 🤖 Freqtrade 실전매매 시스템 인수인계 문서

**작성일**: 2026-01-20  
**목적**: 다른 Claude AI에게 현재 설정된 Freqtrade 실전매매 시스템 전달

---

## 📋 시스템 개요

### 프로젝트 구조
```
strategy-research-lab/
├── freqtrade/
│   ├── config.json                          # Freqtrade 메인 설정
│   └── user_data/
│       └── strategies/
│           ├── SimpleAdaptiveStrategy.py    # 실전 전략 (현재 사용 중)
│           └── AdaptiveMLStrategy.py        # 고급 전략 (백업)
├── deploy_freqtrade_server.sh              # 서버 배포 스크립트
├── start_live_trading.sh                   # 로컬 실행 스크립트
├── setup_live_trading.py                   # 설정 도구
├── test_bitget_connection.py               # API 연결 테스트
├── LIVE_TRADING_SETUP_COMPLETE.md          # 완전한 설정 가이드
└── BITGET_CONNECTION_REPORT.md             # API 연결 리포트
```

---

## 🎯 현재 설정 상태

### 1. 거래소 연결
- **거래소**: Bitget
- **API Key**: `bg_6563f559d91c72bd3a2b2e552a1c9cec`
- **API Secret**: `1db14e0f08b08663d07e60b19af10ecd1ec6f9e162e0cde923dec2770e6b786f`
- **API Password**: `Wnrkswl123`
- **연결 상태**: ✅ 테스트 완료 (1,350개 거래쌍 로드 성공)

### 2. 전략 설정
- **전략명**: `SimpleAdaptiveStrategy`
- **파일 위치**: `freqtrade/user_data/strategies/SimpleAdaptiveStrategy.py`
- **기반**: Adaptive ML Trailing Stop (평균 수익률 111.08%, Sharpe 0.30)
- **타임프레임**: 1시간
- **거래쌍**: BTC/USDT, ETH/USDT, SOL/USDT, XRP/USDT, ADA/USDT

### 3. 리스크 관리
- **거래 모드**: 실전 거래 (dry_run: false)
- **거래당 금액**: 20 USDT
- **최대 동시 거래**: 3개
- **손절**: -3%
- **목표 수익**: 10% (즉시), 5% (1시간), 2% (2시간)
- **트레일링 스톱**: 활성화 (2% 이익 후 1% 트레일링)

### 4. 서버 정보
- **IP**: 141.164.55.245
- **사용자**: root
- **비밀번호**: `[Br76r(6mMDr%?ia`
- **배포 경로**: `/root/freqtrade-live`
- **API 포트**: 8082

---

## 📄 핵심 파일 내용

### 1. Freqtrade 설정 (config.json)

```json
{
    "max_open_trades": 3,
    "stake_currency": "USDT",
    "stake_amount": 20.0,
    "dry_run": false,
    "trading_mode": "spot",
    "user_data_dir": "freqtrade/user_data",
    "exchange": {
        "name": "bitget",
        "key": "bg_6563f559d91c72bd3a2b2e552a1c9cec",
        "secret": "1db14e0f08b08663d07e60b19af10ecd1ec6f9e162e0cde923dec2770e6b786f",
        "password": "Wnrkswl123",
        "ccxt_config": {
            "enableRateLimit": true,
            "rateLimit": 100
        },
        "pair_whitelist": [
            "BTC/USDT",
            "ETH/USDT",
            "SOL/USDT",
            "XRP/USDT",
            "ADA/USDT"
        ]
    },
    "api_server": {
        "enabled": true,
        "listen_ip_address": "0.0.0.0",
        "listen_port": 8081,
        "username": "admin",
        "password": "admin"
    },
    "telegram": {
        "enabled": true,
        "token": "8327452496:AAFwrVohBY-9dVoo8D7mXHqGLEDXMOCJK_M",
        "chat_id": "7980845952"
    }
}
```

### 2. 전략 코드 (SimpleAdaptiveStrategy.py)

**전략 로직:**
```python
# 진입 조건
- EMA(9) > EMA(21)           # 상승 추세
- RSI 40-70                  # 과매수/과매도 회피
- MACD > Signal              # 모멘텀 확인
- Volume > 평균의 50%        # 유동성 확인

# 청산 조건
- EMA 크로스다운             # 하락 전환
- RSI > 75                   # 과매수
- MACD < Signal              # 모멘텀 약화

# 리스크 관리
- 손절: -3%
- 트레일링 스톱: 2% 이익 후 1% 트레일링
```

**전체 코드는 `freqtrade/user_data/strategies/SimpleAdaptiveStrategy.py` 참조**

---

## 🚀 실행 방법

### 로컬 실행
```bash
# 1. 설정 확인
python3 test_bitget_connection.py

# 2. Freqtrade 시작
./start_live_trading.sh

# 또는
freqtrade trade --config freqtrade/config.json --strategy SimpleAdaptiveStrategy
```

### 서버 배포
```bash
# 1. 서버에 배포
./deploy_freqtrade_server.sh

# 2. 서버 접속
ssh root@141.164.55.245

# 3. Freqtrade 시작
cd /root/freqtrade-live
./start_trading.sh

# 4. 상태 확인
./check_status.sh

# 5. 로그 확인
docker-compose logs -f freqtrade

# 6. 중지
./stop_trading.sh
```

---

## 📊 모니터링

### API 대시보드
- **로컬**: http://localhost:8081
- **서버**: http://141.164.55.245:8082
- **인증**: admin / admin

### 주요 엔드포인트
```bash
# 상태 확인
curl http://localhost:8081/api/v1/status

# 잔고 확인
curl http://localhost:8081/api/v1/balance

# 수익 확인
curl http://localhost:8081/api/v1/profit

# 성과 확인
curl http://localhost:8081/api/v1/performance
```

### 로그 확인
```bash
# 로컬
tail -f freqtrade/user_data/logs/freqtrade.log

# 서버 (Docker)
docker-compose logs -f freqtrade
```

---

## 🔧 주요 명령어

### 테스트 및 검증
```bash
# API 연결 테스트
python3 test_bitget_connection.py

# Freqtrade 설정 검증
python3 test_freqtrade_bitget.py

# 전략 목록 확인
freqtrade list-strategies --config freqtrade/config.json

# 백테스트
freqtrade backtesting --config freqtrade/config.json --strategy SimpleAdaptiveStrategy --timerange 20260115-
```

### 데이터 관리
```bash
# 데이터 다운로드
freqtrade download-data \
  --exchange bitget \
  --pairs BTC/USDT ETH/USDT SOL/USDT \
  --timeframe 1h \
  --days 30 \
  --config freqtrade/config.json

# 데이터 확인
freqtrade list-data --config freqtrade/config.json
```

### 긴급 조치
```bash
# 로컬 - 즉시 중단
pkill -f "freqtrade trade"

# 서버 - 즉시 중단
ssh root@141.164.55.245 "cd /root/freqtrade-live && docker-compose down"
```

---

## ⚠️ 중요 주의사항

### 보안
1. **API 키 보안**: 절대 공개하지 말 것
2. **서버 비밀번호**: 정기적으로 변경 권장
3. **출금 권한**: API에서 출금 권한 비활성화 권장
4. **2FA**: Bitget 계정에 2FA 활성화 필수

### 리스크 관리
1. **소액 시작**: 처음에는 거래당 10-20 USDT
2. **정기 모니터링**: 하루 2-3회 성과 확인
3. **손실 한도**: 일일/주간 최대 손실 한도 설정
4. **점진적 증액**: 안정적인 성과 확인 후 증액

### 운영
1. **서버 모니터링**: 서버 상태 정기 확인
2. **로그 확인**: 에러 로그 정기 확인
3. **백업**: 설정 파일 정기 백업
4. **업데이트**: Freqtrade 정기 업데이트

---

## 🐛 문제 해결

### 봇이 거래하지 않는 경우
1. 진입 조건 미충족 (정상)
2. 로그 확인: `tail -f freqtrade/user_data/logs/freqtrade.log`
3. 잔고 부족 확인
4. API 연결 상태 확인

### API 오류
```bash
# 연결 테스트
python3 test_bitget_connection.py

# API 키 확인
cat freqtrade/config.json | grep -A 5 "exchange"
```

### 서버 접속 불가
```bash
# SSH 연결 테스트
ssh -v root@141.164.55.245

# 포트 확인
telnet 141.164.55.245 8082
```

---

## 📚 참고 문서

### 프로젝트 내 문서
1. `LIVE_TRADING_SETUP_COMPLETE.md` - 완전한 설정 가이드
2. `BITGET_CONNECTION_REPORT.md` - API 연결 리포트
3. `freqtrade/README.md` - Freqtrade 기본 가이드

### 외부 리소스
1. [Freqtrade 공식 문서](https://www.freqtrade.io/en/stable/)
2. [Bitget API 문서](https://www.bitget.com/api-doc/common/intro)
3. [CCXT 라이브러리](https://github.com/ccxt/ccxt)

---

## 🔄 다음 작업 제안

### 단기 (1주일)
1. 매일 성과 모니터링
2. 로그 에러 확인
3. 거래 패턴 분석

### 중기 (1개월)
1. 전략 성과 평가
2. 파라미터 최적화 검토
3. 다른 전략 테스트

### 장기 (3개월)
1. 포트폴리오 다각화
2. 자동화 개선
3. 리스크 관리 강화

---

## 💬 Claude에게 전달할 때 사용할 프롬프트

```
안녕하세요! Freqtrade 실전매매 시스템을 인수인계 받았습니다.

현재 상황:
- Bitget 거래소에 연결된 Freqtrade 봇이 실전 거래 중입니다
- 전략: SimpleAdaptiveStrategy (EMA 크로스오버 기반)
- 거래당 금액: 20 USDT, 최대 3개 동시 거래
- 서버: 141.164.55.245 (Docker로 실행 중)

필요한 작업:
[여기에 구체적인 요청 사항 작성]

참고 파일:
- HANDOVER_TO_CLAUDE.md (이 문서)
- freqtrade/config.json (설정)
- freqtrade/user_data/strategies/SimpleAdaptiveStrategy.py (전략)
- LIVE_TRADING_SETUP_COMPLETE.md (상세 가이드)

질문이나 확인이 필요한 사항이 있으면 알려주세요!
```

---

## 📞 긴급 연락처

### Telegram 알림
- **Bot Token**: 8327452496:AAFwrVohBY-9dVoo8D7mXHqGLEDXMOCJK_M
- **Chat ID**: 7980845952

### 서버 접속
```bash
ssh root@141.164.55.245
# 비밀번호: [Br76r(6mMDr%?ia
```

---

## ✅ 체크리스트

인수인계 시 확인할 사항:

- [ ] API 연결 상태 확인
- [ ] 봇 실행 상태 확인
- [ ] 현재 포지션 확인
- [ ] 잔고 확인
- [ ] 최근 거래 내역 확인
- [ ] 로그 에러 확인
- [ ] 서버 접속 가능 확인
- [ ] 모니터링 대시보드 접속 확인
- [ ] 긴급 정지 방법 숙지
- [ ] 백업 파일 위치 확인

---

**작성자**: Kiro AI Assistant  
**최종 업데이트**: 2026-01-20 18:10  
**버전**: 1.0

**⚠️ 이 문서는 민감한 정보(API 키, 비밀번호)를 포함하고 있습니다. 안전하게 보관하세요!**
