# 전략연구소 자동매매 시스템 - 개발자 가이드

> **최종 업데이트**: 2026-01-10
> **작성 목적**: 다음 작업자를 위한 상세 시스템 문서

---

## 1. 프로젝트 개요

### 1.1 시스템 목적
TradingView에서 Pine Script 전략을 자동 수집 → AI 검증 → 백테스트 → 실전 자동매매까지 연결하는 End-to-End 트레이딩 시스템

### 1.2 주요 기능
- **전략 수집**: TradingView에서 Pine Script 전략 자동 크롤링
- **AI 분석**: Claude API로 전략 품질 분석 (A/B/C/D 등급)
- **백테스트**: Binance 데이터로 전략 성과 검증
- **자동매매**: 검증된 전략으로 멀티봇 자동매매

---

## 2. 디렉토리 구조

```
전략연구소/
├── main_trading_system.py      # ★ 메인 자동매매 시스템 (640줄)
├── final_integration.py        # 통합 테스트 스크립트
├── test_connection.py          # 거래소 연결 테스트
├── .env                        # 환경변수 (API 키)
│
├── strategy-research-lab/      # ★ Strategy Research Lab (서버 배포됨)
│   ├── api/                    # FastAPI REST API
│   │   └── main.py             # API 엔드포인트 (/api/strategies, /api/stats)
│   │
│   ├── src/
│   │   ├── scraper/            # TradingView 크롤러
│   │   │   └── tradingview_scraper.py
│   │   │
│   │   ├── converter/          # Pine Script → Python 변환
│   │   │   └── pine_to_python.py
│   │   │
│   │   ├── analyzer/           # AI 전략 분석기
│   │   │   └── strategy_analyzer.py
│   │   │
│   │   ├── backtester/         # 백테스트 엔진
│   │   │   ├── data_collector.py       # Binance OHLCV 수집
│   │   │   ├── strategy_tester.py      # 전략 백테스트
│   │   │   └── production_generator.py # 프로덕션 봇 생성
│   │   │
│   │   ├── storage/            # 데이터베이스
│   │   │   ├── database.py
│   │   │   └── models.py
│   │   │
│   │   └── notification/       # 텔레그램 알림
│   │       └── telegram_bot.py
│   │
│   ├── scripts/                # 자동화 스크립트
│   │   ├── auto_pipeline.py    # 전체 파이프라인
│   │   └── auto_collector_service.py
│   │
│   └── data/
│       ├── strategies.db       # SQLite 전략 DB
│       └── market_data/        # 캐시된 시장 데이터
│
└── trading-agent-system/       # 전략 최적화 에이전트 (별도 시스템)
```

---

## 3. 핵심 파일 상세 설명

### 3.1 main_trading_system.py (메인 자동매매)

**위치**: `/Users/mr.joo/Desktop/전략연구소/main_trading_system.py`

**역할**: AI 검증된 전략으로 Binance에서 자동매매

**주요 클래스**:
```python
# 설정 관리
@dataclass
class Config:
    STRATEGY_API_URL = "http://141.164.55.245/api"  # 서버 API
    SYMBOLS = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT']
    USE_TESTNET = True
    PAPER_TRADING = True  # 페이퍼 트레이딩 모드

# 전략 API 클라이언트
class StrategyFetcher:
    def fetch_verified_strategies()  # B등급 이상 전략 조회
    def get_api_stats()              # 서버 통계

# 거래소 연결
class ExchangeConnector:
    def get_candles()    # OHLCV 데이터
    def get_balance()    # 잔고 조회
    def place_order()    # 주문 (Paper/Real)

# 트레이딩 전략
class TradingStrategy:
    def analyze()        # EMA + RSI 시그널 분석

# 멀티봇 시스템
class MultiBotSystem:
    def run()            # 메인 루프
    def process_symbol() # 심볼별 처리
```

**실행 방법**:
```bash
cd /Users/mr.joo/Desktop/전략연구소
python main_trading_system.py
```

---

### 3.2 data_collector.py (Binance 데이터 수집)

**위치**: `strategy-research-lab/src/backtester/data_collector.py`

**역할**: Binance에서 OHLCV 데이터 수집 및 캐싱

