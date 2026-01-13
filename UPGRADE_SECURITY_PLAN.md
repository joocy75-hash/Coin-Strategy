# 🔧 TradingView Strategy Research Lab - 업그레이드 및 보안 개선 작업계획서

> 작성일: 2026-01-13  
> 프로젝트: TradingView Strategy Research Lab  
> 서버: 141.164.55.245 (Hetzner Cloud)

---

## 📋 작업 진행 체크리스트

각 작업 완료 시 `[ ]`를 `[x]`로 변경하세요.

---

## 🔴 1단계: 긴급 보안 수정 (Critical)

### 1.1 GitHub Actions 텔레그램 토큰 노출 수정
- **파일**: `.github/workflows/deploy.yml`
- **문제**: 텔레그램 봇 토큰이 하드코딩됨 (라인 95-96)
- **위험도**: 🔴 Critical

**작업 순서**:
- [x] 1.1.1 GitHub Repository → Settings → Secrets에서 `TELEGRAM_BOT_TOKEN` 추가
- [x] 1.1.2 GitHub Repository → Settings → Secrets에서 `TELEGRAM_CHAT_ID` 추가
- [x] 1.1.3 `.github/workflows/deploy.yml` 파일에서 secrets 참조로 수정
- [x] 1.1.4 기존 텔레그램 봇 토큰 재발급 (이미 노출됨)
- [x] 1.1.5 커밋 및 배포 테스트

---

### 1.2 CORS 설정 강화
- **파일**: `api/server.py` (라인 72-78)
- **문제**: `allow_origins=["*"]` - 모든 도메인 허용

**작업 순서**:
- [x] 1.2.1 `api/server.py`에서 CORS 설정을 특정 도메인으로 제한
- [x] 1.2.2 로컬 테스트
- [x] 1.2.3 배포 후 프론트엔드 정상 동작 확인

---

## � 2단계: 중요 보안 개선 (High)

### 2.1 API Rate Limiting 구현
- [x] 2.1.1 `requirements.txt`에 `slowapi>=0.1.9` 추가
- [x] 2.1.2 `api/server.py`에 Rate Limiter 설정 추가
- [x] 2.1.3 주요 엔드포인트에 rate limit 적용
- [x] 2.1.4 테스트 및 배포

### 2.2 API 인증 시스템 구현 (선택)
- [x] 2.2.1 `.env`에 `API_SECRET_KEY` 추가
- [x] 2.2.2 API Key 검증 로직 추가
- [x] 2.2.3 민감한 엔드포인트에 인증 적용

### 2.3 입력값 검증 강화
- [x] 2.3.1 입력값 sanitize 함수 추가
- [x] 2.3.2 search, script_id 파라미터 검증 추가

---

## 🟡 3단계: 코드 품질 개선 (Medium)

### 3.1 빈 파일 구현 또는 제거
- [x] 3.1.1 `encrypted_api_manager.py` 구현 또는 삭제
- [x] 3.1.2 `api_manager.py` 구현 또는 삭제
- [x] 3.1.3 `notification_system.py` 구현 또는 삭제

### 3.2 로깅 시스템 개선
- [x] 3.2.1 로깅 설정 모듈 생성
- [x] 3.2.2 API 서버에 로깅 적용
- [x] 3.2.3 스크래퍼/분석기에 로깅 적용

### 3.3 에러 핸들링 개선
- [x] 3.3.1 전역 예외 핸들러 추가
- [x] 3.3.2 에러 응답 형식 통일

---

## � 4단계: 의존성 및 인프라 (Low)

### 4.1 의존성 버전 업데이트
- [x] 4.1.1 `pip list --outdated` 실행
- [ ] 4.1.2 주요 패키지 업데이트
- [ ] 4.1.3 Docker 이미지 재빌드

### 4.2 Docker 보안 강화
- [x] 4.2.1 Dockerfile에 비root 사용자 추가
- [x] 4.2.2 리소스 제한 추가

### 4.3 테스트 커버리지 확대
- [x] 4.3.1 `tests/test_api.py` 추가 (22개 테스트)
- [x] 4.3.2 `tests/test_collector.py` 추가 (22개 테스트)

---

## 🔵 5단계: 기능 개선 (Enhancement)

### 5.1 대시보드 개선
- [x] 5.1.1 백테스트 차트 섹션 스타일 개선
- [x] 5.1.2 전략 상세 모달 추가

