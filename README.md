# 🎯 TradingView Strategy Research Lab

**최종 업데이트**: 2026-01-04
**프로젝트 상태**: 운영 중 (M1-M4 완료, M5 80%)

---

## 📋 목차

1. [프로젝트 개요](#프로젝트-개요)
2. [시스템 구조](#시스템-구조)
3. [배포 서버 정보](#배포-서버-정보)
4. [빠른 시작](#빠른-시작)
5. [주요 기능](#주요-기능)
6. [현재 상태](#현재-상태)
7. [다음 단계](#다음-단계)
8. [트러블슈팅](#트러블슈팅)

---

## 프로젝트 개요

### 🎯 목적
TradingView에서 Pine Script 전략을 자동으로 수집 → AI 분석 → Python 변환 → 백테스트하여 실전 투자 가능한 전략만 선별하는 완전 자동화 시스템

### ✨ 핵심 가치
- **완전 자동화**: 6시간마다 자동 수집 및 분석
- **AI 기반**: Claude API로 전략 품질 심층 분석
- **실전 검증**: 75개 데이터셋으로 대규모 백테스트
- **리스크 관리**: 모든 전략에 SL/TP 자동 추가

### 📊 현재 성과
| 지표 | 수치 |
|------|------|
| 수집 전략 수 | 86개 (자동 수집 완료) |
| 분석 완료 | 63개 (평균 C등급) |
| B등급 전략 | 3개 (실거래 가능) |
| 백테스트 데이터셋 | 75개 (3년치) |
| 서버 가동률 | 100% (Docker 자동 재시작) |

---

## 시스템 구조

### 아키텍처

```
┌────────────────────────────────────────────────────────┐
│                  TradingView (데이터 소스)                │
└────────────────┬───────────────────────────────────────┘
                 │ Playwright 스크래핑
                 ▼
┌────────────────────────────────────────────────────────┐
│            전략 수집기 (Collector)                        │
│  • 500+ 부스트 전략 필터링                                │
│  • Pine Script 코드 추출                                 │
│  • 메타데이터 수집 (좋아요, 작성자 등)                      │
└────────────────┬───────────────────────────────────────┘
                 ▼
┌────────────────────────────────────────────────────────┐
│            AI 품질 분석기 (Analyzer)                      │
│  • Repainting 탐지 (미래 데이터 참조)                      │
│  • Overfitting 탐지 (과적합)                              │
│  • Risk 체크 (SL/TP 유무)                                │
│  • Claude API 심층 분석                                  │
│  → 등급 부여 (A~F)                                       │
└────────────────┬───────────────────────────────────────┘
                 ▼
┌────────────────────────────────────────────────────────┐
│         Pine → Python 변환기 (Converter)                 │
│  • Rule-based 변환 (기본 패턴)                            │
│  • AI 에이전트 변환 (복잡한 로직)                          │
│  • backtesting.py 호환 코드 생성                          │
└────────────────┬───────────────────────────────────────┘
                 ▼
┌────────────────────────────────────────────────────────┐
│         백테스트 엔진 (Backtest Engine)                   │
│  • 75개 데이터셋 (25 심볼 × 3 타임프레임)                  │
│  • 병렬 실행 (멀티프로세싱)                                │
│  • 고급 지표 계산 (Sharpe, PF, MaxDD 등)                  │
└────────────────┬───────────────────────────────────────┘
                 ▼
┌────────────────────────────────────────────────────────┐
│              결과 리포트 (Reporter)                       │
│  • HTML 대시보드 (초보자/전문가용)                         │
│  • REST API (FastAPI)                                   │
│  • 텔레그램 알림 (옵션)                                   │
└────────────────────────────────────────────────────────┘
```

### 디렉토리 구조

```
/Users/mr.joo/Desktop/전략연구소/
├── README.md                         # 이 파일 (메인 문서)
├── .env                              # 환경 변수 (API 키)
│
├── strategy-research-lab/            # 전략 수집 및 분석
│   ├── api/server.py                # FastAPI REST API
│   ├── src/
│   │   ├── collector/               # TradingView 스크래핑
│   │   ├── analyzer/                # 품질 분석
│   │   ├── converter/               # Pine → Python
│   │   ├── storage/                 # SQLite DB
│   │   └── notification/            # 텔레그램 알림
│   ├── scripts/
│   │   └── auto_collector_service.py  # 자동 수집 스크립트
│   ├── data/
│   │   ├── strategies.db            # 전략 데이터베이스
│   │   └── reports/                 # HTML 리포트
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── requirements.txt
│
└── trading-agent-system/             # AI 에이전트 및 백테스트
    ├── src/
    │   ├── agents/                  # 4개 AI 에이전트
    │   │   ├── strategy_architect.py    # Pine→Python 변환
    │   │   ├── variation_generator.py   # 전략 변형 생성
    │   │   ├── backtest_runner.py       # 다중 백테스트
    │   │   └── result_analyzer.py       # 결과 분석
    │   ├── indicators/              # 23개 기술 지표
    │   ├── backtest/                # 백테스트 엔진
    │   ├── data/                    # 데이터 수집기
    │   └── orchestrator/            # 파이프라인 자동화
    ├── data/datasets/               # 75개 백테스트 데이터셋
    ├── main.py
    └── requirements.txt
```

---

## 배포 서버 정보

### 서버 스펙
| 항목 | 값 |
|------|-----|
| IP 주소 | 5.161.112.248 |
| 위치 | Hetzner Cloud, Germany |
| OS | Ubuntu 22.04 LTS |
| 프로젝트 경로 | `/root/service_c/strategy-research-lab` |

### 실행 중인 서비스

#### 1. API 서버 (strategy-research-lab)
- **포트**: 8081 (외부), 8080 (내부)
- **상태**: ✅ 정상 (Healthy)
- **기능**: REST API, 전략 조회, 백테스트 실행
- **리소스**: CPU 2.0, Memory 2GB

#### 2. 스케줄러 (strategy-scheduler)
- **상태**: ✅ 작동 중
- **기능**: 6시간마다 자동 수집
- **리소스**: CPU 1.5, Memory 1.5GB

### API 엔드포인트

**Base URL**: `http://5.161.112.248:8081`

| 엔드포인트 | 메소드 | 설명 |
|-----------|--------|------|
| `/api/health` | GET | 헬스체크 |
| `/api/stats` | GET | 전략 통계 |
| `/api/strategies` | GET | 전략 목록 (필터, 정렬, 페이징) |
| `/api/strategy/{id}` | GET | 전략 상세 정보 |
| `/api/backtest` | POST | 개별 백테스트 실행 |
| `/api/docs` | GET | Swagger API 문서 |

### 배포 방법 (GitHub Actions 자동)

**⚠️ 중요**: 모든 코드 수정은 **로컬에서만** 진행하고 GitHub에 푸시

```bash
# 로컬에서 코드 수정
cd /Users/mr.joo/Desktop/전략연구소/strategy-research-lab

# Git 커밋 및 푸시
git add .
git commit -m "수정 내용 설명"
git push origin main

# GitHub Actions가 자동으로:
# 1. SSH 연결
# 2. 코드 전송 (rsync)
# 3. Docker 빌드
# 4. 컨테이너 재시작
# 5. 헬스체크
```

**소요 시간**: 5-10분

### 서버 관리 명령어

```bash
# 서버 SSH 접속
ssh root@5.161.112.248

# Docker 컨테이너 상태 확인
docker compose -f /root/service_c/strategy-research-lab/docker-compose.yml ps

# 로그 확인
docker compose -f /root/service_c/strategy-research-lab/docker-compose.yml logs -f scheduler

# 컨테이너 재시작
docker compose -f /root/service_c/strategy-research-lab/docker-compose.yml restart

# 헬스체크
curl http://localhost:8081/api/health
```

---

## 빠른 시작

### 로컬 개발 환경 설정

```bash
# 1. 프로젝트 클론 (또는 로컬 경로 이동)
cd /Users/mr.joo/Desktop/전략연구소/strategy-research-lab

# 2. 가상환경 생성 및 활성화
python3.11 -m venv venv
source venv/bin/activate  # macOS/Linux

# 3. 의존성 설치
pip install -r requirements.txt

# 4. Playwright 브라우저 설치
playwright install chromium

# 5. 환경 변수 설정
cp .env.example .env
# .env 파일 편집 (ANTHROPIC_API_KEY 설정)

# 6. API 서버 실행
python api/server.py
# → http://localhost:8080/api/docs

# 7. 수집기 실행 (단일 실행)
python scripts/auto_collector_service.py --once
```

### 백테스트 엔진 사용

```bash
cd /Users/mr.joo/Desktop/전략연구소/trading-agent-system

# 데이터 로드 테스트
python -c "from src.data.binance_collector import BinanceDataCollector; \
           collector = BinanceDataCollector(); \
           df = collector.load_dataset('BTCUSDT', '1h'); \
           print(f'Loaded {len(df)} rows')"

# 대화형 모드 (전체 파이프라인)
python main.py
```

---

## 주요 기능

### 1. 자동 전략 수집

**수집 기준**:
- 최소 부스트: 500개 이상
- 오픈소스 전략만
- Pine Script 코드 공개

**수집 주기**: 6시간마다 자동 (스케줄러)

### 2. AI 품질 분석

**분석 항목**:
| 항목 | 점수 범위 | 설명 |
|------|-----------|------|
| 코드 품질 | 0-100 | 코드 구조, 가독성 |
| 성능 품질 | 0-100 | 백테스트 결과 |
| 리페인팅 점수 | 0-100 | 미래 데이터 참조 여부 (100 = 안전) |
| 과적합 점수 | 0-100 | 과최적화 여부 (100 = 안전) |

**등급 기준**:
- A: 80점 이상 (최고 품질) → 현재 0개
- B: 70-79점 (우수) → **3개** ✅
- C: 60-69점 (양호) → 37개
- D: 50-59점 (보통) → 16개
- F: 50점 미만 (부적합) → 7개

### 3. Pine Script → Python 변환

**변환 방식**:
1. **Rule-based**: 기본 패턴 매칭 (빠름)
2. **AI 에이전트**: LLM 기반 변환 (정확)

**출력 형식**: backtesting.py 호환 Python 클래스

### 4. 대규모 백테스트

**데이터셋**: 75개
- 25개 심볼 (BTC, ETH, SOL 등)
- 3개 타임프레임 (1h, 4h, 1d)
- 기간: 2023-01-01 ~ 2026-01-03 (3년)

**성과 지표**:
- Total Return (%)
- Sharpe Ratio
- Profit Factor
- Max Drawdown (%)
- Win Rate (%)
- Total Trades

### 5. 텔레그램 알림 (옵션)

**알림 종류**:
- 수집 시작/완료
- 상위 전략 알림
- 백테스트 결과 (수익률 20% 이상)
- 오류 알림
- 서버 상태 (24시간마다)

**설정 방법**:
```bash
# .env 파일에 추가
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# 컨테이너 재시작
docker compose restart scheduler
```

---

## 현재 상태

### 완료된 마일스톤

| 마일스톤 | 내용 | 상태 | 완료율 |
|---------|------|------|--------|
| M1 | 기본 파이프라인 (수집→분석→변환) | ✅ | 100% |
| M2 | AI 에이전트 시스템 (4개 에이전트) | ✅ | 100% |
| M3 | 백테스트 인프라 (데이터+엔진) | ✅ | 100% |
| M4 | 파이프라인 자동화 | ✅ | 100% |
| M5 | 최적화 및 안정화 | 🚧 | 80% |

### M5 완료 항목 (80%)

✅ **완료**:
1. 서버 배포 (Docker Compose)
2. GitHub Actions CI/CD
3. 86개 전략 수집
4. 63개 전략 분석 (B등급 3개 선정)
5. 75개 백테스트 데이터셋
6. HTML 리포트 생성
7. 텔레그램 알림 시스템
8. B등급 전략 #1 백테스트 (PMax)

⏳ **진행 필요** (20%):
1. B등급 전략 #2, #3 백테스트
2. 통합 파이프라인 Import 문제 해결
3. 웹 대시보드 배포 (Nginx 설정)
4. 성능 최적화

### 주요 발견 사항

#### 1. 전략 품질 현실
- **실거래 가능 전략**: 4.8% (3/63개)
- **리스크 관리 부재**: 90.5% (57/63개)
- **Repainting 위험**: 31.8% (20/63개)

#### 2. TradingView 점수 ≠ 실제 성과
- **PMax 전략**: TradingView 72.2점 → 실제 Sharpe -0.08
- **교훈**: 백테스트 검증 필수

#### 3. 타임프레임 의존성
- **1h 타임프레임**: 대부분 손실 (-35%~-50%)
- **4h 타임프레임**: 일부 수익 (+4%~+153%)
- **최적 조합**: SOLUSDT 4h (+153.79%, PF 2.37)

---

## 다음 단계

### 우선순위 높음 (즉시 실행)

1. **B등급 전략 #2, #3 백테스트** (2시간)
   - Adaptive ML Trailing Stop (70.2점)
   - Heikin Ashi Wick (70.0점)
   - 각 10개 데이터셋 테스트
   - 3개 전략 비교 분석

2. **통합 파이프라인 실행** (1시간)
   - Import 문제 해결
   - 엔드투엔드 테스트
   - 1-2개 샘플 전략

3. **웹 대시보드 배포** (30분)
   - Nginx 설정 (정적 파일 서빙)
   - HTML 리포트 자동 갱신
   - http://5.161.112.248:8081/ 접근 가능

### 우선순위 중간

4. **C등급 전략 개선** (선택)
   - 37개 C등급에 리스크 관리 추가
   - B등급으로 업그레이드 시도

5. **성능 최적화**
   - 병렬 처리 개선
   - 메모리 사용량 모니터링
   - 데이터베이스 인덱싱

### 우선순위 낮음

6. **모니터링 대시보드**
   - Prometheus + Grafana (선택)
   - 실시간 메트릭 수집

---

## 트러블슈팅

### 문제 1: 스케줄러 컨테이너 Unhealthy

**증상**:
```bash
docker compose ps
# STATUS: Unhealthy
```

**원인**: 데이터베이스 아직 생성 안 됨 (수집 진행 중)

**해결**: 정상 상태입니다. 수집 완료 후 자동 정상화

### 문제 2: API 응답 없음 (504)

**증상**:
```bash
curl http://5.161.112.248:8081/api/health
# (504 Gateway Timeout)
```

**해결**:
```bash
# 컨테이너 재시작
ssh root@5.161.112.248
docker compose -f /root/service_c/strategy-research-lab/docker-compose.yml restart strategy-lab

# 포트 확인
netstat -tlnp | grep 8081
```

### 문제 3: GitHub Actions 배포 실패

**증상**:
```bash
gh run list
# ✗ Deploy to Production (failed)
```

**해결**:
```bash
# 워크플로우 로그 확인
gh run view

# SSH 키 확인
gh secret list | grep SSH

# 수동 재실행
gh run rerun <run_id>
```

### 문제 4: 수집기가 0개 전략 수집

**증상**: `✅ 수집 완료: 0개 전략`

**원인**: TradingView 접근 차단, 필터 변경

**해결**:
```bash
# 로컬에서 Headless 해제
# .env 파일:
HEADLESS=false

# 브라우저 동작 확인
python scripts/auto_collector_service.py --once

# Rate Limit 조정
RATE_LIMIT_DELAY=2.0  # 1초 → 2초
```

### 문제 5: 데이터베이스 잠금

**증상**: `sqlite3.OperationalError: database is locked`

**해결**: 이미 aiosqlite로 해결됨. 발생 시:
```bash
# 스케줄러 임시 중지
docker stop strategy-scheduler

# DB 작업 완료 후 재시작
docker start strategy-scheduler
```

---

## 빠른 참조

### API 테스트 명령어

```bash
# 헬스체크
curl http://5.161.112.248:8081/api/health

# 통계
curl http://5.161.112.248:8081/api/stats

# A등급 전략 조회
curl "http://5.161.112.248:8081/api/strategies?grade=A&limit=10"

# API 문서 (브라우저)
open http://5.161.112.248:8081/api/docs
```

### Git 작업 명령어

```bash
# 상태 확인
git status

# 변경사항 확인
git diff

# 커밋 및 푸시
git add .
git commit -m "메시지"
git push origin main

# 최근 커밋 확인
git log -1
```

### Docker 관리 명령어

```bash
# 컨테이너 상태
docker compose ps

# 로그 확인
docker compose logs -f scheduler

# 재시작
docker compose restart

# 중지
docker compose down

# 시작
docker compose up -d
```

---

## 기술 스택

### Backend
- **언어**: Python 3.11
- **프레임워크**: FastAPI, asyncio
- **AI/LLM**: Anthropic Claude 3.5 Sonnet
- **데이터베이스**: SQLite, aiosqlite
- **스크래핑**: Playwright (Chromium)
- **백테스트**: backtesting.py, pandas, numpy

### 인프라
- **서버**: Ubuntu 22.04 LTS
- **컨테이너**: Docker + Docker Compose
- **CI/CD**: GitHub Actions
- **알림**: Telegram Bot API

### 주요 라이브러리
- anthropic (Claude API)
- playwright (웹 스크래핑)
- fastapi (REST API)
- backtesting (백테스트)
- ccxt (거래소 데이터)
- pandas (데이터 분석)
- pydantic (데이터 검증)

---

## 연락처 및 문서

### 주요 링크
- **API 문서**: http://5.161.112.248:8081/api/docs
- **GitHub**: (설정 필요)
- **서버**: ssh root@5.161.112.248

### 추가 문서
- **배포 가이드**: 핵심.md
- **프로젝트 상태**: strategy-research-lab/STATUS.md
- **서버 점검 보고서**: SERVER_HEALTH_CHECK_20260104.md

---

**프로젝트 버전**: 5.1
**총 코드 라인**: ~15,000+
**마지막 업데이트**: 2026-01-04
**상태**: ✅ 운영 중
