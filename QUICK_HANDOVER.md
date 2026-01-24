# 🚀 Freqtrade 실전매매 - 빠른 인수인계

## 📋 핵심 정보

### 시스템 상태
- **거래소**: Bitget (API 연결 완료)
- **전략**: SimpleAdaptiveStrategy (EMA 크로스오버)
- **모드**: 실전 거래 (dry_run: false)
- **거래당 금액**: 20 USDT
- **최대 동시 거래**: 3개

### 서버 정보
```
IP: 141.164.55.245
User: root
Password: [Br76r(6mMDr%?ia
Path: /root/freqtrade-live
```

### API 정보
```
Exchange: Bitget
API Key: bg_6563f559d91c72bd3a2b2e552a1c9cec
API Secret: 1db14e0f08b08663d07e60b19af10ecd1ec6f9e162e0cde923dec2770e6b786f
Password: Wnrkswl123
```

---

## 🎯 즉시 실행 가능한 명령어

### 서버 접속 및 시작
```bash
# 1. 서버 접속
ssh root@141.164.55.245

# 2. 디렉토리 이동
cd /root/freqtrade-live

# 3. 봇 시작
./start_trading.sh

# 4. 상태 확인
./check_status.sh

# 5. 로그 확인
docker-compose logs -f freqtrade

# 6. 중지
./stop_trading.sh
```

### 모니터링
```
대시보드: http://141.164.55.245:8082
사용자명: admin
비밀번호: admin
```

### 긴급 정지
```bash
ssh root@141.164.55.245 "cd /root/freqtrade-live && docker-compose down"
```

---

## 📁 핵심 파일

1. **전략 파일**: `freqtrade/user_data/strategies/SimpleAdaptiveStrategy.py`
2. **설정 파일**: `freqtrade/config.json`
3. **배포 스크립트**: `deploy_freqtrade_server.sh`
4. **상세 가이드**: `LIVE_TRADING_SETUP_COMPLETE.md`
5. **완전한 인수인계**: `HANDOVER_TO_CLAUDE.md`

---

## 💬 Claude에게 전달하는 방법

### 방법 1: 파일 첨부
다음 파일들을 첨부하세요:
1. `HANDOVER_TO_CLAUDE.md` (완전한 문서)
2. `freqtrade/config.json` (설정)
3. `freqtrade/user_data/strategies/SimpleAdaptiveStrategy.py` (전략)

### 방법 2: 프롬프트 사용
```
Freqtrade 실전매매 시스템을 인수인계합니다.

현재 상황:
- Bitget 거래소 연결 완료
- SimpleAdaptiveStrategy 전략으로 실전 거래 중
- 서버: 141.164.55.245 (Docker 실행)
- 거래당 20 USDT, 최대 3개 동시 거래

필요한 작업:
[구체적인 요청 사항]

첨부 파일:
- HANDOVER_TO_CLAUDE.md (전체 문서)
- config.json (설정)
- SimpleAdaptiveStrategy.py (전략)

도움이 필요하면 알려주세요!
```

### 방법 3: 컨텍스트 공유
Claude에게 다음 정보를 제공하세요:

**시스템 구조:**
```
- 거래소: Bitget
- 전략: EMA(9) x EMA(21) 크로스오버
- 리스크: 손절 -3%, 트레일링 스톱 활성화
- 서버: Docker Compose로 실행
```

**즉시 필요한 정보:**
- 서버 IP: 141.164.55.245
- 모니터링: http://141.164.55.245:8082
- 긴급 정지: `docker-compose down`

---

## ⚠️ 주의사항

1. **API 키 보안**: 절대 공개하지 말 것
2. **실전 거래 중**: 실제 자금 사용 중
3. **정기 모니터링**: 하루 2-3회 확인 필수
4. **긴급 정지 방법**: 숙지 필수

---

## 📞 긴급 연락

**Telegram 알림:**
- Bot: 8327452496:AAFwrVohBY-9dVoo8D7mXHqGLEDXMOCJK_M
- Chat: 7980845952

**서버 접속:**
```bash
ssh root@141.164.55.245
# 비밀번호: [Br76r(6mMDr%?ia
```

---

**더 자세한 내용은 `HANDOVER_TO_CLAUDE.md` 참조**
