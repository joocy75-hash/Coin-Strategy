# 서버 배포 가이드

## 배포 정보

- **서버 IP**: 152.42.169.132
- **서버 OS**: Ubuntu 22.04 LTS
- **프로젝트 경로**: `/opt/strategy-research-lab`
- **서비스명**: `strategy-collector`

---

## 자동화 시스템 구성

### 1. 수집 주기
- **연속 실행 모드**: 6시간마다 자동 수집
- **수집 대상**: TradingView 오픈소스 전략 (좋아요 500개 이상)
- **최대 수집 수**: 30개/사이클

### 2. 파이프라인 흐름
```
1. 전략 메타데이터 수집 (TradingView 스크래핑)
   ↓
2. Pine Script 소스 코드 추출
   ↓
3. 품질 분석 (리페인팅, 오버피팅 검사)
   ↓
4. SQLite 데이터베이스 저장
   ↓
5. 고득점 전략 Python 변환 (점수 ≥ 50)
```

---

## 서비스 관리 명령어

### 상태 확인
```bash
ssh root@152.42.169.132

# 서비스 상태 확인
systemctl status strategy-collector

# 실시간 로그 확인
journalctl -u strategy-collector -f

# 최근 로그 확인
journalctl -u strategy-collector -n 100
```

### 서비스 제어
```bash
# 서비스 시작
systemctl start strategy-collector

# 서비스 중지
systemctl stop strategy-collector

# 서비스 재시작
systemctl restart strategy-collector
```

### 수동 실행 (단일 사이클)
```bash
cd /opt/strategy-research-lab
source venv/bin/activate
python deploy/auto_collector.py --max-strategies 10 --min-likes 500
```

---

## 데이터 확인

### 데이터베이스 조회
```bash
cd /opt/strategy-research-lab
source venv/bin/activate
python3 -c "
import sqlite3
conn = sqlite3.connect('data/strategies.db')
cur = conn.cursor()

# 총 전략 수
cur.execute('SELECT COUNT(*) FROM strategies')
print(f'총 전략 수: {cur.fetchone()[0]}')

# 최근 수집 전략
cur.execute('SELECT title, likes, created_at FROM strategies ORDER BY created_at DESC LIMIT 5')
for row in cur.fetchall():
    print(row)
"
```

### 변환된 파일 확인
```bash
ls -la /opt/strategy-research-lab/data/converted/
```

### 로그 파일 확인
```bash
ls -la /opt/strategy-research-lab/logs/
cat /opt/strategy-research-lab/logs/auto_collect_$(date +%Y%m%d).log
```

---

## 디렉토리 구조 (서버)

```
/opt/strategy-research-lab/
├── deploy/
│   ├── auto_collector.py       # 자동 수집 스크립트
│   ├── strategy-collector.service  # systemd 서비스
│   └── check_status.sh         # 상태 확인 스크립트
├── src/                        # 소스 코드
├── data/
│   ├── strategies.db           # SQLite 데이터베이스
│   └── converted/              # 변환된 Python 파일
├── logs/                       # 로그 파일
├── venv/                       # Python 가상환경
├── requirements.txt
└── .env                        # 환경 설정
```

---

## 설정 변경

### .env 파일 수정
```bash
nano /opt/strategy-research-lab/.env
```

주요 설정:
- `OPENAI_API_KEY`: LLM 분석용 API 키 (선택)
- `MAX_STRATEGIES`: 최대 수집 수
- `MIN_LIKES`: 최소 좋아요 필터
- `SKIP_LLM`: LLM 분석 스킵 여부

### systemd 서비스 수정
```bash
# 서비스 파일 수정
nano /etc/systemd/system/strategy-collector.service

# 변경 적용
systemctl daemon-reload
systemctl restart strategy-collector
```

---

## 문제 해결

### 1. 서비스가 시작되지 않음
```bash
# 로그 확인
journalctl -u strategy-collector -n 50

# 수동으로 테스트 실행
cd /opt/strategy-research-lab
source venv/bin/activate
python deploy/auto_collector.py
```

### 2. Playwright 브라우저 오류
```bash
source /opt/strategy-research-lab/venv/bin/activate
playwright install chromium
playwright install-deps chromium
```

### 3. 의존성 문제
```bash
cd /opt/strategy-research-lab
source venv/bin/activate
pip install -r requirements.txt --upgrade
```

### 4. 디스크 공간 부족
```bash
# 오래된 로그 정리
find /opt/strategy-research-lab/logs -mtime +30 -delete

# 디스크 사용량 확인
df -h /
```

---

## 로컬에서 배포 업데이트

```bash
# 변경된 파일만 업로드
scp -r src/ root@152.42.169.132:/opt/strategy-research-lab/
scp deploy/auto_collector.py root@152.42.169.132:/opt/strategy-research-lab/deploy/

# 서비스 재시작
ssh root@152.42.169.132 'systemctl restart strategy-collector'
```

---

## 모니터링

### 간단한 상태 체크 스크립트
```bash
#!/bin/bash
# check_status.sh

echo "=== Strategy Collector 상태 ==="
systemctl is-active strategy-collector
journalctl -u strategy-collector -n 5 --no-pager
echo ""
echo "=== 데이터베이스 통계 ==="
cd /opt/strategy-research-lab
source venv/bin/activate
python3 -c "
import sqlite3
conn = sqlite3.connect('data/strategies.db')
cur = conn.cursor()
cur.execute('SELECT COUNT(*) FROM strategies')
print(f'총 전략: {cur.fetchone()[0]}개')
"
```

---

## 연락처

문제 발생 시 로그를 확인하고 필요한 경우 서비스를 재시작하세요.
