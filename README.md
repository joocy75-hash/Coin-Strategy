# 🎯 TradingView Strategy Research Lab

**자동화된 Pine Script 전략 수집 → AI 분석 → Python 변환 → 백테스트 → 실전매매 시스템**

> 서버: `141.164.55.245` (Hetzner Cloud) | 테스트: 172개 통과 | 버전: 6.0

---

## 🚀 핵심 기능

| 기능 | 설명 | 상태 |
|------|------|------|
| **전략 수집** | TradingView에서 500+ 부스트 전략 자동 수집 (6시간마다) | ✅ |
| **AI 분석** | Claude API로 리페인팅/과적합 탐지, A~F 등급 부여 | ✅ |
| **Pine → Python** | Rule-based + AI 에이전트 변환 | ✅ |
| **백테스트** | 75개 데이터셋 (25심볼 × 3타임프레임) | ✅ |
| **실전매매** | Binance 연동, 안전장치, 텔레그램 알림 | ✅ |
| **Freqtrade** | FreqAI + 강화학습 통합 (선택) | ✅ |

---

## 📁 프로젝트 구조

```
├── api/                    # FastAPI REST API 서버
├── src/
│   ├── collector/          # TradingView 스크래핑
│   ├── analyzer/           # AI 품질 분석 (Claude, FinBERT, Pine Parser)
│   ├── converter/          # Pine → Python 변환
│   ├── backtester/         # VectorBT 고속 백테스트
│   ├── trading/            # 실전매매 안전장치
│   └── logging/            # 거래 로그
├── freqtrade/              # Freqtrade 통합 (FreqAI + RL)
├── tests/                  # 172개 테스트
├── templates/              # 대시보드 HTML
└── docker-compose.yml      # 배포 설정
```

---

## ⚡ 빠른 시작

### 로컬 개발

```bash
# 1. 의존성 설치
python3.11 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
playwright install chromium

# 2. 환경 변수
cp .env.example .env
# ANTHROPIC_API_KEY 설정

# 3. API 서버 실행
python api/server.py
# → http://localhost:8080/api/docs
```

### 배포 (GitHub Actions 자동)

```bash
git add . && git commit -m "feat: 변경사항" && git push origin main
# → 자동 배포 (5-10분)
```

---

## 🔌 API 엔드포인트

**Base URL**: `http://141.164.55.245/api`

| 엔드포인트 | 설명 |
|-----------|------|
| `GET /health` | 헬스체크 |
| `GET /stats` | 전략 통계 |
| `GET /strategies` | 전략 목록 (필터, 정렬, 페이징) |
| `GET /strategy/{id}` | 전략 상세 |
| `POST /backtest` | 백테스트 실행 |
| `GET /live/status` | 실전매매 상태 |
| `POST /emergency-stop` | 긴급 정지 (인증 필요) |
| `GET /docs` | Swagger 문서 |

---

## 🛡️ 보안 기능

- **API 인증**: Bearer 토큰 (민감한 엔드포인트)
- **Rate Limiting**: 분당 60회 제한
- **CORS**: 허용 도메인 제한
- **API 키 암호화**: 시스템 키체인 활용
- **실전매매 안전장치**: 최대 손실 5%, 긴급 정지, 슬리피지 체크

---

## 🤖 Freqtrade 통합 (선택)

```bash
cd freqtrade
./install_freqtrade.sh  # FreqAI + 강화학습 풀 설치

# 드라이런 테스트
freqtrade trade --config config_freqai.json --strategy FreqAIStrategy --dry-run
```

자세한 내용: [freqtrade/README.md](freqtrade/README.md)

---

## 📊 기술 스택

- **Backend**: Python 3.11, FastAPI, asyncio
- **AI/ML**: Claude 3.5 Sonnet, FinBERT, VectorBT, FreqAI
- **Database**: SQLite, aiosqlite
- **Scraping**: Playwright
- **Infra**: Docker, GitHub Actions, Hetzner Cloud
- **Trading**: ccxt, Binance API

---

## 📄 문서

| 파일 | 설명 |
|------|------|
| `README.md` | 이 파일 (메인 문서) |
| `ARCHITECTURE.md` | 시스템 아키텍처 다이어그램 |
| `UPGRADE_SECURITY_PLAN.md` | 보안 업그레이드 체크리스트 |
| `freqtrade/README.md` | Freqtrade 사용 가이드 |

---

## 🔧 서버 관리

```bash
# SSH 접속
ssh root@141.164.55.245

# 컨테이너 상태
docker compose ps

# 로그 확인
docker compose logs -f scheduler

# 재시작
docker compose restart
```

---

**마지막 업데이트**: 2026-01-13 | **테스트**: 172개 통과 | **상태**: ✅ 운영 중
