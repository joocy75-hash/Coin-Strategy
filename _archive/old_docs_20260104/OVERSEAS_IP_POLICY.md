# 해외 IP 백테스트 및 자동화 운영 정책

**작성일**: 2026-01-04
**작성자**: Strategy Research Lab
**버전**: 1.0

---

## 📋 요약

**결론**: 현재 전략연구소 시스템은 **해외 IP에서 완전히 안전하게 운영 가능**합니다.

| 활동 | 해외 IP 사용 | 제약사항 | 권장사항 |
|------|------------|---------|----------|
| **백테스트** | ✅ 완전 안전 | 없음 | 로컬 데이터 사용 |
| **데이터 수집** (완료) | ✅ 완전 안전 | 없음 | 이미 75개 수집 완료 |
| **TradingView 추가 수집** | ✅ 안전 | Rate Limit 주의 | VPS(독일) 권장 |
| **Binance API (Testnet)** | ✅ 완전 안전 | 없음 | 전 세계 사용 가능 |
| **Binance API (Mainnet)** | ✅ 안전 | KYC 필요 | 한국 IP는 VPN 필요 |
| **실전 거래** | ✅ 안전 | 세금 신고 | API 키만 있으면 OK |

---

## 1. 백테스트 (Backtesting)

### ✅ 완전 안전 - IP 무관

**이유**:
- 백테스트는 **로컬에 저장된 데이터**를 사용
- 외부 API 호출 없음
- 네트워크 연결 불필요
- 순수 계산 작업

**현재 환경**:
```
데이터 위치: /Users/mr.joo/Desktop/전략연구소/trading-agent-system/data/datasets/
데이터 개수: 75개 (25 심볼 × 3 타임프레임)
데이터 기간: 2023-01-01 ~ 2026-01-03 (약 3년치)
총 용량: ~100MB (Parquet 압축)
```

**사용 장소**:
- ✅ 로컬 Mac (현재 환경)
- ✅ 해외 VPS (독일 서버)
- ✅ 회사 네트워크
- ✅ 카페 WiFi
- ✅ **어디서든 가능**

---

## 2. 데이터 수집

### 2.1 TradingView Pine Script 수집

**현재 상황**:
- ✅ 86개 전략 이미 수집 완료 (서버: 5.161.112.248)
- ✅ 63개 Pine Script 코드 보유
- ✅ 데이터베이스 저장 완료

**추가 수집 시**:
| 방법 | 안전성 | 제약사항 |
|------|--------|---------|
| 로컬 Mac (한국 IP) | ✅ 안전 | Rate Limit 주의 (1000 req/day) |
| VPS (독일 IP) | ✅ 더 안전 | 제약 없음 |

**TradingView 정책**:
- 국가별 IP 차단 없음
- Rate Limiting만 존재 (요청 사이 0.5초 대기)
- Playwright로 스크래핑 시 User-Agent 설정 필요
- 과도한 요청 시 일시적 차단 (24시간 후 해제)

**권장 설정**:
```python
# session_manager.py
DELAY_BETWEEN_REQUESTS = 0.5  # 초
MAX_RETRIES = 3
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0"
```

---

### 2.2 Binance 히스토리컬 데이터 수집

**현재 상황**:
- ✅ 75개 데이터셋 이미 수집 완료
- ✅ 3년치 OHLCV 데이터 보유
- ✅ Parquet 파일로 저장

**추가 수집 시**:
| API | 해외 IP | 한국 IP | 제약사항 |
|-----|---------|---------|---------|
| Binance Public API | ✅ 완전 안전 | ✅ 안전 | Rate Limit: 1200 req/min |
| Binance Websocket | ✅ 완전 안전 | ✅ 안전 | 없음 |

**Binance 공식 정책**:
- 히스토리컬 데이터 API는 **전 세계 제한 없음**
- API 키 불필요 (Public Endpoint)
- 국가별 차단 없음
- Rate Limit만 준수하면 OK

**코드 예시**:
```python
import ccxt

exchange = ccxt.binance({
    'enableRateLimit': True,  # 자동 Rate Limiting
})

# Public API - API 키 없이 사용 가능
ohlcv = exchange.fetch_ohlcv('BTC/USDT', '1h')
```

---

## 3. Binance API 사용 (Trading)

### 3.1 Testnet (Paper Trading)

**정책**: ✅ **전 세계 제한 없음**

| 항목 | 설명 |
|------|------|
| URL | https://testnet.binancefuture.com/ |
| 계정 | 이메일로 즉시 생성 가능 |
| API 키 | 무료 발급 |
| IP 제한 | 없음 (선택적 IP 화이트리스트 설정 가능) |
| 사용 국가 | 전 세계 어디서나 가능 |
| VPN 필요 | 불필요 |

