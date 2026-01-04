# 🎯 TradingView Strategy Research Lab - 완전 가이드

**최종 업데이트**: 2026-01-04 21:20 KST
**프로젝트 상태**: ✅ 운영 중 (Phase 1-3 완료, Phase 4 진행 예정)
**서버 상태**: ✅ 정상 작동 (44개 전략 수집/분석 완료)

---

## ⚠️ **필독: 작업 시작 전 반드시 읽기**

### 🚨 코드 수정 시 절대 규칙

**❌ 절대 하지 말아야 할 것**:
1. ❌ 원격서버에 직접 SSH 접속하여 코드 수정
2. ❌ Docker 컨테이너 내부에서 파일 수정
3. ❌ 로컬과 원격서버의 코드가 다른 상태로 방치
4. ❌ Git 커밋 없이 코드 수정

**✅ 반드시 따라야 할 절차**:
1. ✅ **로컬에서만** 코드 수정
2. ✅ Git 커밋 후 GitHub에 푸시
3. ✅ GitHub Actions가 자동으로 배포하도록 대기
4. ✅ 배포 완료 후 원격서버에서 동작 확인

### 📋 코드 수정 워크플로우

```bash
# Step 1: 로컬에서 코드 수정
cd /Users/mr.joo/Desktop/전략연구소/strategy-research-lab
# (코드 수정 작업)

# Step 2: 변경사항 확인
git status
git diff

# Step 3: Git 커밋
git add .
git commit -m "feat: [수정 내용을 명확히 기술]"

# Step 4: GitHub에 푸시
git push origin main

# Step 5: GitHub Actions 워크플로우 확인 (5-10분 소요)
gh run list --limit 1
# 또는 브라우저에서: https://github.com/joocy75-hash/TradingView-Strategy/actions

# Step 6: 배포 완료 후 원격서버 확인
curl http://5.161.112.248:8081/api/health
curl http://5.161.112.248:8081/api/stats

# Step 7: (선택) 원격서버 로그 확인
ssh root@5.161.112.248
docker compose -f /root/service_c/strategy-research-lab/docker-compose.yml logs -f
```

---

## 📋 목차

