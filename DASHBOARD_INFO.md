# 🎯 통합 대시보드 정보

## ✅ 현재 상태

**통합 대시보드가 정상적으로 설정되었습니다!**

- **URL**: http://localhost:8081
- **파일**: `data/integrated_dashboard.html`
- **제목**: Trading Strategy Lab - Integrated Dashboard

## 📊 통합된 기능

### 1. 📈 Overview (개요)
- 전체 시스템 상태 요약
- 주요 지표 대시보드

### 2. 🤖 AI Intelligence (AI 인텔리전스)
- 마켓 인텔리전스 AI
- 실시간 분석

### 3. 🎯 Live Trading (실전 자동매매)
- 실전 매매 모니터링
- 포지션 관리

### 4. ⬡ FreqControl (매매 관리)
- **포트**: 8081
- **기능**: 추세 추종 전략 관리 및 실시간 매매 상태 제어
- **로그인**: admin / admin
- **iframe으로 통합**

### 5. ⚗ FreqBacktest (전략 검증소)
- **포트**: 8082
- **기능**: 고성능 백테스트 및 전략 검증 환경
- **로그인**: admin / admin
- **iframe으로 통합**

### 6. 🐝 Hummingbot (AMM & Arbitrage)
- **포트**: 8501
- **기능**: 시장 조성 및 차익 거래
- **상태**: 삭제됨 (필요시 재설치)

### 7. 🌐 CryptoVision AI
- HuggingFace 기반 자산 관계망 시각화

### 8. 📰 External Tools
- Messari: 기관급 온체인 데이터
- CryptoPanic: 실시간 뉴스 피드
- Perplexity: AI 기반 금융 리서치

## 🚀 사용 방법

### 1. 브라우저 접속
```
http://localhost:8081
```

### 2. 완전 새로고침
- **Mac**: Cmd + Shift + R
- **Windows/Linux**: Ctrl + Shift + R

### 3. 탭 전환
- 왼쪽 사이드바에서 원하는 기능 클릭
- 각 탭은 독립적으로 작동

## ⚙️ 필요한 서비스

### 현재 실행 중
- ✅ **API 서버**: 포트 8081 (통합 대시보드 제공)

### 필요시 실행
- ⏸️ **FreqControl**: Freqtrade 웹 UI (포트 8081)
  ```bash
  cd freqtrade
  freqtrade webserver --config config.json
  ```

- ⏸️ **FreqBacktest**: Freqtrade 백테스트 서버 (포트 8082)
  ```bash
  cd freqtrade
  freqtrade webserver --config config_backtest_server.json
  ```

- ❌ **Hummingbot**: 삭제됨 (필요시 재설치)

## 🎨 디자인 특징

- **테마**: Enamel Black / Professional Fintech UI
- **스타일**: Sophisticated Dark Theme
- **반응형**: 세로 스크롤 지원
- **iframe 최적화**: 0.7x 스케일링으로 최적화

## 📝 주의사항

1. **FreqControl과 FreqBacktest는 별도 실행 필요**
   - 통합 대시보드는 iframe으로 표시만 함
   - 실제 서비스는 각각 실행해야 함

2. **포트 충돌 주의**
   - 8081: API 서버 (현재 실행 중)
   - 8081: FreqControl (필요시 실행)
   - 8082: FreqBacktest (필요시 실행)

3. **로그인 정보**
   - Username: admin
   - Password: admin

## 🔧 문제 해결

### 대시보드가 안 보임
```bash
# 브라우저 캐시 완전 삭제 후 재접속
# 또는 시크릿 모드로 접속
```

### iframe이 로드 안됨
```bash
# 해당 서비스가 실행 중인지 확인
lsof -i :8081
lsof -i :8082
lsof -i :8501
```

### API 서버 재시작
```bash
# 현재 프로세스 확인
lsof -i :8081

# 재시작
cd /Users/mr.joo/Desktop/전략연구소
APP_BASE_DIR=$(pwd) python3 api/server.py
```

---

**통합 대시보드로 모든 기능을 한 곳에서 관리하세요! 🚀**