**현재 서버 (5.161.112.248, 독일)**:
- ✅ Testnet 사용 가능
- ✅ 제약 없음

---

### 3.2 Mainnet (Real Trading)

**정책**: ✅ **안전하나 한국 IP는 주의**

| 항목 | 한국 IP | 해외 IP (VPS) |
|------|---------|--------------|
| 웹사이트 접속 | ❌ 차단 (binance.com) | ✅ 가능 |
| API 접속 | ✅ **가능** | ✅ 가능 |
| 거래 실행 | ✅ **가능** | ✅ 가능 |
| 출금 | ✅ **가능** | ✅ 가능 |
| VPN 필요 | 웹 접속 시만 | 불필요 |

**중요 사실**:
```
❌ 잘못된 정보: "한국에서 Binance 사용 불가"
✅ 실제 상황: 웹사이트는 차단, API는 정상 작동

한국 IP에서도 API를 통한 자동 거래는 완전히 가능!
```

**KYC (본인인증)**:
- Mainnet 사용 시 필수
- 여권 또는 신분증 필요
- 한국인도 인증 가능
- 인증 후 일일 출금 한도 증가

**API 접속 방법**:
```python
# 한국 IP에서도 API는 정상 작동
import ccxt

exchange = ccxt.binance({
    'apiKey': 'YOUR_API_KEY',
    'secret': 'YOUR_SECRET',
    'enableRateLimit': True,
})

# 잔고 조회 - 한국 IP에서도 OK
balance = exchange.fetch_balance()
print(f"USDT: {balance['USDT']['free']}")

# 주문 실행 - 한국 IP에서도 OK
order = exchange.create_limit_buy_order('BTC/USDT', 0.01, 26000)
```

**IP 화이트리스트 설정 (권장)**:
```
Binance 계정 설정:
1. API Management 메뉴
2. IP Access Restrictions 활성화
3. 서버 IP (5.161.112.248) 추가
4. 보안 강화 ✅
```

---

## 4. 자동 거래 시스템 운영

### 4.1 현재 서버 (5.161.112.248)

| 항목 | 값 | 상태 |
|------|-----|------|
| 위치 | 독일 (Hetzner) | ✅ |
| IP | 5.161.112.248 | ✅ |
| OS | Ubuntu 22.04 | ✅ |
| Docker | 설치됨 | ✅ |
| API 서버 | 포트 8081 | ✅ 실행 중 |

**장점**:
- ✅ Binance 제약 없음
- ✅ TradingView 제약 없음
- ✅ 24/7 무인 운영 가능
- ✅ 낮은 지연시간 (유럽 거래소 접근)

### 4.2 자동 거래 Bot 배포 시

**Phase 0 (준비)**:
```bash
# 1. Binance Testnet API 키 발급
# 2. .env 파일 설정
BINANCE_TESTNET_API_KEY=your_key
BINANCE_TESTNET_API_SECRET=your_secret

# 3. Docker로 배포
docker-compose up -d trading-bot
```

**Phase 1 (Testnet 검증)**:
- 기간: 1-2주
- 자본: 가상 자본 (무제한)
- 리스크: 0 (실제 돈 아님)
- 목적: 전략 검증 및 버그 발견

**Phase 2 (Paper Trading)**:
- 기간: 1-2주
- 자본: 가상 자본
- 데이터: Mainnet 실시간 가격
- 목적: 실전 환경 시뮬레이션

**Phase 3 (Real Trading - 소액)**:
- 기간: 1개월
- 자본: $100-500 (테스트용)
- 리스크: 제한적
- 목적: 실전 성과 검증

---

## 5. 법적/세금 고려사항

### 5.1 해외 거래소 수익

| 항목 | 설명 |
|------|------|
| **소득 분류** | 기타소득 (국세청 기준) |
| **세율** | 22% (소득세 20% + 주민세 2%) |
| **신고 의무** | 연간 수익 250만원 초과 시 |
| **신고 시기** | 다음 해 5월 (종합소득세 신고) |
| **증빙 자료** | 거래 내역서 (Binance에서 다운로드) |

**중요**:
```
해외 VPS에서 자동 거래 → 한국 거주자 → 한국에 세금 신고 필요
IP 위치는 무관, 거주자 여부가 중요!
```

### 5.2 출금 시 주의사항

| 금액 | 신고 의무 |
|------|----------|
| 1만 달러 미만 | 신고 불필요 |
| 1만 달러 이상 | 외환 신고 필요 |
| 3만 달러 이상 | 국세청 자동 통보 |