1. [프로젝트 개요](#프로젝트-개요)
2. [시스템 아키텍처](#시스템-아키텍처)
3. [현재 상태 (2026-01-04)](#현재-상태-2026-01-04)
4. [디렉토리 구조](#디렉토리-구조)
5. [기술 스택](#기술-스택)
6. [로컬 개발 환경 설정](#로컬-개발-환경-설정)
7. [배포 서버 정보](#배포-서버-정보)
8. [API 문서](#api-문서)
9. [데이터베이스 스키마](#데이터베이스-스키마)
10. [주요 컴포넌트 상세](#주요-컴포넌트-상세)
11. [배포 가이드](#배포-가이드)
12. [트러블슈팅](#트러블슈팅)
13. [작업 로드맵](#작업-로드맵)
14. [FAQ](#faq)

---

## 프로젝트 개요

### 🎯 목적

TradingView에서 Pine Script 전략을 **자동으로 수집** → **AI 기반 분석** → **Python 변환** → **백테스트**하여 **실전 투자 가능한 전략만 선별**하는 완전 자동화 시스템

### ✨ 핵심 가치

- **완전 자동화**: 6시간마다 자동 수집 및 분석
- **AI 기반 품질 평가**: Claude API로 Repainting, Overfitting, Risk 분석
- **대규모 백테스트**: 75개 데이터셋으로 검증
- **실전 검증**: Stop Loss/Take Profit 자동 추가

### 📊 현재 성과 (2026-01-04)

| 지표 | 수치 | 상태 |
|------|------|------|
| **수집 전략 수** | 44개 | ✅ 자동 수집 완료 |
| **분석 완료** | 44개 (100%) | ✅ AI 분석 완료 |
| **평균 점수** | 63.9점 (C등급) | 🟡 개선 여지 있음 |
| **합격 전략** | 15개 (34%) | ✅ Pass 기준 통과 |
| **최고 등급** | B등급 1개 | 🟢 우수 전략 발견 |
| **서버 가동률** | 100% | ✅ Docker 자동 재시작 |

### 🏆 TOP 3 전략

1. **Next Candle Predictor** (76.0점, B등급)
   - 좋아요: 2,200개
   - Repainting: 100.0점 (안전)
   - Overfitting: 80.0점 (양호)

2. **Candle 2 Closure [LuxAlgo]** (64.0점, C등급)
   - 좋아요: 2,200개
   - Repainting: 90.0점
   - Overfitting: 80.0점

3. **Swing Failure Signals [AlgoAlpha]** (64.0점, C등급)
   - 좋아요: 1,900개
   - Repainting: 90.0점
   - Overfitting: 80.0점

---

## 시스템 아키텍처

### 전체 파이프라인

```
┌─────────────────────────────────────────────────────────────┐
│                    TradingView (데이터 소스)                   │
│              https://www.tradingview.com/scripts/            │
└────────────────────────┬────────────────────────────────────┘
                         │ Playwright 스크래핑 (Chromium)
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   1️⃣ 전략 수집기 (Collector)                  │
│  • scripts_scraper.py: 500+ 부스트 전략 필터링                 │
│  • pine_fetcher.py: Pine Script 코드 추출                     │
│  • performance_parser.py: 백테스트 성과 파싱                   │
│  → 출력: strategies.db (SQLite)                               │
└────────────────────────┬────────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                  2️⃣ AI 품질 분석기 (Analyzer)                 │
│  • repainting_detector.py: 미래 데이터 참조 탐지                │
│  • overfitting_detector.py: 과적합 탐지                       │
│  • risk_checker.py: SL/TP 체크                               │
│  • deep_analyzer.py: Claude API 심층 분석                    │
│  • scorer.py: 통합 점수 산출 (A~F 등급)                        │
│  → 출력: 분석 결과 (total_score, grade)                       │
└────────────────────────┬────────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                3️⃣ Pine → Python 변환기 (Converter)            │
│  • rule_based_converter.py: 기본 패턴 매칭                     │
│  • llm_converter.py: AI 기반 복잡한 로직 변환 (Phase 4 예정)    │
│  → 출력: Python 클래스 (backtesting.py 호환)                   │
└────────────────────────┬────────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                 4️⃣ 백테스트 엔진 (Backtest Engine)            │
│  • 75개 데이터셋 (25 심볼 × 3 타임프레임)                        │
│  • 병렬 실행 (멀티프로세싱)                                      │
│  • 고급 지표: Sharpe Ratio, Profit Factor, Max Drawdown      │
│  → 출력: BacktestResult (HTML/JSON)                          │
└────────────────────────┬────────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    5️⃣ 결과 리포트 (Reporter)                  │
│  • HTML 대시보드 (초보자/전문가용)                              │
│  • REST API (FastAPI)                                       │
│  • 텔레그램 알림 (옵션)                                         │
│  → URL: http://5.161.112.248:8081/                          │
└─────────────────────────────────────────────────────────────┘
```

### 자동화 스케줄

```
00:00 ─┬─ 수집 사이클 #1 (0시)
       │   ├─ 수집 (30-60분)
       │   ├─ 분석 (10-20분)
       │   └─ 리포트 생성 (5분)
       │
06:00 ─┼─ 수집 사이클 #2 (6시)
       │
12:00 ─┼─ 수집 사이클 #3 (12시)
       │
18:00 ─┴─ 수집 사이클 #4 (18시)

📊 일일 총 수집: ~120-200개 전략
```

---

## 현재 상태 (2026-01-04)

### ✅ 완료된 마일스톤

| 마일스톤 | 상태 | 완료율 | 주요 내용 |
|---------|------|--------|----------|
| **Phase 1**: 기본 파이프라인 | ✅ | 100% | 수집 → 분석 → 변환 |
| **Phase 2**: AI 에이전트 시스템 | ✅ | 100% | 4개 전문 에이전트 |
| **Phase 3**: 백테스트 인프라 | ✅ | 100% | 23개 지표 + 엔진 |
| **Phase 4**: LLM 변환기 | 🚧 | 0% | 계획 수립 완료 |

### 🚀 실시간 상태

**서버**: http://5.161.112.248:8081
- ✅ API 서버: Healthy (응답 시간 <100ms)
- ✅ 스케줄러: Running (현재 수집 진행 중)
- ✅ 데이터베이스: 1.5MB (44개 전략)

**최근 수집 활동** (실시간):
```
21:15:07 | 📈 페이지 15: 총 9개 수집 (+4)
21:14:54 | 📈 페이지 14: 총 5개 수집 (+0)
21:14:43 | 📈 페이지 13: 총 5개 수집 (+0)
21:14:30 | 📈 페이지 12: 총 5개 수집 (+2)
```

### 📊 데이터베이스 통계

```sql
-- 전체 전략 수
SELECT COUNT(*) FROM strategies;
-- 결과: 44

-- 등급별 분포
SELECT grade, COUNT(*) FROM strategies GROUP BY grade;
-- B: 1개 (2.3%)
-- C: 43개 (97.7%)

-- 평균 점수
SELECT AVG(total_score) FROM strategies;
-- 결과: 63.9점

-- 합격 전략 (Pass)
SELECT COUNT(*) FROM strategies WHERE total_score >= 60;
-- 결과: 15개 (34%)
```

---

## 디렉토리 구조

### 전체 프로젝트 구조

```
/Users/mr.joo/Desktop/전략연구소/
│
├── 📘 MASTER_GUIDE.md                    # ⭐ 이 파일 (통합 가이드)
├── 📘 README.md                          # 프로젝트 소개 (GitHub용)
├── 📘 IMPLEMENTATION_ROADMAP.md          # Phase 4 로드맵
├── 📘 SERVER_HEALTH_CHECK_20260104.md    # 서버 상태 보고서
├── 📘 COMPLETION_REPORT_20260104.md      # 작업 완료 보고서
│
├── .claude/                              # Claude Code 설정
│   └── skills/                           # 모듈별 Skill 가이드
│       ├── README.md                     # Skill 인덱스
│       ├── collector_guide.md            # 수집 모듈 가이드
│       ├── analyzer_guide.md             # 분석 모듈 가이드
│       ├── converter_guide.md            # 변환 모듈 가이드
│       ├── agent_guide.md                # AI 에이전트 가이드
│       ├── backtest_guide.md             # 백테스트 가이드
│       ├── pipeline_guide.md             # 파이프라인 가이드
│       └── deployment_guide.md           # 배포 가이드
│
├── strategy-research-lab/               # 🔥 메인 프로젝트
│   │
│   ├── 📁 src/                          # 소스 코드
│   │   ├── collector/                   # 수집 모듈
│   │   │   ├── scripts_scraper.py       # TradingView 스크래핑
│   │   │   ├── pine_fetcher.py          # Pine Script 추출
│   │   │   ├── performance_parser.py    # 성과 지표 파싱
│   │   │   └── session_manager.py       # 세션 관리
│   │   │
│   │   ├── analyzer/                    # 분석 모듈
│   │   │   ├── repainting_detector.py   # Repainting 탐지
│   │   │   ├── overfitting_detector.py  # Overfitting 탐지
│   │   │   ├── risk_checker.py          # 리스크 체크
│   │   │   ├── deep_analyzer.py         # Claude API 분석
│   │   │   └── scorer.py                # 점수 산출
│   │   │
│   │   ├── converter/                   # 변환 모듈
│   │   │   ├── rule_based_converter.py  # 규칙 기반 변환
│   │   │   ├── ast_parser.py            # AST 파싱
│   │   │   ├── code_generator.py        # 코드 생성
│   │   │   └── indicator_mapper.py      # 지표 매핑
│   │   │
│   │   ├── backtester/                  # 백테스트 모듈
│   │   │   ├── backtest_engine.py       # 엔진
│   │   │   ├── data_provider.py         # 데이터 제공
│   │   │   └── performance_metrics.py   # 성과 지표
│   │   │
│   │   ├── storage/                     # 저장 모듈
│   │   │   ├── database.py              # SQLite 관리
│   │   │   └── models.py                # 데이터 모델
│   │   │
│   │   └── notification/                # 알림 모듈
│   │       └── telegram_bot.py          # 텔레그램 봇
│   │
│   ├── 📁 api/                          # REST API
│   │   └── server.py                    # FastAPI 서버
│   │
│   ├── 📁 scripts/                      # 실행 스크립트
│   │   └── auto_collector_service.py    # 자동 수집 스크립트
│   │
│   ├── 📁 data/                         # 데이터 저장
│   │   ├── strategies.db                # SQLite 데이터베이스
│   │   ├── beginner_report.html         # 초보자 대시보드
│   │   ├── converted/                   # 변환된 Python 코드
│   │   └── reports/                     # 백테스트 리포트
│   │
│   ├── 📁 tests/                        # 테스트 코드
│   │   ├── test_collector.py
│   │   ├── test_analyzer.py
│   │   └── test_converter.py
│   │
│   ├── 📁 .github/                      # GitHub Actions
│   │   └── workflows/
│   │       └── deploy.yml               # 자동 배포 워크플로우
│   │
│   ├── 📄 main.py                       # 메인 실행 파일
│   ├── 📄 Dockerfile                    # Docker 이미지 정의
│   ├── 📄 docker-compose.yml            # Docker Compose 설정
│   ├── 📄 requirements.txt              # Python 의존성
│   ├── 📄 .env                          # 환경 변수 (비공개)
│   └── 📄 .env.example                  # 환경 변수 템플릿
│
└── trading-agent-system/               # AI 에이전트 시스템
    ├── src/
    │   ├── agents/                     # 4개 AI 에이전트
    │   │   ├── strategy_architect.py   # Pine → Python 변환
    │   │   ├── variation_generator.py  # 전략 변형 생성
    │   │   ├── backtest_runner.py      # 다중 백테스트
    │   │   └── result_analyzer.py      # 결과 분석
    │   │
    │   ├── indicators/                 # 23개 기술 지표
    │   ├── backtest/                   # 백테스트 엔진
    │   ├── data/                       # 데이터 수집기
    │   └── orchestrator/               # 파이프라인 자동화
    │
    ├── data/datasets/                  # 75개 백테스트 데이터셋
    ├── main.py
    └── requirements.txt
```

### 핵심 파일 설명

| 파일 | 용도 | 중요도 |
|------|------|--------|
| `main.py` | 단일 수집 실행 (테스트용) | ⭐⭐⭐ |
| `scripts/auto_collector_service.py` | 자동 수집 + 분석 (프로덕션) | ⭐⭐⭐⭐⭐ |
| `api/server.py` | REST API 서버 | ⭐⭐⭐⭐ |
| `src/analyzer/deep_analyzer.py` | AI 기반 품질 분석 | ⭐⭐⭐⭐⭐ |
| `src/converter/rule_based_converter.py` | Pine → Python 변환 | ⭐⭐⭐⭐ |
| `docker-compose.yml` | Docker 서비스 정의 | ⭐⭐⭐⭐⭐ |
| `.env` | 환경 변수 (API 키) | ⭐⭐⭐⭐⭐ |

---

## 기술 스택

### Backend

| 항목 | 기술 | 버전 | 용도 |
|------|------|------|------|
| **언어** | Python | 3.11.14 | 메인 언어 |
| **웹 프레임워크** | FastAPI | 0.104+ | REST API |
| **비동기** | asyncio, aiohttp | - | 비동기 I/O |
| **AI/LLM** | Anthropic Claude | 3.5 Sonnet | 품질 분석 |
| **데이터베이스** | SQLite | 3.x | 경량 DB |
| **DB 드라이버** | aiosqlite | - | 비동기 SQLite |
| **스크래핑** | Playwright | 1.40+ | Chromium 자동화 |
| **백테스트** | backtesting.py | - | 전략 백테스트 |
| **데이터 분석** | pandas, numpy | - | 데이터 처리 |

### 인프라

| 항목 | 기술 | 상태 |
|------|------|------|
| **서버 OS** | Ubuntu 22.04 LTS | ✅ |
| **서버 위치** | Hetzner Cloud, Germany | ✅ |
| **IP 주소** | 5.161.112.248 | ✅ |
| **컨테이너** | Docker + Docker Compose | ✅ |
| **CI/CD** | GitHub Actions | ✅ |
| **알림** | Telegram Bot API | ⚠️ (설정 선택) |
| **웹서버** | Nginx | 🚧 (설정 예정) |

### AI 모델

| 용도 | 모델 | 비용 | 사용처 |
|------|------|------|--------|
| **심층 분석** | `claude-3-5-sonnet-20241022` | $3/MTok | deep_analyzer.py |
| **요약 생성** | `claude-3-5-haiku-20241022` | $1/MTok | 리포트 생성 (미사용) |
| **변환** | `gemini-2.0-flash-exp` | 무료 | LLM 변환 (Phase 4) |

---

## 로컬 개발 환경 설정

### 1️⃣ 사전 요구사항

- **Python**: 3.11 이상 (권장: 3.11.14)
- **Git**: 최신 버전
- **GitHub CLI**: `gh` (선택, CI/CD 확인용)
- **macOS/Linux**: 검증됨 (Windows는 WSL2 권장)

### 2️⃣ 프로젝트 클론

```bash
# 로컬 경로 확인
cd /Users/mr.joo/Desktop/전략연구소

# 이미 클론되어 있음 (확인)
ls -la strategy-research-lab

# Git 상태 확인
cd strategy-research-lab
git status
git remote -v
```

### 3️⃣ 가상환경 생성

```bash
cd strategy-research-lab

# 가상환경 생성
python3.11 -m venv venv

# 활성화
source venv/bin/activate  # macOS/Linux
# venv\Scripts\activate   # Windows

# Python 버전 확인
python --version
# Python 3.11.14 확인
```

### 4️⃣ 의존성 설치

```bash
# Python 패키지 설치
pip install --upgrade pip
pip install -r requirements.txt

# Playwright 브라우저 설치
playwright install chromium

# 설치 확인
python -c "import playwright; print('Playwright OK')"
python -c "import anthropic; print('Anthropic OK')"
```

### 5️⃣ 환경 변수 설정

```bash
# .env 파일 확인 (이미 존재)
cat .env

# .env 파일 내용 (예시)
ANTHROPIC_API_KEY=sk-ant-api03-FqEiz8Skz0BK_...
DB_PATH=data/strategies.db
MAX_STRATEGIES=50
MIN_LIKES=500
HEADLESS=true
TIMEOUT=30000
LLM_MODEL=claude-3-5-sonnet-20241022
SKIP_LLM=false
MAX_RETRIES=3
OUTPUT_DIR=data/converted
LOGS_DIR=logs
RATE_LIMIT_DELAY=1.0

# (선택) 텔레그램 알림 추가
# TELEGRAM_BOT_TOKEN=your_bot_token
# TELEGRAM_CHAT_ID=your_chat_id
```

### 6️⃣ 로컬 테스트 실행

#### 단일 수집 테스트

```bash
# 5개 전략만 수집 (테스트)
python main.py --max-strategies 5 --min-likes 1000

# 로그 확인
tail -f logs/collector_*.log
```

#### API 서버 실행

```bash
# FastAPI 서버 시작
cd api
uvicorn server:app --reload --host 0.0.0.0 --port 8080

# 다른 터미널에서 테스트
curl http://localhost:8080/api/health
curl http://localhost:8080/api/stats

# 브라우저에서 Swagger UI
open http://localhost:8080/api/docs
```

#### 전체 파이프라인 테스트

```bash
# 자동 수집 스크립트 (1회만 실행)
python scripts/auto_collector_service.py --once

# 출력 예시:
# 🚀 수집 사이클 시작 #1
# 📊 페이지 1 수집 중...
# ✅ 수집 완료: 5개 전략
# 🔍 분석 시작...
# ✅ 분석 완료: 5/5
# 📄 리포트 생성 완료
```

---

## 배포 서버 정보

### 서버 스펙

| 항목 | 값 |
|------|-----|
| **IP 주소** | `5.161.112.248` |
| **호스팅** | Hetzner Cloud |
| **위치** | Falkenstein, Germany |
| **OS** | Ubuntu 22.04 LTS |
| **프로젝트 경로** | `/root/service_c/strategy-research-lab` |
| **포트** | 8081 (외부), 8080 (내부) |

### SSH 접속

```bash
# SSH 접속
ssh root@5.161.112.248
# 비밀번호: Wnrkswl!23

# 또는 sshpass 사용 (자동화)
sshpass -p 'Wnrkswl!23' ssh -o StrictHostKeyChecking=no root@5.161.112.248

# 프로젝트 디렉토리 이동
cd /root/service_c/strategy-research-lab
```

### 실행 중인 서비스

#### Docker Compose 구성

```yaml
# docker-compose.yml
services:
  strategy-lab:
    container_name: strategy-research-lab
    image: strategy-research-lab-strategy-lab
    ports:
      - "8081:8080"
    restart: always
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  scheduler:
    container_name: strategy-scheduler
    image: strategy-research-lab-scheduler
    restart: always
    depends_on:
      - strategy-lab
```

#### 서비스 상태 확인

```bash
# Docker 컨테이너 상태
docker compose -f /root/service_c/strategy-research-lab/docker-compose.yml ps

# 출력 예시:
# NAME                   STATUS                 PORTS
# strategy-research-lab  Up 20 minutes (healthy) 0.0.0.0:8081->8080/tcp
# strategy-scheduler     Up 10 minutes (unhealthy)

# 로그 확인
docker compose logs -f strategy-lab    # API 서버 로그
docker compose logs -f scheduler       # 스케줄러 로그

# 컨테이너 재시작
docker compose restart strategy-lab
docker compose restart scheduler

# 전체 재시작
docker compose down
docker compose up -d
```

### 데이터 파일 위치

```bash
# 데이터베이스
/root/service_c/strategy-research-lab/data/strategies.db

# HTML 리포트
/root/service_c/strategy-research-lab/data/beginner_report.html

# 로그 파일
/root/service_c/strategy-research-lab/logs/

# 변환된 Python 코드
/root/service_c/strategy-research-lab/data/converted/
```

---

## API 문서

### Base URL

**프로덕션**: http://5.161.112.248:8081
**로컬**: http://localhost:8080

### 엔드포인트 목록

#### 1. Health Check

```bash
GET /api/health

# 응답 예시:
{
  "status": "healthy",
  "timestamp": "2026-01-04T21:15:31.419005",
  "database_exists": true
}
```

#### 2. 전략 통계

```bash
GET /api/stats

# 응답 예시:
{
  "total_strategies": 44,
  "analyzed_count": 44,
  "passed_count": 15,
  "avg_score": 63.9
}
```

#### 3. 전략 목록 조회

```bash
GET /api/strategies?grade=B&limit=10&offset=0

# 쿼리 파라미터:
# - grade: A/B/C/D/F (등급 필터)
# - limit: 최대 개수 (기본: 50)
# - offset: 페이지네이션 오프셋 (기본: 0)
# - min_likes: 최소 좋아요 수
# - order_by: total_score, likes, created_at (정렬 기준)

# 응답 예시:
[
  {
    "script_id": "V8X0KT7b",
    "title": "Next Candle Predictor",
    "author": "PredictaFutures",
    "likes": 2200,
    "total_score": 76.0,
    "grade": "B",
    "repainting_score": 100.0,
    "overfitting_score": 80.0
  }
]
```

#### 4. 전략 상세 정보

```bash
GET /api/strategy/{script_id}

# 예시:
GET /api/strategy/V8X0KT7b

# 응답 예시:
{
  "script_id": "V8X0KT7b",
  "title": "Next Candle Predictor",
  "author": "PredictaFutures",
  "likes": 2200,
  "script_url": "https://www.tradingview.com/script/V8X0KT7b/",
  "pine_code": "// Pine Script 코드...",
  "total_score": 76.0,
  "grade": "B",
  "repainting_score": 100.0,
  "overfitting_score": 80.0,
  "risk_score": 60.0,
  "analysis": {
    "strengths": ["명확한 진입/청산 로직"],
    "weaknesses": ["SL/TP 미포함"],
    "recommendations": ["리스크 관리 추가"]
  },
  "created_at": "2026-01-04T10:15:30"
}
```

#### 5. Swagger UI

```bash
GET /api/docs

# 브라우저에서 열기
open http://5.161.112.248:8081/api/docs
```

### API 사용 예시

#### Python

```python
import requests

BASE_URL = "http://5.161.112.248:8081"

# 통계 조회
stats = requests.get(f"{BASE_URL}/api/stats").json()
print(f"총 전략: {stats['total_strategies']}개")

# B등급 전략 조회
b_grade = requests.get(f"{BASE_URL}/api/strategies?grade=B").json()
for strategy in b_grade:
    print(f"{strategy['title']} - {strategy['total_score']}점")
```

#### cURL

```bash
# 통계 조회
curl -s http://5.161.112.248:8081/api/stats | jq

# 전략 목록 (상위 3개)
curl -s "http://5.161.112.248:8081/api/strategies?limit=3" | jq

# 특정 전략 상세
curl -s http://5.161.112.248:8081/api/strategy/V8X0KT7b | jq
```

---

## 데이터베이스 스키마

### SQLite Database: `strategies.db`

#### 테이블: `strategies`

```sql
CREATE TABLE strategies (
    -- 기본 정보
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    script_id TEXT UNIQUE NOT NULL,          -- TradingView 스크립트 ID
    title TEXT NOT NULL,                     -- 전략 이름
    author TEXT,                             -- 작성자
    likes INTEGER DEFAULT 0,                 -- 좋아요 수
    script_url TEXT,                         -- TradingView URL

    -- Pine Script 코드
    pine_code TEXT,                          -- Pine Script 원본

    -- 분석 점수
    total_score REAL DEFAULT 0.0,            -- 총점 (0-100)
    grade TEXT,                              -- 등급 (A/B/C/D/F)
    repainting_score REAL,                   -- Repainting 점수 (0-100)
    overfitting_score REAL,                  -- Overfitting 점수 (0-100)
    risk_score REAL,                         -- Risk 점수 (0-100)

    -- AI 분석 결과
    analysis TEXT,                           -- JSON 형식 분석 결과

    -- 변환 정보
    python_code TEXT,                        -- 변환된 Python 코드
    conversion_status TEXT,                  -- converted, failed, pending

    -- 타임스탬프
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    analyzed_at TIMESTAMP
);

-- 인덱스
CREATE INDEX idx_grade ON strategies(grade);
CREATE INDEX idx_total_score ON strategies(total_score DESC);
CREATE INDEX idx_likes ON strategies(likes DESC);
CREATE INDEX idx_script_id ON strategies(script_id);
```

#### 샘플 쿼리

```sql
-- 전체 통계
SELECT
    COUNT(*) as total,
    AVG(total_score) as avg_score,
    COUNT(CASE WHEN grade IN ('A','B') THEN 1 END) as excellent
FROM strategies;

-- 등급별 분포
SELECT grade, COUNT(*) as count
FROM strategies
GROUP BY grade
ORDER BY grade;

-- TOP 10 전략
SELECT title, author, likes, total_score, grade
FROM strategies
ORDER BY total_score DESC
LIMIT 10;

-- B등급 이상 전략
SELECT script_id, title, total_score, grade
FROM strategies
WHERE grade IN ('A', 'B')
ORDER BY total_score DESC;

-- Repainting 안전한 전략
SELECT title, repainting_score, total_score
FROM strategies
WHERE repainting_score >= 90
ORDER BY total_score DESC;
```

---

## 주요 컴포넌트 상세

### 1️⃣ 수집 모듈 (Collector)

#### `scripts_scraper.py`

**기능**: TradingView Scripts 페이지에서 전략 메타데이터 수집

**주요 클래스**: `ScriptsScraper`

```python
class ScriptsScraper:
    async def scrape_strategies(
        self,
        max_strategies: int = 100,
        min_likes: int = 500
    ) -> List[Dict]:
        """
        전략 메타데이터 수집

        Args:
            max_strategies: 최대 수집 개수
            min_likes: 최소 좋아요 수

        Returns:
            List[Dict]: 전략 메타데이터 리스트
        """
```

**수집 로직**:
1. Playwright로 Chromium 브라우저 시작
2. TradingView Scripts 페이지 이동
3. 필터 적용: "Strategies", "Popular"
4. 무한 스크롤로 페이지 순회
5. 각 전략의 메타데이터 추출 (제목, 작성자, 좋아요, URL)
6. 중복 제거 및 필터링

**Rate Limiting**:
- 페이지당 12-14초 대기
- 인간 행동 패턴 시뮬레이션 (랜덤 휴식 15-25초)
- User-Agent 로테이션

#### `pine_fetcher.py`

**기능**: 각 전략 페이지에서 Pine Script 코드 추출

**주요 클래스**: `PineFetcher`

```python
class PineFetcher:
    async def fetch_pine_code(self, script_url: str) -> Optional[str]:
        """
        Pine Script 코드 추출

        Args:
            script_url: TradingView 스크립트 URL

        Returns:
            Optional[str]: Pine Script 코드 (없으면 None)
        """
```

**추출 로직**:
1. 스크립트 페이지 접근
2. "소스 코드 보기" 버튼 클릭
3. 코드 블록에서 텍스트 추출
4. 정규화 및 검증

### 2️⃣ 분석 모듈 (Analyzer)

#### `deep_analyzer.py`

**기능**: Claude API를 사용한 심층 품질 분석

**주요 클래스**: `DeepAnalyzer`

```python
class DeepAnalyzer:
    def __init__(self, api_key: str):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = "claude-3-5-sonnet-20241022"

    async def analyze(self, pine_code: str) -> AnalysisResult:
        """
        Pine Script 심층 분석

        분석 항목:
        - Repainting 위험 (미래 데이터 참조)
        - Overfitting 위험 (과적합)
        - Risk 관리 (SL/TP 유무)
        - 코드 품질
        - 전략 설명

        Returns:
            AnalysisResult: 분석 결과 객체
        """
```

**프롬프트 구조**:
```
당신은 TradingView Pine Script 전문가입니다.

다음 전략을 분석하고 JSON 형식으로 응답하세요:

Pine Script 코드:
```pine
[코드]
```

분석 항목:
1. repainting_score (0-100): 미래 데이터 참조 여부
2. overfitting_score (0-100): 과적합 위험
3. risk_score (0-100): 리스크 관리 수준
4. strengths: 강점 (리스트)
5. weaknesses: 약점 (리스트)
6. recommendations: 개선 제안 (리스트)

출력 형식:
{
  "repainting_score": 85,
  "overfitting_score": 70,
  "risk_score": 60,
  "strengths": ["명확한 로직"],
  "weaknesses": ["SL 미포함"],
  "recommendations": ["SL 추가"]
}
```

#### `scorer.py`

**기능**: 개별 점수를 통합하여 최종 등급 산출

```python
def calculate_total_score(
    repainting_score: float,
    overfitting_score: float,
    risk_score: float
) -> float:
    """
    가중 평균 점수 계산

    가중치:
    - Repainting: 40%
    - Overfitting: 30%
    - Risk: 30%
    """
    weights = {
        "repainting": 0.4,
        "overfitting": 0.3,
        "risk": 0.3
    }

    total = (
        repainting_score * weights["repainting"] +
        overfitting_score * weights["overfitting"] +
        risk_score * weights["risk"]
    )

    return round(total, 1)

def assign_grade(total_score: float) -> str:
    """등급 부여"""
    if total_score >= 80:
        return "A"
    elif total_score >= 70:
        return "B"
    elif total_score >= 60:
        return "C"
    elif total_score >= 50:
        return "D"
    else:
        return "F"
```

### 3️⃣ 변환 모듈 (Converter)

#### `rule_based_converter.py`

**기능**: 규칙 기반 Pine Script → Python 변환

**지원 패턴**:
- 기본 지표: `sma()`, `ema()`, `rsi()`, `macd()`
- 조건문: `if`, `else`
- 변수 선언: `var`, `float`, `int`
- 함수 호출

**제한사항**:
- 복잡한 사용자 정의 함수: ❌
- 고급 배열 조작: ❌
- 특수 Pine Script 내장 함수: ❌

**Phase 4 계획**:
- LLM 기반 변환기 추가 (`llm_converter.py`)
- 복잡도 0.3 이상 전략 처리
- Claude API를 사용한 완전 변환

---

## 배포 가이드

### 🚨 배포 시 절대 규칙

**배포 원칙**:
1. ✅ **로컬 → GitHub → 원격서버** 순서 엄수
2. ❌ 원격서버에서 직접 코드 수정 금지
3. ✅ 모든 변경사항은 Git 커밋 필수
4. ✅ GitHub Actions를 통한 자동 배포

### GitHub Actions CI/CD 워크플로우

#### 워크플로우 파일: `.github/workflows/deploy.yml`

```yaml
name: Deploy to Production

on:
  push:
    branches:
      - main

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v3

      - name: Deploy to server
        env:
          SSH_PRIVATE_KEY: ${{ secrets.SSH_PRIVATE_KEY }}
        run: |
          # SSH 키 설정
          mkdir -p ~/.ssh
          echo "$SSH_PRIVATE_KEY" > ~/.ssh/id_rsa
          chmod 600 ~/.ssh/id_rsa

          # rsync로 파일 전송
          rsync -avz --exclude '.git' \
                      --exclude 'venv' \
                      --exclude '__pycache__' \
                      --exclude '*.pyc' \
                      ./ root@5.161.112.248:/root/service_c/strategy-research-lab/

          # Docker 재빌드 및 재시작
          ssh root@5.161.112.248 << 'EOF'
            cd /root/service_c/strategy-research-lab
            docker compose down
            docker compose build
            docker compose up -d
          EOF

      - name: Health check
        run: |
          sleep 30
          curl -f http://5.161.112.248:8081/api/health
```

### 배포 실행 절차

#### 1️⃣ 로컬에서 코드 수정

```bash
cd /Users/mr.joo/Desktop/전략연구소/strategy-research-lab

# 예: analyzer 코드 수정
vim src/analyzer/deep_analyzer.py

# 또는 VSCode
code .
```

#### 2️⃣ 변경사항 확인 및 테스트

```bash
# 변경 파일 확인
git status

# 차이점 확인
git diff src/analyzer/deep_analyzer.py

# 로컬 테스트
python -m pytest tests/test_analyzer.py

# 또는 단일 실행
python main.py --max-strategies 3
```

#### 3️⃣ Git 커밋

```bash
# 변경 파일 스테이징
git add src/analyzer/deep_analyzer.py

# 또는 모든 변경사항
git add .

# 커밋 (명확한 메시지 작성)
git commit -m "fix: Claude API 프롬프트 개선 - Repainting 탐지 정확도 향상"

# 커밋 메시지 규칙:
# - feat: 새 기능
# - fix: 버그 수정
# - docs: 문서 수정
# - refactor: 리팩토링
# - test: 테스트 추가
# - chore: 기타 변경
```

#### 4️⃣ GitHub에 푸시

```bash
# main 브랜치에 푸시
git push origin main

# 푸시 결과 확인
# GitHub Actions가 자동으로 트리거됨
```

#### 5️⃣ GitHub Actions 워크플로우 확인

```bash
# CLI에서 확인
gh run list --limit 1

# 출력 예시:
# ✓  Deploy to Production  main  push  1234567  2m 30s ago

# 상세 로그 확인
gh run view --log

# 또는 브라우저에서 확인
# https://github.com/joocy75-hash/TradingView-Strategy/actions
```

#### 6️⃣ 배포 완료 확인 (5-10분 소요)

```bash
# 헬스체크
curl http://5.161.112.248:8081/api/health

# 응답 예시:
# {"status":"healthy","timestamp":"..."}

# 통계 확인 (데이터 변경 시)
curl http://5.161.112.248:8081/api/stats

# Docker 컨테이너 상태 확인
ssh root@5.161.112.248 "docker compose -f /root/service_c/strategy-research-lab/docker-compose.yml ps"
```

#### 7️⃣ 원격서버 로그 확인

```bash
# SSH 접속
ssh root@5.161.112.248

# 프로젝트 디렉토리 이동
cd /root/service_c/strategy-research-lab

# API 서버 로그
docker compose logs -f strategy-lab

# 스케줄러 로그
docker compose logs -f scheduler

# 최근 100줄만 확인
docker compose logs --tail=100 scheduler

# 에러만 필터링
docker compose logs scheduler 2>&1 | grep -i error
```

### 배포 실패 시 대응

#### 시나리오 1: GitHub Actions 실패

```bash
# 워크플로우 상태 확인
gh run list --limit 1

# 실패 원인 확인
gh run view --log

# 일반적인 원인:
# 1. SSH 키 권한 문제
# 2. rsync 실패 (서버 접속 불가)
# 3. Docker 빌드 실패

# 재실행
gh run rerun <run_id>
```

#### 시나리오 2: Docker 컨테이너 시작 실패

```bash
# SSH 접속
ssh root@5.161.112.248

# 컨테이너 상태 확인
docker compose -f /root/service_c/strategy-research-lab/docker-compose.yml ps

# 로그 확인
docker compose logs strategy-lab

# 일반적인 원인:
# 1. 환경 변수 누락 (.env 파일)
# 2. 포트 충돌 (8081)
# 3. 의존성 설치 실패

# 수동 재시작
docker compose down
docker compose up -d

# 빌드 캐시 제거 후 재시작
docker compose down
docker compose build --no-cache
docker compose up -d
```

#### 시나리오 3: API 응답 없음

```bash
# 헬스체크 실패
curl http://5.161.112.248:8081/api/health
# (타임아웃 또는 Connection refused)

# 원인 확인:
# 1. Docker 컨테이너 중단
docker compose ps

# 2. 포트 바인딩 확인
netstat -tlnp | grep 8081

# 3. 방화벽 확인
ufw status

# 해결:
docker compose restart strategy-lab
```

### 롤백 절차

```bash
# 1. Git 이전 커밋으로 되돌리기
git log --oneline -5
# 54a053c ci: Add GitHub Actions CI/CD workflow
# 710293e feat: Phase 4 - LLM-Based Pine Script Converter
# ec02fa4 Fix: Pydantic 2.x compatibility

# 2. 특정 커밋으로 롤백
git revert 54a053c

# 3. 푸시하여 자동 배포
git push origin main

# 4. 또는 강제 롤백 (주의!)
git reset --hard 710293e
git push --force origin main
```

---

## 트러블슈팅

### 문제 1: 스케줄러 컨테이너 Unhealthy

**증상**:
```bash
docker compose ps
# STATUS: strategy-scheduler - Unhealthy
```

**원인**:
- 데이터베이스 아직 생성 안 됨 (수집 진행 중)
- 헬스체크 타이밍 이슈

**해결**:
```bash
# 로그 확인
docker compose logs scheduler | tail -20

# 실제로 수집 중이면 정상
# "📈 페이지 15: 총 9개 수집" 같은 로그가 보이면 정상

# 수집 완료 후 자동으로 Healthy 상태로 전환됨
```

**예방**:
- Unhealthy는 무시해도 됨 (기능상 문제 없음)
- 원한다면 healthcheck 비활성화:
  ```yaml
  # docker-compose.yml
  scheduler:
    healthcheck:
      disable: true
  ```

### 문제 2: API 응답 없음 (504 Gateway Timeout)

**증상**:
```bash
curl http://5.161.112.248:8081/api/health
# (504 Gateway Timeout)
```

**원인**:
- Docker 컨테이너 중단
- Nginx 미설정 (현재 상태)

**해결**:
```bash
# 1. 컨테이너 상태 확인
ssh root@5.161.112.248
docker compose -f /root/service_c/strategy-research-lab/docker-compose.yml ps

# 2. 중단되었다면 재시작
docker compose restart strategy-lab

# 3. 포트 직접 확인 (Nginx 우회)
curl http://5.161.112.248:8081/api/health

# 4. 컨테이너 내부 확인
docker compose exec strategy-lab curl http://localhost:8080/api/health
```

### 문제 3: 수집기가 0개 전략 수집

**증상**:
```bash
docker compose logs scheduler
# "✅ 수집 완료: 0개 전략"
```

**원인**:
- TradingView 접근 차단 (Rate Limit)
- 필터 조건 너무 엄격
- Playwright 브라우저 시작 실패

**해결**:
```bash
# 1. Headless 모드 해제 (로컬 테스트)
# .env 파일:
HEADLESS=false

# 2. Rate Limit 완화
RATE_LIMIT_DELAY=2.0  # 1초 → 2초

# 3. 필터 조건 완화
MIN_LIKES=300  # 500 → 300

# 4. Playwright 재설치
docker compose exec scheduler playwright install chromium

# 5. 로컬에서 테스트
python main.py --max-strategies 5 --headless false
```

### 문제 4: 데이터베이스 잠금 (Database Locked)

**증상**:
```bash
sqlite3.OperationalError: database is locked
```

**원인**:
- 동시에 여러 프로세스가 DB 접근
- aiosqlite 미사용

**해결**:
```bash
# 이미 aiosqlite로 해결됨
# 발생 시 임시 조치:

# 1. 스케줄러 임시 중지
docker stop strategy-scheduler

# 2. DB 작업 완료 후 재시작
docker start strategy-scheduler

# 3. 영구 해결: aiosqlite 확인
grep -r "aiosqlite" src/storage/database.py
```

### 문제 5: Claude API 할당량 초과

**증상**:
```bash
anthropic.RateLimitError: 429 Too Many Requests
```

**원인**:
- API 호출 속도 제한 초과
- 월간 할당량 소진

**해결**:
```bash
# 1. API 사용량 확인
# https://console.anthropic.com/settings/usage

# 2. 임시로 LLM 분석 비활성화
# .env 파일:
SKIP_LLM=true

# 3. Rate Limit 추가
# src/analyzer/deep_analyzer.py에 sleep 추가
await asyncio.sleep(1.0)  # 1초 대기

# 4. 배치 크기 줄이기
MAX_STRATEGIES=30  # 50 → 30
```

### 문제 6: GitHub Actions 배포 실패

**증상**:
```bash
gh run list
# ✗ Deploy to Production (failed)
```

**원인**:
- SSH 키 권한 문제
- 서버 접속 불가

**해결**:
```bash
# 1. GitHub Secrets 확인
gh secret list

# 출력 예시:
# ANTHROPIC_API_KEY  Updated 2025-12-26
# SSH_PRIVATE_KEY    Updated 2025-12-26

# 2. SSH 키 재설정 (필요 시)
# 로컬에서 SSH 키 생성
ssh-keygen -t rsa -b 4096 -C "github-actions"

# Public 키를 서버에 추가
cat ~/.ssh/id_rsa.pub | ssh root@5.161.112.248 "cat >> ~/.ssh/authorized_keys"

# Private 키를 GitHub Secrets에 추가
gh secret set SSH_PRIVATE_KEY < ~/.ssh/id_rsa

# 3. 워크플로우 재실행
gh run rerun <run_id>

# 4. 수동 배포 (최후 수단)
rsync -avz --exclude '.git' \
            --exclude 'venv' \
            ./ root@5.161.112.248:/root/service_c/strategy-research-lab/
```

### 문제 7: 메모리 부족 (Out of Memory)

**증상**:
```bash
docker stats
# strategy-scheduler  1.5GB / 1.5GB  100.00%
# (컨테이너 강제 종료)
```

**원인**:
- Playwright Chromium 메모리 사용
- 대량 데이터 처리

**해결**:
```bash
# 1. 메모리 제한 증가
# docker-compose.yml:
scheduler:
  deploy:
    resources:
      limits:
        memory: 2G  # 1.5G → 2G

# 2. 배치 크기 줄이기
MAX_STRATEGIES=20  # 50 → 20

# 3. Playwright 설정 최적화
# src/collector/scripts_scraper.py:
browser = await playwright.chromium.launch(
    args=[
        '--disable-dev-shm-usage',  # 공유 메모리 사용 안 함
        '--disable-gpu',
        '--no-sandbox'
    ]
)

# 4. 재시작
docker compose restart scheduler
```

---

## 작업 로드맵

### Phase 4: LLM 기반 변환기 (미완료)

**목표**: 복잡도 0.3 이상의 전략을 LLM으로 변환

**예상 소요 시간**: 2-3주

**상세 계획**: [IMPLEMENTATION_ROADMAP.md](IMPLEMENTATION_ROADMAP.md) 참조

#### Week 1: LLM Converter 기본 구조

**Day 1-3**:
- [ ] `llm_converter.py`: Claude API 통합
- [ ] `llm_prompt_builder.py`: 프롬프트 생성
- [ ] `llm_response_parser.py`: 응답 파싱
- [ ] `llm_validator.py`: 출력 검증

**Day 4-5**:
- [ ] `hybrid_converter.py`: Rule + LLM 하이브리드
- [ ] `conversion_strategy.py`: 전략 선택 로직

#### Week 2: 통합 및 최적화

**Day 1-2**:
- [ ] `unified_converter.py`: 통합 인터페이스
- [ ] API 엔드포인트 추가

**Day 3-5**:
- [ ] `conversion_cache.py`: 캐싱
- [ ] `cost_optimizer.py`: 비용 최적화
- [ ] 성능 벤치마크

#### Week 3: 테스트 및 문서화

- [ ] 종합 테스트 (10개 이상 전략)
- [ ] API 문서 작성
- [ ] Phase 4 완료 보고서

### Phase 5: 백테스트 시스템 통합 (계획)

**목표**: 변환된 전략을 자동으로 백테스트

**예상 소요 시간**: 2주

- Week 1: 백테스트 엔진 통합
- Week 2: 자동 백테스트 파이프라인

### Phase 6: 프로덕션 배포 준비 (계획)

**목표**: 실제 서비스 배포 가능한 상태

- Docker 컨테이너화 완성
- API 엔드포인트 확장
- 모니터링 및 로깅

---

## FAQ

### Q1: 로컬 코드와 원격서버 코드가 다른 것 같아요

**A**: 다음 명령어로 동기화 상태를 확인하세요:

```bash
# 로컬 MD5 해시
cd strategy-research-lab
md5 main.py api/server.py

# 원격 MD5 해시
ssh root@5.161.112.248 "cd /root/service_c/strategy-research-lab && md5sum main.py api/server.py"

# 해시가 다르면:
# 1. 로컬 변경사항 확인
git status
git diff

# 2. GitHub에 푸시
git add .
git commit -m "sync: 코드 동기화"
git push origin main

# 3. GitHub Actions가 자동 배포 (5-10분 대기)
gh run watch
```

### Q2: 수집기가 계속 Unhealthy 상태입니다

**A**: Unhealthy는 정상 동작 중일 수 있습니다:

```bash
# 로그 확인
docker compose -f /root/service_c/strategy-research-lab/docker-compose.yml logs scheduler | tail -30

# "📈 페이지 XX: 총 YY개 수집" 로그가 보이면 정상
# 수집 완료 후 자동으로 Healthy 상태로 전환됨

# 진짜 문제인지 확인:
# 1. 에러 로그 확인
docker compose logs scheduler 2>&1 | grep -i error

# 2. Python 프로세스 확인
docker compose exec scheduler ps aux | grep python

# 3. 재시작 (최후 수단)
docker compose restart scheduler
```

### Q3: API가 404 에러를 반환합니다

**A**: 엔드포인트 경로를 확인하세요:

```bash
# 올바른 엔드포인트:
curl http://5.161.112.248:8081/api/health       # ✅
curl http://5.161.112.248:8081/api/stats        # ✅
curl "http://5.161.112.248:8081/api/strategies" # ✅

# 잘못된 엔드포인트:
curl http://5.161.112.248:8081/health           # ❌ (/api 누락)
curl http://5.161.112.248/api/health            # ❌ (:8081 누락)

# Swagger UI에서 전체 엔드포인트 확인:
open http://5.161.112.248:8081/api/docs
```

### Q4: 텔레그램 알림을 활성화하고 싶어요

**A**: 다음 단계를 따르세요:

```bash
# 1. 텔레그램 봇 생성
# - @BotFather에게 /newbot 명령
# - 봇 이름 및 username 설정
# - 토큰 받기: 1234567890:ABCdefGHIjklMNOpqrsTUVwxyz

# 2. Chat ID 확인
# - 봇에게 메시지 전송
# - https://api.telegram.org/bot<TOKEN>/getUpdates 접속
# - chat.id 값 확인

# 3. .env 파일 수정 (로컬)
cd strategy-research-lab
vim .env

# 추가:
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_CHAT_ID=987654321

# 4. GitHub에 푸시 (자동 배포)
git add .env
git commit -m "feat: 텔레그램 알림 활성화"
git push origin main

# 5. 배포 완료 후 확인
# 텔레그램에 "🚀 수집 사이클 시작" 메시지가 오면 성공
```

### Q5: 데이터베이스를 초기화하고 싶어요

**A**: 주의하여 실행하세요 (모든 데이터 삭제됨):

```bash
# 원격서버에서 실행
ssh root@5.161.112.248

# 1. 스케줄러 중지
docker compose -f /root/service_c/strategy-research-lab/docker-compose.yml stop scheduler

# 2. 데이터베이스 백업
cp /root/service_c/strategy-research-lab/data/strategies.db \
   /root/backups/strategies_backup_$(date +%Y%m%d_%H%M%S).db

# 3. 데이터베이스 삭제
rm /root/service_c/strategy-research-lab/data/strategies.db

# 4. 스케줄러 재시작 (자동으로 새 DB 생성)
docker compose start scheduler

# 5. 로그 확인
docker compose logs -f scheduler
```

### Q6: Phase 4는 언제 시작하나요?

**A**: 현재는 Phase 1-3 안정화 중이며, Phase 4는 다음 조건 충족 시 시작합니다:

**시작 조건**:
- [ ] 100개 이상 전략 수집 완료
- [ ] B등급 이상 전략 5개 이상 발견
- [ ] 백테스트 데이터셋 75개 수집 완료
- [ ] 현재 시스템 30일 이상 안정 운영

**예상 시작**: 2026년 1월 중순 ~ 2월 초

### Q7: 서버 비용은 얼마나 드나요?

**A**: 월간 예상 비용:

| 항목 | 비용 | 비고 |
|------|------|------|
| Hetzner 서버 | €5-10/월 | CX11 또는 CX21 |
| Claude API | $10-50/월 | 사용량에 따라 변동 |
| 도메인 | $10-15/년 | 선택 사항 |
| **총계** | **$15-60/월** | 평균 $30/월 |

**비용 절감 팁**:
- `SKIP_LLM=true` 설정 시 Claude API 비용 $0
- 수집 주기 12시간으로 변경 시 서버 부하 감소
- 무료 Tier 활용 (Gemini API)

### Q8: 다른 사람이 작업한 내용을 어떻게 확인하나요?

**A**: Git 히스토리를 확인하세요:

```bash
cd strategy-research-lab

# 최근 5개 커밋 확인
git log --oneline -5

# 특정 커밋의 변경사항 확인
git show <commit_hash>

# 특정 파일의 변경 히스토리
git log -p -- src/analyzer/deep_analyzer.py

# 특정 날짜 범위의 커밋
git log --since="2026-01-01" --until="2026-01-04"

# 작업자별 커밋
git log --author="Claude"

# 변경 통계
git diff --stat HEAD~5 HEAD
```

### Q9: 원격서버에 직접 접속해야 하는 경우는?

**A**: 다음 경우에만 SSH 접속:

**허용되는 작업**:
- ✅ 로그 확인 (`docker compose logs`)
- ✅ 컨테이너 상태 확인 (`docker compose ps`)
- ✅ 헬스체크 (`curl http://localhost:8080/api/health`)
- ✅ 데이터베이스 백업
- ✅ 디스크 용량 확인 (`df -h`)

**금지되는 작업**:
- ❌ 코드 파일 직접 수정 (`vim`, `nano`)
- ❌ Git 커밋
- ❌ Python 패키지 설치
- ❌ 환경 변수 직접 수정 (`.env`)

**올바른 방법**:
1. 로컬에서 수정
2. Git 커밋
3. GitHub 푸시
4. 자동 배포 대기

### Q10: 긴급 상황 시 어떻게 하나요?

**A**: 긴급 상황별 대응:

#### 시나리오 1: 서버 전체 다운

```bash
# 1. 서버 재부팅 (최후 수단)
ssh root@5.161.112.248 "reboot"

# 2. 5분 후 재접속
ssh root@5.161.112.248

# 3. Docker 상태 확인
systemctl status docker
docker ps

# 4. 서비스 재시작
cd /root/service_c/strategy-research-lab
docker compose up -d
```

#### 시나리오 2: 데이터베이스 손상

```bash
# 1. 백업에서 복원
cp /root/backups/strategies_backup_latest.db \
   /root/service_c/strategy-research-lab/data/strategies.db

# 2. 권한 확인
chown 1001:1001 /root/service_c/strategy-research-lab/data/strategies.db

# 3. 서비스 재시작
docker compose restart
```

#### 시나리오 3: API 완전 응답 없음

```bash
# 1. 컨테이너 강제 재시작
docker compose down
docker compose up -d --force-recreate

# 2. 로그 실시간 확인
docker compose logs -f

# 3. 여전히 안 되면 이미지 재빌드
docker compose down
docker compose build --no-cache
docker compose up -d
```

---

## 📞 연락처 및 리소스

### 주요 링크

- **프로덕션 API**: http://5.161.112.248:8081
- **Swagger UI**: http://5.161.112.248:8081/api/docs
- **GitHub 저장소**: https://github.com/joocy75-hash/TradingView-Strategy
- **GitHub Actions**: https://github.com/joocy75-hash/TradingView-Strategy/actions

### 추가 문서

- **IMPLEMENTATION_ROADMAP.md**: Phase 4 상세 로드맵
- **SERVER_HEALTH_CHECK_20260104.md**: 서버 상태 보고서
- **.claude/skills/**: 모듈별 가이드

### 버전 정보

- **프로젝트 버전**: 5.2
- **Python 버전**: 3.11.14
- **Docker 버전**: 24.0+
- **최종 업데이트**: 2026-01-04 21:20 KST

---

## 🔒 보안 주의사항

### API 키 관리

**절대 규칙**:
- ❌ API 키를 Git에 커밋 금지
- ❌ 코드에 하드코딩 금지
- ✅ `.env` 파일에만 저장
- ✅ `.gitignore`에 `.env` 추가됨

**API 키 로테이션**:
```bash
# 1. Anthropic Console에서 새 키 생성
# https://console.anthropic.com/settings/keys

# 2. 로컬 .env 업데이트
vim .env
# ANTHROPIC_API_KEY=sk-ant-api03-NEW_KEY

# 3. GitHub Secrets 업데이트
gh secret set ANTHROPIC_API_KEY

# 4. 원격서버 .env 업데이트 (수동)
ssh root@5.161.112.248
vim /root/service_c/strategy-research-lab/.env
# ANTHROPIC_API_KEY=sk-ant-api03-NEW_KEY

# 5. 컨테이너 재시작
docker compose restart
```

### 서버 보안

```bash
# 1. SSH 비밀번호 변경 (권장: 3개월마다)
ssh root@5.161.112.248
passwd

# 2. 방화벽 확인
ufw status

# 3. 열린 포트 확인
netstat -tlnp

# 4. Docker 컨테이너 권한 확인
docker ps --format "table {{.Names}}\t{{.Status}}"
```

### 데이터베이스 백업

```bash
# 자동 백업 설정 (cron)
ssh root@5.161.112.248
crontab -e

# 매일 새벽 3시 백업
0 3 * * * cp /root/service_c/strategy-research-lab/data/strategies.db \
              /root/backups/strategies_$(date +\%Y\%m\%d).db

# 7일 이상 된 백업 삭제
0 4 * * * find /root/backups -name "strategies_*.db" -mtime +7 -delete
```

---

## 📝 변경 이력

| 날짜 | 버전 | 변경 내용 | 작성자 |
|------|------|----------|--------|
| 2026-01-04 | 5.2 | 통합 가이드 작성, 배포 워크플로우 추가 | Claude Sonnet 4.5 |
| 2026-01-04 | 5.1 | 서버 상태 검증, 코드 동기화 확인 | Claude Sonnet 4.5 |
| 2026-01-04 | 5.0 | Phase 1-3 완료, 44개 전략 수집/분석 | Claude Sonnet 4.5 |
| 2025-12-27 | 4.0 | GitHub Actions CI/CD 구축 | Claude Sonnet 4.5 |
| 2025-12-26 | 3.0 | 원격서버 배포 (5.161.112.248) | Claude Sonnet 4.5 |
| 2025-12-25 | 2.0 | AI 분석 모듈 완성 | Claude Sonnet 4.5 |
| 2025-12-24 | 1.0 | 기본 수집 파이프라인 완성 | Claude Sonnet 4.5 |

---

**마스터 가이드 작성**: Claude Sonnet 4.5
**최종 검토**: 2026-01-04 21:20 KST
**다음 업데이트 예정**: Phase 4 시작 시

---

## ✅ 체크리스트: 이 문서를 읽었다면

- [ ] 코드 수정은 **로컬에서만** 한다는 것을 이해했습니다
- [ ] Git 커밋 → GitHub 푸시 → 자동 배포 절차를 숙지했습니다
- [ ] 원격서버에 직접 코드 수정하면 안 된다는 것을 알았습니다
- [ ] API 엔드포인트 목록을 확인했습니다
- [ ] 트러블슈팅 섹션을 읽었습니다
- [ ] 긴급 상황 시 대응 방법을 알고 있습니다

**모든 항목에 체크했다면, 안전하게 작업을 시작할 수 있습니다!** 🎉
