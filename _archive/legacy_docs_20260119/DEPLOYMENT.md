# 🚀 배포 및 운영 가이드

> **서버**: `141.164.55.245` (Hetzner Cloud, Ubuntu 22.04)  
> **프로젝트 경로**: `/root/service_c/strategy-research-lab`  
> **마지막 업데이트**: 2026-01-13

---

## ⚠️ 핵심 규칙 (반드시 준수)

### ❌ 절대 금지
1. **원격 서버에서 직접 코드 수정 금지** - 코드 동기화 깨짐
2. **Docker 컨테이너 내부에서 파일 수정 금지**
3. **로컬과 서버 코드가 다른 상태로 방치 금지**
4. **main 브랜치에 테스트 안 된 코드 push 금지**

### ✅ 올바른 배포 순서
```
로컬 수정 → 테스트 → Git 커밋 → GitHub Push → 자동 배포 (5-10분)
```

---

## 📋 배포 절차

### 1. 로컬에서 코드 수정 및 테스트
```bash
# 테스트 실행 (172개 통과해야 함)
python -m pytest tests/ -v

# 변경사항 확인
git status
git diff
```

### 2. Git 커밋 및 푸시
```bash
git add .
git commit -m "feat: 변경 내용 설명"
git push origin main
```

### 3. 배포 상태 확인
```bash
# GitHub Actions 상태 확인
gh run list --limit 3

# 배포 로그 확인 (실패 시)
gh run view --log | tail -100
```

### 4. 서버 헬스체크
```bash
# API 서버 확인 (포트 8081 사용!)
curl http://141.164.55.245:8081/api/health

# 전략 통계 확인
curl http://141.164.55.245:8081/api/stats
```

---

## 🔧 서버 관리

### SSH 접속
```bash
ssh root@141.164.55.245
```

### Docker 명령어
```bash
# 프로젝트 경로
cd /root/service_c/strategy-research-lab

# 컨테이너 상태 확인
docker compose ps

# 로그 확인
docker compose logs -f --tail=100

# 재시작
docker compose restart

# 완전 재시작 (문제 발생 시)
docker compose down && docker compose up -d
```

### 디스크 정리 (용량 부족 시)
```bash
# Docker 캐시 정리 (약 10-30GB 확보)
docker system prune -af --volumes

# 디스크 사용량 확인
df -h /
docker system df
```

---

## 🏗️ 시스템 구조

### 실행 중인 서비스
| 서비스 | 컨테이너명 | 포트 | 역할 |
|--------|-----------|------|------|
| API 서버 | strategy-research-lab | 8081:8080 | REST API, 대시보드 |
| 스케줄러 | strategy-scheduler | - | 6시간마다 전략 수집 |

### 네트워크 구조
```
외부 접근 (포트 8081)
    └── strategy-research-lab (API)
    
내부 네트워크 (group_c_network)
    ├── strategy-research-lab
    └── strategy-scheduler
```

### 주요 디렉토리
```
/root/service_c/strategy-research-lab/
├── api/server.py          # API 서버
├── data/                   # 데이터 (DB, 리포트)
├── logs/                   # 로그 파일
├── freqtrade/              # Freqtrade 설정
└── docker-compose.yml      # Docker 설정
```

---

## 🔥 트러블슈팅

### 1. 배포 실패 - SSH 타임아웃
**증상**: `Broken pipe`, `Connection timed out`
```bash
# 해결: 서버에서 직접 빌드
ssh root@141.164.55.245
cd /root/service_c/strategy-research-lab
docker compose build --parallel
docker compose up -d
```

### 2. 배포 실패 - 디스크 부족
**증상**: `no space left on device`
```bash
# 해결: Docker 캐시 정리
ssh root@141.164.55.245
docker system prune -af --volumes
```

### 3. 배포 실패 - 권한 오류
**증상**: `PermissionError: /app/logs/api.log`
```bash
# 해결: 권한 수정
ssh root@141.164.55.245
cd /root/service_c/strategy-research-lab
chmod -R 777 logs data
docker compose restart
```

### 4. API 응답 없음
**증상**: `curl` 타임아웃
```bash
# 1. 컨테이너 상태 확인
ssh root@141.164.55.245
docker compose ps

# 2. 로그 확인
docker compose logs --tail=50

# 3. 재시작
docker compose restart
```

### 5. Health Check 실패
**증상**: GitHub Actions에서 Health check failed
```bash
# 주의: 포트 80이 아닌 8081 사용!
curl http://141.164.55.245:8081/api/health

# Nginx 프록시 미설정 상태이므로 직접 포트 접근 필요
```

---

## 🤖 Freqtrade 운영

### 설치 상태 확인
```bash
ssh root@141.164.55.245
cd /root/freqtrade
source .venv/bin/activate
freqtrade --version
```

### 드라이런 실행
```bash
cd /root/freqtrade
freqtrade trade --config config.json --strategy SampleStrategy --dry-run
```

### FreqAI 실행
```bash
freqtrade trade --config config_freqai.json --strategy FreqAIStrategy --dry-run
```

### 설정 파일 위치
- 기본 설정: `/root/service_c/strategy-research-lab/freqtrade/config.json`
- FreqAI 설정: `/root/service_c/strategy-research-lab/freqtrade/config_freqai.json`
- 전략 파일: `/root/service_c/strategy-research-lab/freqtrade/user_data/strategies/`

---

## 📊 모니터링

### API 엔드포인트
| 엔드포인트 | 설명 |
|-----------|------|
| `GET /api/health` | 헬스체크 |
| `GET /api/stats` | 전략 통계 |
| `GET /api/strategies` | 전략 목록 |
| `GET /api/docs` | Swagger 문서 |

### 주요 지표
```bash
# 전략 수집 현황
curl -s http://141.164.55.245:8081/api/stats | jq

# 예상 응답:
# {"total_strategies":71,"analyzed_count":71,"passed_count":31,"avg_score":64.9}
```

---

## 🔐 보안 체크리스트

- [x] API 키는 GitHub Secrets에만 저장
- [x] `.env` 파일은 `.gitignore`에 포함
- [x] SSH 키는 GitHub Secrets에 저장
- [x] Rate Limiting 적용 (분당 60회)
- [x] CORS 제한 설정
- [ ] Nginx 리버스 프록시 설정 (선택)
- [ ] SSL 인증서 설정 (선택)

---

## 📁 GitHub Secrets 목록

| Secret 이름 | 용도 |
|------------|------|
| `SSH_PRIVATE_KEY` | 서버 SSH 접속 |
| `ANTHROPIC_API_KEY` | Claude AI API |
| `TELEGRAM_BOT_TOKEN` | 텔레그램 알림 (선택) |
| `TELEGRAM_CHAT_ID` | 텔레그램 채팅 ID (선택) |

---

## 📞 긴급 연락

### 서버 정보
- **IP**: 141.164.55.245
- **Provider**: Hetzner Cloud
- **OS**: Ubuntu 22.04 LTS
- **디스크**: 75GB (현재 45% 사용)
- **메모리**: 4GB

### 복구 절차
1. SSH 접속: `ssh root@141.164.55.245`
2. 프로젝트 이동: `cd /root/service_c/strategy-research-lab`
3. 컨테이너 재시작: `docker compose down && docker compose up -d`
4. 헬스체크: `curl localhost:8081/api/health`

---

**문서 버전**: 2.0  
**작성일**: 2026-01-13