**권장 방법**:
1. Binance → 한국 거래소 (Upbit, Bithumb)
2. 한국 거래소 → 원화 출금
3. 자동으로 소득 추적됨

---

## 6. 현재 시스템의 IP 의존성 분석

### 완전 독립적 (IP 무관)

✅ **백테스트 엔진**
- 로컬 데이터 사용
- 네트워크 불필요

✅ **전략 분석 (Claude API)**
- Anthropic API는 전 세계 사용 가능
- IP 제한 없음

✅ **데이터 저장 (SQLite)**
- 로컬 파일 시스템
- IP 무관

### 외부 의존성 (제한 없음)

✅ **TradingView 스크래핑**
- Rate Limiting만 존재
- IP 차단 없음

✅ **Binance Public API**
- 전 세계 사용 가능
- Rate Limiting만 존재

✅ **Binance Private API (Testnet)**
- 전 세계 사용 가능
- 제한 없음

⚠️ **Binance Private API (Mainnet)**
- 한국 IP: 웹 차단, API 정상
- 해외 IP: 모두 정상

---

## 7. 권장 운영 방식

### 개발 단계 (현재)

```
로컬 Mac (한국):
├── 백테스트 개발 ✅
├── 전략 최적화 ✅
├── 데이터 분석 ✅
└── 코드 작성 ✅

해외 VPS (독일):
├── 데이터 수집 ✅
├── API 서버 운영 ✅
├── 스케줄러 실행 ✅
└── 웹 대시보드 ✅
```

### 자동 거래 단계 (향후)

```
Phase 1-2 (Testnet/Paper):
└── 어디서든 가능 (IP 무관)

Phase 3 (Real Trading):
├── Option A: 로컬 Mac (한국)
│   ├── API 정상 작동 ✅
│   ├── 웹 접속 시 VPN 필요
│   └── 세금 신고 필요
│
└── Option B: 해외 VPS (독일) ⭐ 권장
    ├── 모든 제약 없음 ✅
    ├── 24/7 무인 운영
    ├── 낮은 지연시간
    └── 세금 신고 필요 (한국 거주자)
```

---

## 8. 최종 결론

### ✅ 현재 환경에서 모든 작업 가능

| 작업 | 로컬 (한국) | VPS (독일) | 권장 |
|------|-----------|----------|------|
| 백테스트 | ✅ | ✅ | 로컬 |
| 최적화 | ✅ | ✅ | 로컬 (빠른 CPU) |
| 데이터 수집 | ✅ | ✅ | VPS (24/7) |
| Testnet 거래 | ✅ | ✅ | 어디든 |
| Mainnet 거래 | ✅ (API만) | ✅ | VPS |

### 🚀 즉시 실행 가능한 작업

1. ✅ **Moon Dev 최적화** (로컬에서 실행 중)
2. ✅ **C등급 Batch 처리** (로컬에서 가능)
3. ✅ **Testnet 거래 시작** (어디서든 가능)
4. ✅ **VPS에 배포** (이미 구축됨)

### ⚠️ 주의사항

1. **Rate Limiting 준수**
   - TradingView: 요청 사이 0.5초
   - Binance: ccxt의 enableRateLimit=True 사용

2. **세금 신고**
   - 연간 수익 250만원 초과 시 신고
   - 해외 거래소도 한국 거주자는 신고 의무

3. **API 키 보안**
   - .env 파일 사용
   - Git에 커밋 금지
   - IP 화이트리스트 설정 권장

---

## 9. FAQ

**Q: 한국에서 Binance 자동 거래 불법인가요?**
A: 아닙니다. 웹사이트 접속만 차단되고, API는 정상 작동합니다. 자동 거래 완전히 합법입니다.

**Q: 해외 VPS 사용 시 추가 세금이 있나요?**
A: 없습니다. 한국 거주자는 전 세계 어디서 거래하든 한국에 신고하면 됩니다.

**Q: VPN 사용 필요한가요?**
A: 한국에서 Binance 웹 접속 시만 필요. API 사용 시 불필요.

**Q: 백테스트 결과가 IP에 따라 달라지나요?**
A: 절대 아닙니다. 로컬 데이터를 사용하므로 완전히 동일합니다.

**Q: 현재 서버(독일)에서 모든 작업 가능한가요?**
A: 네, 100% 가능합니다. 어떤 제약도 없습니다.

---

**결론**: 현재 시스템은 해외 IP로 완벽하게 작동하며, 백테스트부터 실전 거래까지 모든 단계에서 제약이 없습니다. 독일 VPS는 오히려 더 유리한 환경을 제공합니다.

**작성일**: 2026-01-04
**다음 업데이트**: 실전 거래 시작 시
