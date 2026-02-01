# 🎯 Strategy Research Lab (SRL) Integrated Platform

**전략연구소 통합 트레이딩 플랫폼**은 Freqtrade(추세 매매), Hummingbot(시장 조성), 그리고 AI 기반 시장 분석을 하나의 인터페이스로 통합한 프리미엄 개인 트레이딩 시스템입니다.

---

## 🚀 프로젝트 개요 (Project Overview)

이 프로젝트는 파편화된 암호화폐 트레이딩 도구들을 **Enamel Black / Professional Fintech UI**로 통합하여, 단일 대시보드에서 시장 분석부터 실전 매매까지 원스톱으로 관리할 수 있도록 설계되었습니다.

- **핵심 목표**: 데이터 기반의 객관적 투자 결정 및 자동화된 수익 창출
- **주요 스택**: Python (FastAPI), JavaScript (Vanilla), Docker, SQLite, HuggingFace Transformers
- **현재 상태**: ✅ 운영 중 (Stable) | **버전**: 2.0.0 (Integrated)

---

## 🛠 주요 기능 (Key Features)

### 1. 통합 대시보드 (Integrated Dashboard)
- **URL**: `http://localhost:8080/`
- **특징**: 모든 모듈(Freqtrade, Hummingbot, AI 분석 등)을 직관적인 탭 UI로 관리.
- **디자인**: Sophisticated Dark Theme (반응형, 세로 스크롤 지원, iframe 최적화).

### 2. 트레이딩 엔진 (Trading Engines)
| 엔진 | 역할 | 포트 | 상태 |
| :--- | :--- | :--- | :--- |
| **FreqControl** | 추세 추종 전략 관리 및 실시간 매매 상태 제어 | `8081` | ✅ |
| **FreqBacktest** | 고성능 백테스트 및 전략 검증 환경 | `8082` | ✅ |
| **Hummingbot** | 시장 조성(AMM) 및 차익 거래 실행 (**v2.11.0**) | `8501` | ✅ (Docker) |

### 3. 마켓 인텔리전스 (Market Intelligence)
- **AI Sentiment**: HuggingFace CryptoBERT 모델을 활용한 실시간 뉴스 심성 분석.
- **External Tools**: 
    - **CryptoVision**: 자산 관계망 시각화.
    - **Messari**: 기관급 온체인 데이터.
    - **CryptoPanic**: 실시간 뉴스 피드 애그리게이터.
    - **Perplexity**: AI 기반 금융 리서치.

---

## ⚡ 빠른 시작 (Quick Start)

### 1. 통합 서버 시작 (권장)
대시보드와 API 서버를 실행합니다.

```bash
# 프로젝트 루트에서 실행
cd strategy-research-lab
export APP_BASE_DIR=$(pwd)
python3 api/server.py
```
> 실행 후 브라우저에서 `http://localhost:8080` 접속

### 1-1. 개발 서버 실행 (통합 프론트엔드 전용, 상세 가이드)
다른 작업자가 "종합 프론트엔드"를 가장 확실하게 올릴 수 있는 실행 절차입니다.

```bash
# 0) 프로젝트 루트에서 시작
cd /Users/mr.joo/Desktop/전략연구소/strategy-research-lab

# 1) 최초 1회 의존성 설치 (slowapi 등)
python3 -m pip install -r requirements.txt

# 2) 통합 프론트엔드/DB 경로 지정
export APP_BASE_DIR=$(pwd)

# 3) 개발 서버 실행 (권장: uvicorn)
python3 -m uvicorn api.server:app --host 127.0.0.1 --port 8080
```

운영 확인 포인트:
- 대시보드 URL: `http://127.0.0.1:8080/`
- API 문서: `http://127.0.0.1:8080/api/docs`
- 통합 프론트엔드 파일: `strategy-research-lab/data/integrated_dashboard.html`

자주 발생하는 에러와 해결:
- `ModuleNotFoundError: No module named 'slowapi'`: `requirements.txt` 설치가 빠졌습니다.
- `PermissionError: /app` 또는 DB 초기화 실패: `APP_BASE_DIR` 미설정입니다.
- `Operation not permitted` 바인딩 실패: `--host 127.0.0.1`로 실행하거나 권한이 있는 터미널에서 실행하세요.

실행 로그를 남기려면:
```bash
APP_BASE_DIR=$(pwd) nohup python3 -m uvicorn api.server:app --host 127.0.0.1 --port 8080 > server.log 2>&1 &
```
로그 파일: `strategy-research-lab/server.log`

### 2. Hummingbot 실행 (Docker)
시장 조성 봇은 독립된 Docker 컨테이너로 실행됩니다.

```bash
cd hummingbot
docker compose up -d
# 대시보드 접속: http://localhost:8501
```

### 3. Freqtrade 실행 (Optional)
개별 전략 학습 및 백테스트 실행 시 사용합니다.

```bash
cd freqtrade
source .venv/bin/activate
freqtrade trade --config config.json --strategy MyStrategy
```

---

## 📁 프로젝트 구조 (Project Structure)

```plaintext
/Desktop/전략연구소/
├── README.md                   # 메인 가이드 (This file)
├── strategy-research-lab/      # [Core] 핵심 시스템 코드
│   ├── api/server.py           # FastAPI 백엔드 서버
│   ├── data/                   # 통합 대시보드 HTML 및 데이터
│   ├── templates/              # 개별 템플릿 파일
│   └── src/                    # 분석 및 유틸리티 로직
├── hummingbot/                 # [Bot] Hummingbot v2.11.0 설정 및 Docker
├── freqtrade/                  # [Bot] Freqtrade 전략 및 설정
├── scripts/                    # [Util] 유틸리티 스크립트
└── _archive/                   # 구버전 문서 및 백업
```

---

## 🔒 보안 및 설정 (Security & Config)

- **API 키 관리**: GitHub Push Protection 준수를 위해 소스 코드 내 하드코딩된 API 키는 제거되었습니다. 실제 운영 시 대시보드 내 `Secure Storage` 또는 서버 환경변수(`server.py`)를 통해 주입해야 합니다.
- **환경 변수**:
    - `BINANCE_API_KEY`: 바이낸스 거래 연동
    - `ANTHROPIC_API_KEY`: 심층 분석용 AI (Claude)
- **네트워크**: `localhost` 바인딩을 기본으로 하며, 외부 접속 필요 시 Nginx 리버스 프록시 설정을 권장합니다.

---

## 🔌 API 엔드포인트 요약

**Base URL**: `http://localhost:8080/api`

| Method | Endpoint | 설명 |
| :--- | :--- | :--- |
| `GET` | `/` | 통합 대시보드 페이지 (HTML) |
| `GET` | `/api/stats` | 전체 전략 성과 통계 |
| `GET` | `/api/strategies` | 분석된 전략 리스트 조회 |
| `GET` | `/live` | 실전 매매 모니터링 페이지 |
| `POST` | `/api/emergency-stop` | 긴급 매매 정지 (Key 인증) |

---

## 📝 관리자 노트 (Admin Notes)

- **2026-01-19**: UI 스크롤 개선 및 iframe 스케일링(0.7x) 적용 완료. API 보안 패치 적용.
- **유지보수**: 대시보드 레이아웃 수정은 `data/integrated_dashboard.html` 내 CSS 섹션을 참고하십시오.
- **백업**: 중요한 설정 파일(`config.json`, `conf/`)은 정기적으로 백업하십시오.

---
**Strategy Research Lab** | Created with Antigravity AI
