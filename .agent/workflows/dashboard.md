---
description: 통합 대시보드(Integrated Dashboard) 시작 및 관리 방법
---

# 통합 대시보드(Integrated Dashboard) 가이드

이 워크플로우는 **전략연구소의 핵심 진입점**인 통합 대시보드를 구동하고 관리하는 절차를 설명합니다.
다른 AI 에이전트나 관리자가 시스템을 파악할 때 **이 문서를 최우선으로 참조**하십시오.

---

## 1. 시스템 개요

### 1.1 아키텍처 구성도

```
┌─────────────────────────────────────────────────────────────┐
│                    통합 대시보드 (8080)                      │
│              http://localhost:8080                          │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  strategy-research-lab/api/server.py (FastAPI)      │   │
│  │  └── data/integrated_dashboard.html (프론트엔드)    │   │
│  └─────────────────────────────────────────────────────┘   │
└────────────────────┬───────────────────┬───────────────────┘
                     │                   │
     ┌───────────────▼───┐       ┌───────▼───────────────┐
     │  FreqControl      │       │  FreqBacktest         │
     │  (8081)           │       │  (8082)               │
     │  실시간 트레이딩   │       │  백테스트 전용        │
     └───────────────────┘       └───────────────────────┘
```

### 1.2 서비스 목록

| 서비스명 | 포트 | 역할 | 로그인 |
|----------|------|------|--------|
| **통합 대시보드** | 8080 | 메인 커맨드 센터 (Freqtrade, AI 분석, 뉴스 통합) | - |
| **FreqControl** | 8081 | Freqtrade 실시간 트레이딩 봇 (FreqUI) | admin / admin |
| **FreqBacktest** | 8082 | Freqtrade 백테스트 전용 서버 (FreqUI) | admin / admin |

---

## 2. 서비스 실행 방법

### 2.1 전체 서비스 한 번에 실행 (권장)

```bash
# 프로젝트 루트에서 실행
./scripts/start_all_services.sh
```

이 스크립트는 다음 서비스를 순차적으로 실행합니다:
1. 통합 대시보드 API (8080)
2. Freqtrade 트레이딩 봇 (8081)
3. Freqtrade 백테스트 서버 (8082)

### 2.2 전체 서비스 종료

```bash
./scripts/stop_all_services.sh
```

### 2.3 개별 서비스 실행 (수동)

#### 통합 대시보드 (8080)
```bash
cd strategy-research-lab
APP_BASE_DIR=$(pwd) python api/server.py
```

#### Freqtrade 트레이딩 봇 (8081)
```bash
cd freqtrade
freqtrade trade --config config.json --strategy SampleStrategy
```

#### Freqtrade 백테스트 서버 (8082)
```bash
cd freqtrade
freqtrade webserver --config config_backtest_server.json
```

---

## 3. 주요 파일 경로

### 3.1 백엔드
| 파일 | 설명 |
|------|------|
| `strategy-research-lab/api/server.py` | 통합 대시보드 FastAPI 서버 |
| `freqtrade/config.json` | Freqtrade 트레이딩 설정 (8081) |
| `freqtrade/config_backtest_server.json` | Freqtrade 백테스트 설정 (8082) |

### 3.2 프론트엔드
| 파일 | 설명 |
|------|------|
| `strategy-research-lab/data/integrated_dashboard.html` | 통합 대시보드 메인 UI |

### 3.3 스크립트
| 파일 | 설명 |
|------|------|
| `scripts/start_all_services.sh` | 전체 서비스 시작 |
| `scripts/stop_all_services.sh` | 전체 서비스 종료 |

---

## 4. API 엔드포인트 목록

### 4.1 Core APIs
| 엔드포인트 | 메서드 | 설명 |
|------------|--------|------|
| `/api/health` | GET | 서버 상태 확인 |
| `/api/stats` | GET | 전략 통계 |
| `/api/strategies` | GET | 전략 목록 |
| `/api/live/status` | GET | 실시간 트레이딩 상태 |

### 4.2 Freqtrade 연동
| 엔드포인트 | 메서드 | 설명 |
|------------|--------|------|
| `/api/freqtrade/status` | GET | Freqtrade 봇 상태 |
| `/api/freqtrade/strategies` | GET | 등록된 전략 목록 |

### 4.3 Intelligence (AI 분석)
| 엔드포인트 | 메서드 | 설명 |
|------------|--------|------|
| `/api/intelligence/sentiment` | GET | AI 감성 분석 |
| `/api/intelligence/news` | GET | 매크로 뉴스 |

### 4.4 Trades
| 엔드포인트 | 메서드 | 설명 |
|------------|--------|------|
| `/api/trades/statistics` | GET | 거래 통계 |
| `/api/trades/recent` | GET | 최근 거래 내역 |

---

## 5. 대시보드 탭 구성

| 탭 이름 | 기능 |
|---------|------|
| **대시보드** | 종합 상태, 손익, 승률, 상위 전략 |
| **마켓 인텔리전스** | AI 감성 분석, 매크로 뉴스 |
| **실전매매** | 거래 내역, 긴급 정지 버튼 |
| **FreqControl** | Freqtrade 실시간 트레이딩 (iframe → 8081) |
| **FreqBacktest** | Freqtrade 백테스트 (iframe → 8082) |
| **Hummingbot** | 시장 조성 엔진 (8501 연동) |
| **CryptoVision** | HuggingFace AI 분석 |
| **전략 탐색** | 수집된 전략 검색/필터링 |
| **Pine 백테스트** | TradingView 전략 백테스트 |

---

## 6. 문제 해결

### 6.1 페이지가 빈 화면으로 표시되는 경우

**원인**: 해당 포트의 서비스가 실행되지 않음

**해결**:
```bash
# 모든 서비스 재시작
./scripts/stop_all_services.sh
./scripts/start_all_services.sh
```

### 6.2 특정 포트 확인
```bash
# 8080 포트 확인
lsof -i :8080

# 8081 포트 확인
lsof -i :8081

# 8082 포트 확인
lsof -i :8082
```

### 6.3 개별 서비스 상태 확인
```bash
# 통합 대시보드
curl http://localhost:8080/api/health

# Freqtrade 트레이딩
curl http://localhost:8081/api/v1/ping

# Freqtrade 백테스트
curl http://localhost:8082/api/v1/ping
```

---

## 7. 외부 연동 서비스 (선택사항)

| 서비스 | 포트 | 설명 | 실행 방법 |
|--------|------|------|-----------|
| Hummingbot | 8501 | 시장 조성 봇 | Docker 또는 수동 실행 |

---

**업데이트 날짜**: 2026-01-19
**작성**: Claude (Anthropic)
