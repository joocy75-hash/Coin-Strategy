# 🦅 Trading Strategy Research Lab - System Architecture

본 문서는 대시보드 및 백테스트 시스템의 구조와 설정을 다음 작업자가 쉽게 이해하고 유지보수할 수 있도록 설명합니다.

## 1. 프로젝트 구조 (System Overview)

시스템은 크게 세 가지 주요 컴포넌트로 구성되어 있습니다.

### A. 통합 대시보드 (Frontend)

- **파일 경로**: `strategy-research-lab/data/integrated_dashboard.html`
- **역할**: 사용자 인터페이스 제공 (Enamel Black 테마).
- **주요 기능**:
  - 실시간 매매 상태 모니터링
  - Freqtrade 봇 제어 및 백테스트 UI 임베딩
  - Pine Script 전략 탐색 및 연구소 백테스트 실행
  - 자동 생성된 HTML 리포트 열람

### B. 연구소 API 서버 (Backend)
- **파일 경로**: `strategy-research-lab/api/server.py`
- **실행 포트**: `8080`
- **기술 스택**: FastAPI, SQLite, Pydantic
- **핵심 역할**:
  - 전략 데이터베이스 관리 (`strategies.db`)
  - Pine Script → Python 변환 엔진 연동
  - 백테스트 실행 유도 및 HTML 리포트 자동 생성
  - Freqtrade API와의 통신 중계

### C. Freqtrade 시스템 (Engine)
- **매매 봇 (Port 8081)**: 실시간 매매 수행 및 FreqUI 제공.
- **백테스트 전용 서버 (Port 8082)**: 독립된 환경에서 전략 검증 및 시각화 수행.
- **설정 파일**: `config.json` (매매용), `config_backtest.json` (백테스트 서버용).

---

## 2. 주요 설정 (Configuration)

### 포트 할당 표
| 서비스명 | 포트 | 역할 |
| :--- | :--- | :--- |
| **Main API** | `8080` | 대시보드 서빙 및 연구소 핵심 기능 |
| **FreqControl** | `8081` | 실시간 매매 봇 인터페이스 |
| **FreqBacktest** | `8082` | 독립 백테스트 분석 서버 |
| **Hummingbot** | `8501` | AMM / Arbitrage 전략 대시보드 |

### 인증 정보 (Default)
- **Username**: `admin`
- **Password**: `admin`
- **인증 방식**: Basic Auth 및 JWT 토큰 (FreqUI 연동 시)

---

## 3. 작업자 가이드 (Maintenance Guide)

1. **디자인 테마 수정**: 
   `integrated_dashboard.html` 내의 CSS `:root` 변수를 통해 색상을 관리합니다. 현재 **Enamel Black** 테마가 적용되어 있습니다.

2. **백테스트 리포트 생성 로직**:
   `server.py`의 `run_backtest` 엔드포인트에서 HTML 템플릿을 생성합니다. 차트 시각화를 수정하려면 해당 섹션의 `Chart.js` 코드를 수정하십시오.

3. **중복 파일 주의**:
   현재 시스템은 `integrated_dashboard.html`로 통합되었습니다. `templates/` 폴더 내의 파일들이나 루트의 개별 html 파일은 더 이상 사용되지 않으므로 생성하지 않도록 주의하십시오.

---

## 4. 🚨 보안 개선 권고 사항 (Security Hardening)

현재 시스템은 개발 및 로컬 테스트 환경에 최적화되어 있어, 실전 배포 시 다음 사항을 반드시 개선해야 합니다.

### 1단계: API 노출 제한
- **현재**: CORS가 `*`로 열려 있고, 모든 포트가 외부에 노출되어 있습니다.
- **개선**: **Nginx** 또는 **Traefik** 같은 리버스 프록시를 앞에 두고, `80` 또는 `443` 포트 하나로 모든 통신을 통합하십시오. 나머지 포트는 로컬호스트(`127.0.0.1`)에서만 접근 가능하도록 방화벽 설정을 해야 합니다.

### 2단계: 인증 시스템 강화
- **현재**: `admin/admin` 고정 계정을 사용하며, 대시보드 페이지 자체에 대한 접근 제어가 약합니다.
- **개선**: 대시보드 진입 시 별도의 **JWT 기반 로그인 페이지**를 구현하고, 하드코딩된 비밀번호를 `.env` 파일 또는 시스템 환경 변수로 분리하십시오.

### 3단계: 통신 보안 (HTTPS)
- **현재**: 모든 데이터가 평문(HTTP)으로 전송됩니다. API 키나 거래 정보가 탈취될 수 있습니다.
- **개선**: SSL 인증서를 적용하여 **HTTPS** 통신을 필수화하십시오.

### 4단계: API 키 관리
- **현재**: 바이낸스 등 거래소 API 키가 설정 파일에 평문으로 존재할 수 있습니다.
- **개선**: **AWS Secrets Manager**나 가상환경 변수를 사용하고, `config.json` 자체가 Git에 올라가지 않도록 `.gitignore` 설정을 철저히 하십시오.
