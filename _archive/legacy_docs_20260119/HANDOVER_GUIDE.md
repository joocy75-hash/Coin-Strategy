# 📋 전략연구소 통합 트레이딩 플랫폼 인수인계 가이드 (Handover Guide)

이 문서는 **전략연구소 프로젝트**의 주요 기능, 아키텍처, 설정 방법 및 유지보수 가이드를 포함한 최종 인수인계 자료입니다.

---

## 1. 프로젝트 개요
본 프로젝트는 **Freqtrade(추세 매매)**와 **Hummingbot(시장 조성/차익 거래)**을 결합하고, **AI 기반 시장 감성 분석** 및 **전문 분석 도구**를 하나로 통합한 프리미엄 개인 트레이딩 랩 구축을 목표로 합니다.

- **디자인 컨셉**: Enamel Black 테마 (Sophisticated, Professional Fintech UI)
- **주요 스택**: Python (FastAPI), JavaScript (Vanilla), Docker, Freqtrade, Hummingbot

---

## 2. 주요 통합 기능 리스트

### ① 통합 대시보드 (Integrated Dashboard)
- 모든 기능을 하나의 단일 페이지(`integrated_dashboard.html`)에서 관리.
- 글로벌 내비게이션 바를 통한 쾌적한 탭 전환.
- 실시간 시스템 상태 모니터링 및 심장박동(Heartbeat) 체크.

### ② 마켓 인텔리전스 (Market Intelligence)
- **AI Sentiment**: HuggingFace CryptoBERT를 통한 실시간 시장 심리 지수 분석.
- **Macro News**: Brave Search & Playwright를 이용한 실시간 주요 경제 뉴스 수집.

### ③ 외부 전문 분석 도구 (External Intelligence)
- **CryptoVision**: HuggingFace 기반 가상자산 관계망 시각화.
- **Messari**: 프로페셔널 등급의 온체인 데이터 스크리너 연동.
- **CryptoPanic**: 고영향 뉴스 데이터 (제공된 API 키를 통한 실시간 피드 연동).
- **Perplexity Finance**: 최신 AI 검색 기반 금융 시장 브리핑.

### ④ 트레이딩 엔진 (Trading Engines)
- **FreqControl**: 실시간 매매 상태 및 전략 제어.
- **FreqBacktest**: 독립된 고성능 백테스트 분석 환경.
- **Hummingbot**: AMM(시장 조성) 및 차익 거래를 위한 최신 엔진(**v2.11.0** - 2025.12 Latest) 연동.

---

## 3. 시스템 아키텍처 및 포트 구성

| 구성 요소 | 포트 | 비고 |
| :--- | :--- | :--- |
| **Main Dashboard/API** | `8080` | 프로젝트의 핵심 진입점 및 백엔드 서버 |
| **FreqControl (Live)** | `8081` | 실전 매매 로봇 제어 UI |
| **FreqBacktest** | `8082` | 백테스트 분석 및 전략 검증 UI |
| **Hummingbot Dashboard**| `8501` | AMM/Arb 전략 관리 UI (Docker) |
| **Hummingbot Gateway** | `15888` | DEX 미들웨어 (Uniswap, PancakeSwap 등) |

---

## 4. 보안 및 API 키 관리

모든 중요 키는 대시보드 소스 내 보안 스토리지(`externalApiStorage`) 및 서버 환경변수로 관리됩니다.

- **CryptoPanic API Key**: `82c...8fb` (활성화됨)
- **Perplexity API Key**: `pplx-...` (연동 준비 완료)
- **Messari Key**: `FKEB...` (연동 완료)
- **Binance API**: 환경변수(`BINANCE_API_KEY`)를 통해 서버단에서 처리.

---

## 5. 설치 및 시작 가이드

### ① 대시보드 서버 시작
```bash
# strategy-research-lab 디렉토리에서 실행
APP_BASE_DIR=$(pwd) python api/server.py
```

### ② Hummingbot v2.11.0 설치 및 실행 (✅ 설치 완료)
본 프로젝트는 Hummingbot v2.11.0 (최신 버전)이 Docker로 설치되어 있습니다.

```bash
# Docker Desktop이 실행 중인지 확인
# PATH 설정 (필요시)
export PATH="/Applications/Docker.app/Contents/Resources/bin:$PATH"

# Hummingbot 디렉토리로 이동
cd hummingbot

# 서비스 시작
docker compose up -d

# Hummingbot CLI 연결
docker attach hummingbot
# (분리: Ctrl+P, Ctrl+Q)

# 로그 확인
docker logs -f hummingbot

# 서비스 중지
docker compose down
```

**설치된 서비스:**

- `hummingbot`: 메인 트레이딩 봇
- `hummingbot-gateway`: DEX 연동 미들웨어 (Port 15888)
- `hummingbot-dashboard`: 웹 UI (Port 8501)

### ③ Freqtrade 관리
- `freqtrade/` 디렉토리 내의 `config.json`을 통해 전략과 연동된 거래소를 설정할 수 있습니다.

---

## 6. 향후 유지보수 참고사항
- **디자인 유지**: `integrated_dashboard.html`의 CSS 변수(`--bg-deep`, `--accent-primary` 등)를 수정하여 테마를 일관성 있게 관리하세요.
- **보안 강화**: 실제 운영 시에는 `UPGRADE_SECURITY_PLAN.md`에 기술된 리버스 프록시(Nginx)와 SSL 설정을 권장합니다.
- **뉴스 크롤링**: `api/server.py`의 `/api/intelligence/news` 엔드포인트에서 Playwright 로직을 추가하여 뉴스 수집원을 확장할 수 있습니다.

---
**최종 작성일**: 2026-01-19
**담당 AI**: Antigravity (Google Deepmind Labs)
