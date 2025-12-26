# TradingView Strategy Research Lab - 배포 가이드

> 최종 업데이트: 2025-12-27
> 작성자: Claude Code (자동 생성)

---

## 목차

1. [시스템 아키텍처](#1-시스템-아키텍처)
2. [서버 정보](#2-서버-정보)
3. [프로젝트 구조](#3-프로젝트-구조)
4. [로컬 개발 환경](#4-로컬-개발-환경)
5. [자동 배포 (CI/CD)](#5-자동-배포-cicd)
6. [수동 배포 방법](#6-수동-배포-방법)
7. [Docker 설정](#7-docker-설정)
8. [API 엔드포인트](#8-api-엔드포인트)
9. [트러블슈팅](#9-트러블슈팅)
10. [보안 설정](#10-보안-설정)

---

## 1. 시스템 아키텍처

### 전체 서버 그룹 구성

Hetzner 서버(5.161.112.248)는 3개의 서비스 그룹으로 구성됩니다:

```
┌─────────────────────────────────────────────────────────────┐
│                    Hetzner Server                           │
│                  5.161.112.248 (deep-server)                │
│                  Ubuntu 24.04 LTS                           │
│                  4 vCPU / 8 GB RAM / 160 GB SSD             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐ │
│  │   Group A       │  │   Group B       │  │  Group C    │ │
│  │   Freqtrade     │  │   Personal      │  │  AI Trading │ │
│  │                 │  │   Automation    │  │  Platform   │ │
│  ├─────────────────┤  ├─────────────────┤  ├─────────────┤ │
│  │ Port: 8080      │  │ Port: 5001      │  │ Port: 8081  │ │
│  │ FreqUI: 3000    │  │ (Sports)        │  │             │ │
│  │                 │  │                 │  │             │ │
│  │ ~/service_a/    │  │ ~/service_b/    │  │~/service_c/ │ │
│  └─────────────────┘  └─────────────────┘  └─────────────┘ │
│                                                             │
│  Network: group_a_net   group_b_net      group_c_network   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Group C 상세 구조 (이 프로젝트)

```
Group C: Strategy Research Lab
├── strategy-research-lab (API 서버)
│   ├── Port: 8081 (외부) → 8080 (내부)
│   ├── Memory: 2GB limit
│   └── Role: REST API 제공
│
└── strategy-scheduler (자동 수집기)
    ├── Port: 없음 (내부 서비스)
    ├── Memory: 1.5GB limit
    └── Role: 주기적 전략 수집
```

---

## 2. 서버 정보

### 접속 정보

| 항목 | 값 |
|------|-----|
| IP 주소 | `5.161.112.248` |
| 서버명 | `deep-server` |
| 위치 | Ashburn, VA (USA) |
| OS | Ubuntu 24.04 LTS |
| 사양 | CPX31 (4 vCPU / 8 GB RAM / 160 GB SSD) |

### SSH 접속

```bash
# 일반 접속
ssh root@5.161.112.248

# SSH 키 사용 시 (GitHub Actions용 키)
ssh -i ~/.ssh/github_actions root@5.161.112.248
```

### 서버 디렉토리 구조

```
/root/
├── service_a/          # Freqtrade
├── service_b/          # Personal Automation
└── service_c/          # ★ Strategy Research Lab (이 프로젝트)
    └── strategy-research-lab/
        ├── api/
        ├── src/
        ├── scripts/
        ├── data/        # Docker 볼륨 (영구 데이터)
        ├── logs/        # Docker 볼륨 (로그)
        ├── .env         # 환경 변수 (서버 전용)
        ├── docker-compose.yml
        └── Dockerfile
```

---

## 3. 프로젝트 구조

```
strategy-research-lab/
├── .github/
│   └── workflows/
│       └── deploy.yml          # GitHub Actions 자동 배포
│
├── api/
│   ├── __init__.py
│   └── server.py               # FastAPI 서버 (메인)
│
├── src/
│   ├── analyzer/               # 전략 분석기
│   │   ├── llm/               # LLM 기반 분석
│   │   ├── rule_based/        # 규칙 기반 분석
│   │   └── scorer.py          # 점수 계산
│   │
│   ├── backtester/            # 백테스팅 엔진
│   │   ├── backtest_engine.py
│   │   ├── data_collector.py  # ccxt 사용
│   │   └── strategy_tester.py
│   │
│   ├── collector/             # TradingView 수집기
│   │   ├── scripts_scraper.py # Playwright 스크래퍼
│   │   ├── pine_fetcher.py    # Pine Script 가져오기
│   │   └── session_manager.py
│   │
│   ├── converter/             # Pine → Python 변환
│   │   ├── pine_to_python.py
│   │   └── templates/
│   │
│   └── storage/               # 데이터 저장
│       └── database.py        # SQLite
│
├── scripts/
│   ├── auto_collector_service.py  # 스케줄러 서비스
│   ├── run_collector.py
│   └── generate_report.py
│
├── tests/                     # 테스트
│
├── data/                      # 데이터 (git 제외)
│   ├── strategies.db          # SQLite DB
│   ├── converted/             # 변환된 전략
│   └── reports/               # 생성된 리포트
│
├── logs/                      # 로그 (git 제외)
│
├── .env                       # 환경변수 (git 제외)
├── .env.example               # 환경변수 예시
├── .gitignore
├── .dockerignore
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── DEPLOYMENT.md              # ★ 이 문서
```

---

## 4. 로컬 개발 환경

### 필수 요구사항

- Python 3.10+
- Docker & Docker Compose
- Git
- GitHub CLI (`gh`) - CI/CD 관리용

### 로컬 설정

```bash
# 1. 저장소 클론
git clone https://github.com/joocy75-hash/TradingView-Strategy.git
cd TradingView-Strategy

# 2. 가상환경 생성 (선택)
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. 의존성 설치
pip install -r requirements.txt

# 4. Playwright 브라우저 설치
playwright install chromium

# 5. 환경변수 설정
cp .env.example .env
# .env 파일에서 ANTHROPIC_API_KEY 설정

# 6. 로컬 실행
python api/server.py
# http://localhost:8080/api/docs 에서 확인
```

### 환경변수 (.env)

```env
# API Keys
ANTHROPIC_API_KEY=sk-ant-api03-xxxxx  # 필수

# Database
DB_PATH=data/strategies.db

# Scraping Settings
MAX_STRATEGIES=50
MIN_LIKES=500
HEADLESS=true
TIMEOUT=30000

# Analysis Settings
LLM_MODEL=claude-3-5-sonnet-20241022
SKIP_LLM=false
MAX_RETRIES=3

# Output Paths
OUTPUT_DIR=data/converted
LOGS_DIR=logs

# Rate Limiting
RATE_LIMIT_DELAY=1.0
```

---

## 5. 자동 배포 (CI/CD)

### 배포 흐름

```
┌──────────────────────────────────────────────────────────────┐
│                     자동 배포 파이프라인                      │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  1. 로컬에서 코드 수정                                        │
│           ↓                                                  │
│  2. git commit && git push (main 브랜치)                     │
│           ↓                                                  │
│  3. GitHub Actions 트리거 (.github/workflows/deploy.yml)     │
│           ↓                                                  │
│  4. SSH 키로 서버 접속 (SSH_PRIVATE_KEY secret 사용)          │
│           ↓                                                  │
│  5. .env 파일 생성 (ANTHROPIC_API_KEY secret 사용)           │
│           ↓                                                  │
│  6. rsync로 파일 동기화 (data/, logs/, .env 제외)            │
│           ↓                                                  │
│  7. docker compose build --no-cache                          │
│           ↓                                                  │
│  8. docker compose up -d                                     │
│           ↓                                                  │
│  9. Health Check (http://서버:8081/api/health)               │
│           ↓                                                  │
│  10. 성공/실패 알림                                           │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### GitHub Secrets 설정

GitHub 리포지토리 → Settings → Secrets and variables → Actions

| Secret 이름 | 설명 | 값 |
|------------|------|-----|
| `SSH_PRIVATE_KEY` | 서버 접속용 SSH 개인키 | 서버의 `~/.ssh/github_actions` |
| `ANTHROPIC_API_KEY` | Claude API 키 | `sk-ant-api03-xxxxx` |

### SSH 키 재생성 (필요시)

```bash
# 서버에서 실행
ssh root@5.161.112.248

# 새 키 생성
ssh-keygen -t ed25519 -f ~/.ssh/github_actions -N '' -C 'github-actions-deploy'

# authorized_keys에 추가
cat ~/.ssh/github_actions.pub >> ~/.ssh/authorized_keys

# 개인키 확인 (이 값을 GitHub Secret에 복사)
cat ~/.ssh/github_actions
```

### 배포 상태 확인

```bash
# GitHub Actions 실행 목록
gh run list --repo joocy75-hash/TradingView-Strategy --limit 5

# 특정 실행의 로그 확인
gh run view <RUN_ID> --repo joocy75-hash/TradingView-Strategy --log

# 실패한 배포 재실행
gh run rerun <RUN_ID> --repo joocy75-hash/TradingView-Strategy
```

### 워크플로우 수동 트리거

```bash
# GitHub에서 수동으로 배포 실행
gh workflow run deploy.yml --repo joocy75-hash/TradingView-Strategy
```

---

## 6. 수동 배포 방법

자동 배포가 실패하거나 긴급 배포가 필요할 때:

### 방법 1: rsync로 직접 배포

```bash
# 로컬에서 실행
cd /path/to/strategy-research-lab

# 파일 동기화
rsync -avz --delete \
  --exclude '.git' \
  --exclude '.github' \
  --exclude '__pycache__' \
  --exclude '*.pyc' \
  --exclude '.pytest_cache' \
  --exclude 'venv' \
  --exclude '.env' \
  --exclude 'data/' \
  --exclude 'logs/' \
  ./ root@5.161.112.248:/root/service_c/strategy-research-lab/

# 서버에서 재빌드
ssh root@5.161.112.248 "cd /root/service_c/strategy-research-lab && \
  docker compose down && \
  docker compose build --no-cache && \
  docker compose up -d"
```

### 방법 2: 서버에서 직접 수정

```bash
# 서버 접속
ssh root@5.161.112.248

# 프로젝트 디렉토리로 이동
cd /root/service_c/strategy-research-lab

# 파일 수정 후 재시작
docker compose down
docker compose build --no-cache
docker compose up -d

# 로그 확인
docker compose logs -f
```

---

## 7. Docker 설정

### Dockerfile 설명

```dockerfile
# Python 3.11 slim 이미지 사용
FROM python:3.11-slim AS base

# 시스템 의존성 설치 (Playwright용)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl wget gnupg ca-certificates \
    fonts-liberation libasound2 libatk-bridge2.0-0 ...

# Python 패키지 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Playwright Chromium 설치
RUN playwright install chromium --with-deps

# 애플리케이션 코드 복사
COPY . .

# 포트 노출 및 헬스체크
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8080/api/health || exit 1

# 실행
CMD ["python", "api/server.py"]
```

### docker-compose.yml 설명

```yaml
services:
  # API 서버
  strategy-lab:
    build: .
    container_name: strategy-research-lab
    restart: always
    ports:
      - "8081:8080"  # 외부:내부 (8080은 Freqtrade가 사용)
    environment:
      - TZ=Asia/Seoul
    env_file:
      - .env
    volumes:
      - ./data:/app/data    # 데이터 영구 저장
      - ./logs:/app/logs    # 로그 영구 저장
    networks:
      - group_c_network
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 2G        # 최대 2GB
        reservations:
          memory: 512M      # 최소 512MB

  # 스케줄러 (자동 수집)
  scheduler:
    build: .
    container_name: strategy-scheduler
    restart: always
    command: ["python", "scripts/auto_collector_service.py"]
    depends_on:
      strategy-lab:
        condition: service_healthy
    deploy:
      resources:
        limits:
          memory: 1536M     # 최대 1.5GB

networks:
  group_c_network:
    external: true          # 미리 생성된 네트워크 사용
```

### Docker 명령어 모음

```bash
# 서버 접속 후
cd /root/service_c/strategy-research-lab

# 컨테이너 상태 확인
docker compose ps

# 로그 확인
docker compose logs -f                    # 전체 로그
docker compose logs strategy-lab -f       # API 로그만
docker compose logs scheduler -f          # 스케줄러 로그만

# 컨테이너 재시작
docker compose restart

# 컨테이너 중지/시작
docker compose down
docker compose up -d

# 이미지 재빌드 (코드 변경 후)
docker compose build --no-cache
docker compose up -d

# 리소스 사용량 확인
docker stats strategy-research-lab strategy-scheduler

# 컨테이너 내부 접속
docker exec -it strategy-research-lab /bin/bash

# 불필요한 이미지/캐시 정리
docker system prune -af
```

---

## 8. API 엔드포인트

### 기본 URL

- **Production**: http://5.161.112.248:8081
- **API 문서**: http://5.161.112.248:8081/api/docs
- **ReDoc**: http://5.161.112.248:8081/api/redoc

### 엔드포인트 목록

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/api/health` | 헬스 체크 |
| GET | `/api/stats` | 통계 정보 |
| GET | `/api/strategies` | 전략 목록 |
| GET | `/api/strategy/{script_id}` | 전략 상세 |
| POST | `/api/backtest` | 백테스트 실행 |
| POST | `/api/backtest/all` | 전체 백테스트 |
| GET | `/api/strategy/{script_id}/backtest` | 백테스트 결과 |
| GET | `/` | 메인 페이지 (리포트) |
| GET | `/report.html` | 일반 리포트 |

### API 테스트 예시

```bash
# 헬스 체크
curl http://5.161.112.248:8081/api/health

# 통계 조회
curl http://5.161.112.248:8081/api/stats

# 전략 목록 (상위 10개)
curl "http://5.161.112.248:8081/api/strategies?limit=10"

# 특정 전략 상세
curl http://5.161.112.248:8081/api/strategy/SCRIPT_ID
```

---

## 9. 트러블슈팅

### 문제 1: 배포 실패 - SSH 키 오류

```
Load key "/home/runner/.ssh/id_rsa": error in libcrypto
Permission denied (publickey,password)
```

**해결책:**
1. GitHub Secrets에서 `SSH_PRIVATE_KEY` 값 확인
2. 서버에서 키 재생성 후 Secrets 업데이트

```bash
# 서버에서
cat ~/.ssh/github_actions  # 이 값을 GitHub Secret에 복사
```

### 문제 2: 포트 충돌

```
Bind for 0.0.0.0:8080 failed: port is already allocated
```

**해결책:**
- docker-compose.yml에서 포트 변경 (현재 8081 사용)
- 또는 기존 컨테이너 중지

```bash
docker ps -q --filter 'publish=8080' | xargs -r docker stop
```

### 문제 3: 모듈 없음 오류

```
ModuleNotFoundError: No module named 'ccxt'
```

**해결책:**
- requirements.txt에 누락된 패키지 추가
- Docker 이미지 재빌드

```bash
docker compose build --no-cache
docker compose up -d
```

### 문제 4: 헬스 체크 실패

```
Health check returned: 000
```

**해결책:**
1. 컨테이너 로그 확인
```bash
docker compose logs strategy-lab --tail=50
```

2. 컨테이너 내부에서 직접 확인
```bash
docker exec strategy-research-lab curl localhost:8080/api/health
```

### 문제 5: 메모리 부족

```
Container killed due to OOM
```

**해결책:**
- docker-compose.yml에서 메모리 한도 조정
- 서버 Swap 확인

```bash
free -h  # Swap 확인
```

### 로그 확인 위치

| 로그 종류 | 위치 |
|----------|------|
| Docker 로그 | `docker compose logs` |
| 애플리케이션 로그 | `/root/service_c/strategy-research-lab/logs/` |
| GitHub Actions | GitHub → Actions 탭 |

---

## 10. 보안 설정

### 방화벽 (UFW)

```bash
# 현재 규칙 확인
ufw status

# 허용된 포트
# 22/tcp   - SSH
# 80/tcp   - HTTP
# 443/tcp  - HTTPS
# 3000/tcp - FreqUI
# 5001/tcp - Sports Analysis
# 8080/tcp - Freqtrade
# 8081/tcp - Strategy Lab (이 프로젝트)
```

### Fail2Ban

SSH 브루트포스 공격 방지 설정됨

```bash
# 상태 확인
systemctl status fail2ban

# 차단된 IP 확인
fail2ban-client status sshd
```

### 보안 권장사항

1. **SSH 키 관리**
   - 정기적으로 키 교체
   - 사용하지 않는 키 삭제

2. **API 키 관리**
   - .env 파일은 절대 git에 커밋하지 않음
   - GitHub Secrets 사용

3. **Docker 보안**
   - 컨테이너 리소스 제한 설정
   - 불필요한 포트 노출 금지

---

## 부록: 자주 사용하는 명령어

### 로컬

```bash
# Git
git add . && git commit -m "메시지" && git push

# GitHub Actions 상태
gh run list --repo joocy75-hash/TradingView-Strategy --limit 5

# 배포 재실행
gh run rerun <RUN_ID> --repo joocy75-hash/TradingView-Strategy
```

### 서버

```bash
# 접속
ssh root@5.161.112.248

# 프로젝트 이동
cd /root/service_c/strategy-research-lab

# Docker 상태
docker compose ps
docker compose logs -f
docker stats

# 재시작
docker compose restart

# 전체 재빌드
docker compose down && docker compose build --no-cache && docker compose up -d
```

---

## 변경 이력

| 날짜 | 버전 | 변경 내용 |
|------|------|----------|
| 2025-12-27 | 1.0.0 | 최초 작성 |
| 2025-12-27 | 1.1.0 | CI/CD 자동 배포 구축, 포트 8081 변경 |

---

> 문의: GitHub Issues 또는 리포지토리 관리자에게 연락