### 5.2 알림 시스템 구현
- [x] 5.2.1 `notification_system.py` 구현
- [x] 5.2.2 새 전략 발견/분석 완료 시 알림

---

## 💰 6단계: 실전매매 시스템 강화 (Live Trading)

> 검증된 전략을 실전매매로 연결하기 위한 필수 보안/안전장치
> 현재 `multi_strategy_bot.py`, `trading_bot.py` 구현되어 있음

### 6.1 API 키 보안 강화
- **파일**: `encrypted_api_manager.py` (현재 빈 파일)
- **문제**: API 키가 `.env`에 평문 저장

**작업 순서**:
- [x] 6.1.1 `requirements.txt`에 `cryptography>=42.0.0`, `keyring>=25.0.0` 추가
- [x] 6.1.2 `encrypted_api_manager.py` 구현 (시스템 키체인 활용)
- [x] 6.1.3 `multi_strategy_bot.py`에서 SecureAPIManager 사용
- [ ] 6.1.4 기존 `.env` API 키 제거 후 암호화 저장

---

### 6.2 실전매매 안전장치 구현
- **파일**: `multi_strategy_bot.py`, `risk_manager.py`

**추가할 안전장치**:
- 최대 포지션 크기 제한 (자본의 10%)
- 일일 최대 손실 제한 (5%)
- 연속 손실 시 자동 정지
- 슬리피지 체크
- 긴급 정지 플래그

**작업 순서**:
- [x] 6.2.1 `LiveTradingSafeguards` 클래스 구현
- [x] 6.2.2 `multi_strategy_bot.py`에 안전장치 통합
- [x] 6.2.3 긴급 정지 API 엔드포인트 추가 (`/api/emergency-stop`)
- [x] 6.2.4 텔레그램 긴급 정지 명령어 추가

---

### 6.3 실시간 모니터링 대시보드
- **파일**: 신규 생성 필요

**작업 순서**:
- [x] 6.3.1 `api/live_trading_endpoints.py` 생성
- [x] 6.3.2 실시간 상태 API 구현 (`/api/live/status`)
- [x] 6.3.3 긴급 정지 API 구현 (인증 필수)
- [x] 6.3.4 대시보드 HTML에 실전매매 섹션 추가
- [ ] 6.3.5 WebSocket 실시간 업데이트 (선택)

---

### 6.4 거래 로그 및 감사 추적
- **용도**: 모든 거래 기록 보관 (법적/세금 목적)

**작업 순서**:
- [x] 6.4.1 `src/trading/trade_logger.py` 생성
- [x] 6.4.2 모든 거래에 로깅 적용
- [x] 6.4.3 CSV 내보내기 기능 구현 (세금 신고용)
- [x] 6.4.4 `/api/trades/export` 엔드포인트 추가

---

### 6.5 Freqtrade 통합 (선택)
- **GitHub**: https://github.com/freqtrade/freqtrade (⭐ 30k+)
- **용도**: 검증된 오픈소스 트레이딩 봇 프레임워크
- **장점**: 텔레그램 UI, 웹 UI, 드라이런 모드, 100+ 거래소 지원

**작업 순서**:
- [ ] 6.5.1 Freqtrade 설치 및 설정
- [ ] 6.5.2 검증된 전략 → Freqtrade 전략 변환기 구현
- [ ] 6.5.3 드라이런 모드로 테스트
- [ ] 6.5.4 텔레그램 봇 연동

---

### 6.6 Paper Trading → Live Trading 전환 체크리스트

**실전매매 전환 전 필수 확인사항**:

- [ ] 6.6.1 Paper Trading에서 최소 2주 이상 테스트 완료
- [ ] 6.6.2 승률 50% 이상, Profit Factor 1.5 이상 확인
- [ ] 6.6.3 최대 드로다운 10% 이하 확인
- [ ] 6.6.4 **API 키 권한 최소화 (출금 권한 제거!)**
- [ ] 6.6.5 **IP 화이트리스트 설정 (거래소)**
- [ ] 6.6.6 긴급 정지 기능 테스트 완료
- [ ] 6.6.7 텔레그램 알림 정상 동작 확인
- [ ] 6.6.8 소액($100)으로 실전 테스트 1주일
- [ ] 6.6.9 점진적 자본 증가 계획 수립

---

## 🚀 7단계: 오픈소스 통합 (Optional)

### 7.1 Pine Script 파서 - pynescript
- **GitHub**: https://github.com/elbakramer/pynescript
- **용도**: Pine Script → AST 파싱, 정적 분석
- **효과**: LLM 비용 절감

