# 실전 배포 Phase 0: 사전 준비 체크리스트

**목표**: Binance API 설정 및 인프라 준비
**소요 시간**: 1-2시간
**완료일**: 2026-01-04

---

## ✅ Binance API 설정

### 1. Binance Testnet 계정 생성 (필수)

**Testnet URL**: https://testnet.binancefuture.com/

**절차**:
1. [ ] 이메일로 계정 생성
2. [ ] API 키 발급 (Read + Write 권한)
3. [ ] API Secret 안전하게 저장
4. [ ] IP 화이트리스트 설정 (선택)

**생성된 키 저장 위치**:
```
/Users/mr.joo/Desktop/전략연구소/.env
```

**`.env` 파일 형식**:
```bash
# Binance Testnet API (Phase 1)
BINANCE_TESTNET_API_KEY=your_testnet_api_key_here
BINANCE_TESTNET_API_SECRET=your_testnet_secret_here

# Binance Mainnet API (Phase 3 - 나중에 추가)
BINANCE_API_KEY=
BINANCE_API_SECRET=

# Telegram Bot (기존)
TELEGRAM_BOT_TOKEN=8327452496:AAFwrVohBY-9dVoo8D7mXHqGLEDXMOCJK_M
TELEGRAM_CHAT_ID=your_chat_id_here
```

### 2. Binance Mainnet 계정 준비 (나중에)

**Mainnet URL**: https://www.binance.com/

**절차** (Phase 3에서 진행):
1. [ ] KYC 인증 완료
2. [ ] 2FA 활성화
3. [ ] API 키 발급 (Spot Trading 권한만)
4. [ ] IP 화이트리스트 필수 설정
5. [ ] 출금 권한 비활성화 (보안)

---

## 🖥️ 서버 인프라 확인

### 현재 서버 상태

**Hetzner VPS**: 5.161.112.248

```bash
# 서버 접속
ssh root@5.161.112.248

# 리소스 확인
htop
df -h
```

**필요 리소스** (Trading Engine 추가 시):
- CPU: 4코어 이상 권장 (현재 확인 필요)
- Memory: 8GB 이상 권장
- Disk: 50GB 여유 공간

### Docker 환경 확인

```bash
# 기존 컨테이너 확인
cd /root/service_c/strategy-research-lab/
docker-compose ps

# 리소스 사용량
docker stats --no-stream
```

---

## 📦 필요 패키지 설치

### Python 패키지

```bash
cd /Users/mr.joo/Desktop/전략연구소
pip3 install ccxt python-binance python-dotenv
```

**requirements_trading.txt**:
```
ccxt>=4.2.0
python-binance>=1.0.19
python-dotenv>=1.0.0
websockets>=12.0
```

### PostgreSQL 설정 (거래 데이터 저장)

```bash
# Docker Compose에 PostgreSQL 추가
# docker-compose.yml 수정 필요
```

---

## 🔐 보안 설정

### .env 파일 보안

```bash
# .env 파일 권한 설정
chmod 600 /Users/mr.joo/Desktop/전략연구소/.env

# Git에서 제외
echo ".env" >> .gitignore
echo "*.log" >> .gitignore
echo "*.secret" >> .gitignore
```

### GitHub Secrets 업데이트

```bash
# GitHub repository: joocy75-hash/TradingView-Strategy
# Settings > Secrets and variables > Actions

# 추가할 Secrets:
# - BINANCE_TESTNET_API_KEY
# - BINANCE_TESTNET_API_SECRET
# - TELEGRAM_BOT_TOKEN (기존)
```

---

## 📁 프로젝트 구조 준비

### Trading Engine 디렉토리 생성

```bash
mkdir -p /Users/mr.joo/Desktop/전략연구소/production-trading-engine
cd /Users/mr.joo/Desktop/전략연구소/production-trading-engine

# 하위 디렉토리
mkdir -p {src,config,logs,data}
mkdir -p src/{engine,risk,position,monitor}

# 초기 파일 생성
touch src/__init__.py
touch src/engine/__init__.py
touch src/risk/__init__.py
touch src/position/__init__.py
touch src/monitor/__init__.py
```

**디렉토리 구조**:
```
production-trading-engine/
├── src/
│   ├── engine/          # 거래 실행 엔진
│   │   ├── __init__.py
│   │   ├── trading_engine.py
│   │   └── order_manager.py
│   ├── risk/            # 리스크 관리
│   │   ├── __init__.py
│   │   ├── risk_manager.py
│   │   └── position_sizer.py
│   ├── position/        # 포지션 관리
│   │   ├── __init__.py
│   │   └── position_tracker.py
│   └── monitor/         # 모니터링
│       ├── __init__.py
│       ├── telegram_notifier.py
│       └── metrics_collector.py
├── config/
│   ├── config.yaml
│   └── strategies.yaml
├── logs/
└── data/
```

