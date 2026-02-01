# 🎯 전략연구소 시스템 현황

## ✅ 현재 실행 중인 서비스

### 1. 통합 대시보드 (메인)
- **URL**: http://localhost:8081
- **설명**: Strategy Research Lab 통합 대시보드
- **기능**:
  - TradingView 전략 분석 결과 조회
  - 전략 목록 및 상세 정보
  - 백테스트 차트 확인
  - 실전매매 모니터링
- **상태**: ✅ 실행 중

### 2. API 서버
- **Base URL**: http://localhost:8081/api
- **API 문서**: http://localhost:8081/api/docs
- **주요 엔드포인트**:
  - `GET /api/health` - 헬스 체크
  - `GET /api/stats` - 통계 정보
  - `GET /api/strategies` - 전략 목록
  - `GET /api/strategy/{script_id}` - 전략 상세
  - `GET /live` - 실전매매 대시보드
- **상태**: ✅ 실행 중

## 📦 설치된 컴포넌트

### Freqtrade
- **버전**: 2025.12
- **Python**: 3.11.9
- **CCXT**: 4.5.20
- **설정 파일**: `freqtrade/config.json`
- **전략 디렉토리**: `freqtrade/user_data/strategies/`
- **상태**: ⏸️ 설정 완료 (필요시 실행)

### 사용 가능한 전략
1. SimpleAdaptiveStrategy
2. SimpleAdaptiveStrategy_v2
3. AdaptiveMLStrategy
4. FreqAIStrategy
5. SampleStrategy
6. SmaCrossoverStrategy
7. BollingerBandBounceStrategy
8. RsiOversoldBounceStrategy

## 🚀 서비스 시작 방법

### 통합 대시보드 (이미 실행 중)
```bash
# 현재 실행 중
# 브라우저에서 http://localhost:8081 접속
```

### Freqtrade 실행
```bash
cd freqtrade
freqtrade trade --config config.json --strategy SimpleAdaptiveStrategy
```

### Freqtrade 웹 UI
```bash
cd freqtrade
freqtrade webserver --config config.json
# 접속: http://localhost:8081 (API 서버와 동일 포트)
```

## 📊 주요 기능

### 1. 전략 분석
- TradingView에서 수집한 전략 분석
- 등급 시스템 (A, B, C, D, F)
- Repainting 및 Overfitting 점수

### 2. 백테스트
- 과거 데이터로 전략 성능 테스트
- 수익률, 승률, 최대 낙폭 등 지표
- 시각화 차트

### 3. 실전매매 모니터링
- 실시간 거래 상태
- 포지션 관리
- 손익 추적

## 🔧 설정 파일 위치

```
전략연구소/
├── api/server.py              # API 서버
├── data/
│   └── strategies.db          # 전략 데이터베이스
├── templates/
│   └── dashboard.html         # 대시보드 UI
├── freqtrade/
│   ├── config.json            # Freqtrade 설정
│   └── user_data/
│       └── strategies/        # 전략 파일들
└── logs/                      # 로그 파일
```

## 📝 다음 단계

### 1. 통합 대시보드 사용
```
http://localhost:8081
```

### 2. Freqtrade 최적화
```bash
cd freqtrade
./install_optimal_packages.sh
```

### 3. 전략 백테스트
```bash
cd freqtrade
freqtrade backtesting \
  --strategy SimpleAdaptiveStrategy \
  --timerange 20240101-20241231
```

### 4. 실전 거래 시작 (주의!)
```bash
cd freqtrade
# config.json에서 dry_run: false로 변경
freqtrade trade --config config.json --strategy SimpleAdaptiveStrategy
```

## ⚠️ 중요 사항

1. **Dry Run 모드**: 현재 설정은 시뮬레이션 모드입니다
2. **API 키 보안**: Bitget API 키가 설정되어 있습니다
3. **정기 모니터링**: 봇을 정기적으로 확인하세요
4. **백업**: 중요한 설정과 데이터를 백업하세요

## 🆘 문제 해결

### 대시보드 접속 안됨
```bash
# 프로세스 확인
lsof -i :8081

# 서버 재시작
cd /Users/mr.joo/Desktop/전략연구소
APP_BASE_DIR=$(pwd) python3 api/server.py
```

### Freqtrade 오류
```bash
# 로그 확인
tail -f freqtrade/user_data/logs/freqtrade.log

# 설정 확인
freqtrade show-config
```

## 📚 문서

- `README.md` - 프로젝트 개요
- `freqtrade/OPTIMAL_SETUP_GUIDE.md` - Freqtrade 최적 설정
- `freqtrade/README.md` - Freqtrade 가이드
- `BITGET_CONNECTION_REPORT.md` - Bitget 연결 정보

---

**현재 시스템 상태**: ✅ 정상 작동 중
**마지막 업데이트**: 2026-01-21