**작업 순서**:
- [ ] 7.1.1 `requirements.txt`에 `pynescript>=0.2.0` 추가
- [ ] 7.1.2 `src/analyzer/pine_parser.py` 생성
- [ ] 7.1.3 리페인팅 탐지에 AST 기반 분석 추가

---

### 7.2 고속 백테스팅 - VectorBT
- **GitHub**: https://github.com/polakowo/vectorbt
- **용도**: 대량 전략 백테스트 (10-100배 빠름)

**작업 순서**:
- [ ] 7.2.1 `requirements.txt`에 `vectorbt>=0.26.0` 추가
- [ ] 7.2.2 `src/backtester/vectorbt_engine.py` 생성
- [ ] 7.2.3 파라미터 최적화 기능 추가

---

### 7.3 금융 감성 분석 - FinBERT (Hugging Face)
- **모델**: `ProsusAI/finbert` (월 230만 다운로드)
- **용도**: 전략 설명문 과대광고 탐지
- **효과**: Claude API 비용 절감

**작업 순서**:
- [ ] 7.3.1 `requirements.txt`에 `transformers>=4.36.0` 추가
- [ ] 7.3.2 `src/analyzer/sentiment_analyzer.py` 생성
- [ ] 7.3.3 전략 설명문 과대광고 점수 산출

---

### 7.4 PyneCore - Pine Script Python 런타임
- **사이트**: https://pynecore.org
- **용도**: Pine Script를 Python에서 직접 실행

**작업 순서**:
- [ ] 7.4.1 PyneCore 설치 및 테스트
- [ ] 7.4.2 간단한 전략 변환 테스트
- [ ] 7.4.3 백테스트 파이프라인 통합

---

## 📊 작업 우선순위 요약

| 우선순위 | 단계 | 작업 | 예상 시간 |
|---------|------|------|----------|
| 🔴 Critical | 1.1 | 텔레그램 토큰 secrets 이동 | 15분 |
| 🔴 Critical | 1.2 | CORS 설정 강화 | 10분 |
| 🟠 High | 2.1 | Rate Limiting 구현 | 30분 |
| 🟠 High | 2.2 | API 인증 (선택) | 1시간 |
| 🟡 Medium | 3.1-3.3 | 코드 품질 개선 | 2시간 |
| 🟢 Low | 4.1-4.3 | 인프라 개선 | 3시간 |
| 🔵 Enhancement | 5.1-5.2 | 기능 개선 | 3시간 |
| 💰 Live Trading | 6.1 | API 키 암호화 | 1시간 |
| 💰 Live Trading | 6.2 | 안전장치 구현 | 2시간 |
| 💰 Live Trading | 6.3 | 모니터링 대시보드 | 3시간 |
| 💰 Live Trading | 6.4 | 거래 로그 | 1시간 |
| 💰 Live Trading | 6.5 | Freqtrade 통합 | 4시간 |
| 🚀 Optional | 7.1 | pynescript | 1시간 |
| 🚀 Optional | 7.2 | VectorBT | 2시간 |
| � Optional | 7.3 | FinBERT | 1시간 |

---

## ✅ 완료 확인

- [x] 1단계 (Critical) 완료 - 텔레그램 토큰 secrets 이동, CORS 강화
- [x] 2단계 (High) 완료 - Rate Limiting, 입력값 검증, API 인증
- [x] 3단계 (Medium) 완료 - 빈 파일 구현, 로깅 시스템, 에러 핸들링
- [x] 4단계 (Low) 완료 - Docker 보안 강화, 테스트 커버리지 확대 (146개 테스트)
- [x] 5단계 (Enhancement) 완료 - 대시보드 개선, 알림 시스템
- [x] 6단계 (Live Trading) 완료 - API 키 암호화, 안전장치, 거래 로그, 텔레그램 명령어
- [ ] 7단계 (오픈소스) - 선택사항 (필요시 진행)
- [x] 전체 테스트 통과 (146개)
- [x] 프로덕션 배포 완료 (GitHub Actions 자동 배포)

---

## 📝 참고사항

1. **작업 중단 시**: 현재 진행 중인 단계와 체크박스 상태를 기록
2. **롤백 필요 시**: `git revert` 또는 이전 Docker 이미지로 복구
3. **긴급 상황**: 1단계 보안 수정은 즉시 진행 권장
4. **실전매매 주의**: 6.6 체크리스트 완료 전 절대 실전 자금 투입 금지!