---

## 🧪 Testnet 연결 테스트

### CCXT 연결 테스트 스크립트

**파일**: `test_binance_connection.py`

```python
"""
Binance Testnet Connection Test
"""

import ccxt
import os
from dotenv import load_dotenv

load_dotenv()

# Testnet 설정
exchange = ccxt.binance({
    'apiKey': os.getenv('BINANCE_TESTNET_API_KEY'),
    'secret': os.getenv('BINANCE_TESTNET_API_SECRET'),
    'enableRateLimit': True,
    'options': {
        'defaultType': 'future',
        'adjustForTimeDifference': True,
    }
})

# Testnet URL 설정
exchange.set_sandbox_mode(True)

def test_connection():
    """Test Binance Testnet connection"""

    print("=" * 60)
    print("Binance Testnet Connection Test")
    print("=" * 60)

    try:
        # 1. 계정 정보 조회
        balance = exchange.fetch_balance()
        print("\n✓ Account Balance:")
        print(f"  USDT: {balance['USDT']['free']:.2f}")

        # 2. 시장 데이터 조회
        ticker = exchange.fetch_ticker('BTC/USDT')
        print(f"\n✓ BTC/USDT Price: ${ticker['last']:.2f}")

        # 3. 서버 시간 동기화
        server_time = exchange.fetch_time()
        print(f"\n✓ Server Time: {server_time}")

        # 4. API Rate Limit
        print(f"\n✓ Rate Limit: {exchange.rateLimit}ms")

        print("\n" + "=" * 60)
        print("✅ Connection Test Passed!")
        print("=" * 60)

        return True

    except Exception as e:
        print(f"\n❌ Connection Test Failed: {e}")
        return False

if __name__ == '__main__':
    test_connection()
```

**실행**:
```bash
python3 test_binance_connection.py
```

---

## 📊 Telegram 알림 테스트

### 알림 테스트 스크립트

**파일**: `test_telegram_notification.py`

```python
"""
Telegram Notification Test
"""

import os
import sys
from dotenv import load_dotenv

sys.path.append('/Users/mr.joo/Desktop/전략연구소')
from strategy-research-lab.src.notification.telegram_bot import TelegramNotifier

load_dotenv()

def test_notification():
    """Test Telegram notification"""

    notifier = TelegramNotifier(
        bot_token=os.getenv('TELEGRAM_BOT_TOKEN'),
        chat_id=os.getenv('TELEGRAM_CHAT_ID')
    )

    # 테스트 메시지
    message = """
🧪 **Testnet 연결 테스트**

✅ Binance Testnet 연결 성공
✅ Telegram 봇 연결 성공

📊 시스템 상태:
  - Trading Engine: Ready
  - Risk Manager: Ready
  - Monitor Service: Ready

🚀 Phase 1 준비 완료!
    """

    result = notifier.send_message(message)

    if result:
        print("✅ Telegram notification sent successfully!")
    else:
        print("❌ Telegram notification failed!")

    return result

if __name__ == '__main__':
    test_notification()
```

---

## 🎯 Phase 0 완료 기준

### 필수 항목

- [ ] Binance Testnet API 키 발급 완료
- [ ] `.env` 파일 생성 및 보안 설정
- [ ] Binance 연결 테스트 통과
- [ ] Telegram 알림 테스트 통과
- [ ] 서버 리소스 확인 완료
- [ ] Trading Engine 디렉토리 구조 생성

### 선택 항목

- [ ] PostgreSQL 컨테이너 준비
- [ ] Redis 컨테이너 준비
- [ ] Grafana 대시보드 설치
- [ ] Mainnet API 키 발급 (Phase 3에서 사용)

---

## 📝 다음 단계 (Phase 1)

Phase 0 완료 후:

1. **Trading Engine 구현** (2-3일)
   - CCXT 기반 주문 실행
   - Adaptive ML 전략 통합
   - 포지션 관리 시스템

2. **Testnet 검증** (1주)
   - 24시간 무인 운영 테스트
   - 최소 50회 거래 실행
   - 모든 시나리오 검증

3. **Paper Trading** (1주)
   - Mainnet 실시간 가격
   - 가상 주문 시뮬레이션
   - 성과 모니터링

---

**작성일**: 2026-01-04
**작성자**: Strategy Research Lab
**버전**: 1.0