```python
class BinanceDataCollector:
    SUPPORTED_TIMEFRAMES = ["1m", "5m", "15m", "30m", "1h", "4h", "1d", "1w"]

    async def fetch_ohlcv(symbol, timeframe, start_date, end_date)
    def get_cached_data()   # 캐시에서 로드
    def save_to_cache()     # Parquet 형식 저장

# 동기 래퍼
class SyncBinanceDataCollector:
    def fetch_ohlcv()       # asyncio.run() 래핑
```

**참고**: 이전에 Bitget을 사용했으나, 한국 서버 이전 후 Binance로 변경됨. 하위호환을 위해 `BitgetDataCollector = BinanceDataCollector` alias 유지.

---

### 3.3 strategy_tester.py (백테스트 엔진)

**위치**: `strategy-research-lab/src/backtester/strategy_tester.py`

**역할**: Pine Script 변환 후 백테스트 실행

```python
class StrategyTester:
    async def test_strategy(script_id, symbol, timeframe, start_date, end_date)

    # 내부 흐름
    # 1. DB에서 전략 로드
    # 2. Pine Script → Python 변환
    # 3. 시장 데이터 fetch (Binance)
    # 4. 백테스트 실행
    # 5. 결과 저장
```

**백테스트 결과**:
```python
{
    'total_trades': 25,
    'win_rate': 56.0,
    'total_return': 12.5,  # %
    'sharpe_ratio': 1.2,
    'max_drawdown': 8.3,   # %
}
```

---

### 3.4 Strategy Research Lab API

**서버 주소**: `http://141.164.55.245`

**API 엔드포인트**:
| 엔드포인트 | 설명 |
|-----------|------|
| `GET /api/stats` | 전략 통계 (총 52개, 합격 22개) |
| `GET /api/strategies` | 전략 목록 조회 |
| `GET /api/strategies?min_score=70` | 점수 필터링 |
| `GET /api/strategies/{script_id}` | 개별 전략 조회 |

**응답 예시** (`/api/stats`):
```json
{
    "total_strategies": 52,
    "passed_count": 22,
    "avg_score": 68.5,
    "grade_distribution": {"A": 3, "B": 19, "C": 15, "D": 15}
}
```

---

## 4. 시스템 구동 방식

### 4.1 전체 데이터 흐름

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   TradingView   │────▶│  Strategy Lab    │────▶│  Main Trading   │
│  (Pine Script)  │     │  Server (API)    │     │     System      │
└─────────────────┘     └──────────────────┘     └─────────────────┘
        │                       │                        │
        │ 크롤링                │ 검증                   │ 매매
        ▼                       ▼                        ▼
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│    Scraper      │     │   AI Analyzer    │     │    Binance      │
│   + Converter   │     │   + Backtester   │     │   (Paper/Real)  │
└─────────────────┘     └──────────────────┘     └─────────────────┘
```

### 4.2 메인 트레이딩 루프

```python
# main_trading_system.py의 핵심 로직
while True:
    for symbol in ['BTC/USDT', 'ETH/USDT', 'SOL/USDT']:
        # 1. 캔들 데이터 수집
        candles = await exchange.get_candles(symbol, limit=100)

        # 2. EMA/RSI 분석
        signal = strategy.analyze(candles)
        # {'action': 'buy/sell/hold', 'confidence': 0.7, 'reason': '...'}

        # 3. 포지션 관리
        if signal['action'] == 'buy' and no_position:
            await exchange.place_order(symbol, 'buy', amount)

        # 4. TP/SL 체크
        if position and (pnl > take_profit or pnl < -stop_loss):
            await exchange.place_order(symbol, 'sell', position.amount)

    await asyncio.sleep(60)  # 1분 대기
```

### 4.3 Paper Trading vs Real Trading

| 구분 | Paper Trading | Real Trading |
|-----|---------------|--------------|
| 설정 | `PAPER_TRADING=true` | `PAPER_TRADING=false` |
| API | Public API만 사용 | Private API 필요 |
| 잔고 | 가상 $10,000 | 실제 계좌 |
| 주문 | 로컬 시뮬레이션 | 실제 거래소 |

---

## 5. 환경 설정

### 5.1 필수 환경변수 (.env)

```bash
# Strategy Research Lab API
STRATEGY_API_URL=http://141.164.55.245/api

# Telegram 알림
TELEGRAM_BOT_TOKEN=8327452496:AAFwrVohBY-xxx
TELEGRAM_CHAT_ID=7980845952

# Binance API (Paper Trading에서는 불필요)
BINANCE_API_KEY=your_api_key
BINANCE_API_SECRET=your_api_secret

# 트레이딩 모드
USE_TESTNET=true      # Testnet 사용 (false: Mainnet)
PAPER_TRADING=true    # Paper Trading (인증 불필요)
```

### 5.2 의존성 설치

```bash
pip install ccxt pandas numpy aiohttp aiosqlite python-dotenv requests pyarrow
```

### 5.3 Binance API 키 발급

**Testnet (테스트용)**:
- URL: https://testnet.binancefuture.com
- 별도 API 키 발급 필요 (Mainnet과 다름)

**Mainnet (실제 거래)**:
- URL: https://www.binance.com/en/my/settings/api-management
- IP 화이트리스트 권장

---

## 6. 현재 상태 및 알려진 이슈

### 6.1 현재 상태 (2026-01-10)

| 구성요소 | 상태 | 비고 |
|---------|------|------|
| Strategy API | ✅ 정상 | 52개 전략, 22개 합격 |
| Telegram 알림 | ✅ 정상 | 실시간 알림 동작 |
| Paper Trading | ✅ 정상 | Public API로 가격 데이터 수신 |
| Binance Testnet | ⚠️ 미인증 | 유효한 Testnet API 키 필요 |
| Binance Mainnet | ⚠️ 미설정 | 실거래 API 키 필요 |

### 6.2 알려진 이슈

1. **Binance API 키 인증 오류**
   - 현상: `Invalid Api-Key ID` 에러
   - 원인: Testnet API 키가 Mainnet 키와 다름
   - 해결: https://testnet.binancefuture.com 에서 별도 발급
   - 임시조치: `PAPER_TRADING=true`로 Public API만 사용

2. **Bitget → Binance 마이그레이션 완료**
   - 백테스트 데이터 수집: Binance로 변경됨
   - 하위호환: `BitgetDataCollector` alias 유지

---

## 7. 테스트 방법

### 7.1 통합 테스트

```bash
cd /Users/mr.joo/Desktop/전략연구소
python final_integration.py
```

**기대 결과**:
```
1. Strategy Research Lab API ✓
2. 거래소 연결 (Paper Trading) ✓
3. 트레이딩 전략 분석 ✓
4. Telegram 알림 ✓
5. 멀티봇 1사이클 실행 ✓

✓ 모든 테스트 통과! (5/5)
```

### 7.2 연결 테스트

```bash
python test_connection.py
```

---

## 8. 서버 배포 정보

### 8.1 서버 접속

```bash
ssh root@141.164.55.245
# 작업 디렉토리: /root/strategy-research-lab
```

### 8.2 서비스 관리

```bash
# API 서버 재시작
systemctl restart strategy-api

# 로그 확인
journalctl -u strategy-api -f

# Nginx 설정
cat /etc/nginx/sites-enabled/strategy-api
```

### 8.3 API 헬스체크

```bash
curl http://141.164.55.245/api/stats
```

---

## 9. 다음 작업자 가이드

### 9.1 실거래 전환 체크리스트

- [ ] Binance Mainnet API 키 발급 및 테스트
- [ ] `.env`에서 `PAPER_TRADING=false` 설정
- [ ] `.env`에서 `USE_TESTNET=false` 설정
- [ ] 리스크 파라미터 검토 (RISK_PER_TRADE, STOP_LOSS 등)
- [ ] 소액으로 실거래 테스트

### 9.2 개선 가능 항목

1. **전략 다양화**: 현재 EMA+RSI 기본 전략 → API에서 받은 전략 직접 적용
2. **모니터링 대시보드**: Grafana/Prometheus 연동
3. **멀티 거래소**: Bybit, OKX 등 추가
4. **데이터베이스**: PostgreSQL로 마이그레이션

### 9.3 주요 파일 수정 시 주의사항

| 파일 | 주의사항 |
|-----|----------|
| `main_trading_system.py` | `ExchangeConnector._initialize()` Paper/Real 분기 로직 |
| `data_collector.py` | Binance API rate limit (1000 candles/request) |
| `.env` | 절대 Git에 커밋하지 말 것 |

---

## 10. 연락처 및 참조

- **프로젝트 소유자**: mr.joo
- **서버 IP**: 141.164.55.245
- **Strategy Lab API**: http://141.164.55.245/api
- **관련 문서**: `strategy-research-lab/MASTER_GUIDE.md`

---

*이 문서는 Claude Code에 의해 자동 생성되었습니다.*
